"""
USDT-M Futures backtest engine.

Supports Long/Short, leverage, partial exit, trailing stop,
liquidation, slippage, and commission calculation.

Ported from RCoinFutTrader/src/backtester/realistic_engine.rs
"""

import logging
from typing import List, Optional, Dict, Any

from .types import FuturesConfig, Position, Side, ExitReason
from .metrics import TradeRecord, BacktestMetrics, calculate_metrics
from .data_loader import OhlcvBar
from .signal_evaluator import evaluate_entry_signal

logger = logging.getLogger(__name__)


class FuturesBacktestEngine:
    """
    Futures backtest engine with realistic simulation.

    Features:
    - Long/Short positions with configurable leverage (1x-125x)
    - Commission: 0.04% per trade (configurable)
    - Slippage: 1-2 ticks
    - Partial exit at configurable profit level
    - Trailing stop with trigger and callback
    - Forced liquidation calculation
    """

    def __init__(self, config: FuturesConfig):
        self.config = config
        self.position: Optional[Position] = None
        self.balance = config.investment
        self.equity_curve: List[float] = []
        self.trades: List[TradeRecord] = []

    def run(self, bars: List[OhlcvBar], strategy: Dict[str, Any]) -> BacktestMetrics:
        """
        Run backtest on historical OHLCV bars.

        Args:
            bars: Historical candlestick data
            strategy: Parsed strategy JSON with entry/exit conditions

        Returns:
            BacktestMetrics with comprehensive performance statistics
        """
        self.balance = self.config.investment
        self.equity_curve = [self.balance]
        self.trades = []
        self.position = None

        for i, bar in enumerate(bars):
            if self.position:
                self._check_exits(bar)

            if not self.position and i > 0:
                signal = evaluate_entry_signal(strategy, bars[:i + 1])
                if signal and self._direction_allowed(signal):
                    self._open_position(signal, bar)

            self._update_equity(bar)

        # 마지막 포지션 강제 청산
        if self.position and bars:
            self._close_position(bars[-1].close, bars[-1].datetime.isoformat(), ExitReason.SIGNAL)

        days = (bars[-1].timestamp - bars[0].timestamp) / 86_400_000 if len(bars) > 1 else 1
        return calculate_metrics(self.trades, self.equity_curve, self.config.investment, int(days))

    def _open_position(self, side: str, bar: OhlcvBar):
        entry_price = self._apply_slippage(bar.close, side)
        commission = self.balance * self.config.commission_rate
        self.balance -= commission

        qty = self.balance / entry_price
        self.position = Position(
            side=Side(side),
            entry_price=entry_price,
            quantity=qty,
            leverage=self.config.leverage,
            entry_time=bar.datetime.isoformat(),
            highest_price=entry_price,
            lowest_price=entry_price,
        )

    def _check_exits(self, bar: OhlcvBar):
        pos = self.position
        pos.highest_price = max(pos.highest_price, bar.high)
        pos.lowest_price = min(pos.lowest_price, bar.low)

        pnl_high = pos.unrealized_pnl(bar.high)
        pnl_low = pos.unrealized_pnl(bar.low)
        pnl_close = pos.unrealized_pnl(bar.close)

        time_str = bar.datetime.isoformat()

        # 강제 청산
        if self._check_liquidation(bar):
            self._close_position(pos.liquidation_price, time_str, ExitReason.LIQUIDATION)
            return

        # 손절
        if (pos.side == Side.LONG and pnl_low <= self.config.stop_loss_pct * self.config.leverage) or \
           (pos.side == Side.SHORT and pnl_high <= self.config.stop_loss_pct * self.config.leverage):
            sl_price = self._calc_exit_price(pos, self.config.stop_loss_pct)
            self._close_position(sl_price, time_str, ExitReason.STOP_LOSS)
            return

        # 분할 익절
        if self.config.partial_exit_enabled and not pos.partial_exited:
            if pnl_close >= self.config.partial_exit_pct * self.config.leverage:
                self._partial_exit(bar.close, time_str)

        # 추적 손절
        if self.config.trailing_stop_enabled:
            if self._check_trailing_stop(bar):
                self._close_position(bar.close, time_str, ExitReason.TRAILING_STOP)
                return

        # 익절
        if (pos.side == Side.LONG and pnl_high >= self.config.take_profit_pct * self.config.leverage) or \
           (pos.side == Side.SHORT and pnl_low >= self.config.take_profit_pct * self.config.leverage):
            tp_price = self._calc_exit_price(pos, self.config.take_profit_pct)
            self._close_position(tp_price, time_str, ExitReason.TAKE_PROFIT)

    def _close_position(self, exit_price: float, time_str: str, reason: ExitReason):
        pos = self.position
        commission = abs(pos.quantity * exit_price) * self.config.commission_rate
        pnl_pct = pos.unrealized_pnl(exit_price)
        pnl_amount = self.balance * (pnl_pct / 100)
        self.balance += pnl_amount - commission

        self.trades.append(TradeRecord(
            entry_price=pos.entry_price, exit_price=exit_price,
            side=pos.side.value, pnl=pnl_amount, return_pct=pnl_pct,
            entry_time=pos.entry_time, exit_time=time_str,
            exit_reason=reason.value, leverage=pos.leverage,
        ))
        self.position = None

    def _partial_exit(self, price: float, time_str: str):
        pos = self.position
        ratio = self.config.partial_exit_ratio
        partial_pnl = pos.unrealized_pnl(price) * ratio
        self.balance += self.balance * (partial_pnl / 100)
        pos.quantity *= (1 - ratio)
        pos.partial_exited = True

    def _check_liquidation(self, bar: OhlcvBar) -> bool:
        pos = self.position
        if pos.side == Side.LONG:
            return bar.low <= pos.liquidation_price
        return bar.high >= pos.liquidation_price

    def _check_trailing_stop(self, bar: OhlcvBar) -> bool:
        pos = self.position
        trigger = self.config.trailing_trigger_pct * self.config.leverage
        callback = self.config.trailing_callback_pct * self.config.leverage

        if pos.side == Side.LONG:
            peak_pnl = (pos.highest_price - pos.entry_price) / pos.entry_price * 100 * pos.leverage
            if peak_pnl >= trigger:
                current_pnl = pos.unrealized_pnl(bar.close)
                return (peak_pnl - current_pnl) >= callback
        else:
            peak_pnl = (pos.entry_price - pos.lowest_price) / pos.entry_price * 100 * pos.leverage
            if peak_pnl >= trigger:
                current_pnl = pos.unrealized_pnl(bar.close)
                return (peak_pnl - current_pnl) >= callback
        return False

    def _calc_exit_price(self, pos: Position, target_pct: float) -> float:
        ratio = target_pct / (100 * pos.leverage)
        if pos.side == Side.LONG:
            return pos.entry_price * (1 + ratio)
        return pos.entry_price * (1 - ratio)

    def _apply_slippage(self, price: float, side: str) -> float:
        tick = price * 0.0001 * self.config.slippage_ticks
        return price + tick if side == "long" else price - tick

    def _direction_allowed(self, signal: str) -> bool:
        d = self.config.direction
        if d == "both":
            return True
        return d == signal

    def _update_equity(self, bar: OhlcvBar):
        equity = self.balance
        if self.position:
            equity += self.balance * (self.position.unrealized_pnl(bar.close) / 100)
        self.equity_curve.append(max(equity, 0))
