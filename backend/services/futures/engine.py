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
        self.balance = config.initial_capital
        self.equity_curve: List[float] = []
        self.trades: List[TradeRecord] = []
        self._cooldown_bars = 0  # 청산 후 재진입 쿨다운

    def run(self, bars: List[OhlcvBar], strategy: Dict[str, Any]) -> BacktestMetrics:
        """
        Run backtest on historical OHLCV bars.

        Args:
            bars: Historical candlestick data
            strategy: Parsed strategy JSON with entry/exit conditions

        Returns:
            BacktestMetrics with comprehensive performance statistics
        """
        self.balance = self.config.initial_capital
        self._locked_margin = 0
        self.equity_curve = [self.balance]
        self.trades = []
        self.position = None
        self._cooldown_bars = 0
        self._daily_trades = 0
        self._current_day = -1
        # 현실적 재진입 쿨다운: 청산 후 최소 3봉 대기
        self._COOLDOWN_BARS = 3
        # 일일 최대 거래 수 제한 (과도한 거래 방지)
        self._MAX_DAILY_TRADES = 3

        for i, bar in enumerate(bars):
            # 일일 거래 카운트 리셋 (날짜 변경 감지)
            bar_day = bar.timestamp // 86_400_000
            if bar_day != self._current_day:
                self._current_day = bar_day
                self._daily_trades = 0

            if self.position:
                # 펀딩비: 8시간마다 0.01% (1h봉 기준 8봉마다)
                if i > 0 and i % 8 == 0:
                    funding_cost = self._locked_margin * self.config.leverage * 0.0001
                    self.balance -= funding_cost

                self._check_exits(bar)
                if not self.position:
                    self._cooldown_bars = self._COOLDOWN_BARS
                    self._update_equity(bar)
                    continue

            if self._cooldown_bars > 0:
                self._cooldown_bars -= 1
                self._update_equity(bar)
                continue

            if not self.position and i > 0 and self._daily_trades < self._MAX_DAILY_TRADES:
                signal = evaluate_entry_signal(strategy, bars[:i + 1])
                if signal and self._direction_allowed(signal):
                    self._open_position(signal, bar)
                    self._daily_trades += 1

            self._update_equity(bar)

        # 마지막 포지션 강제 청산
        if self.position and bars:
            self._close_position(bars[-1].close, bars[-1].datetime.isoformat(), ExitReason.SIGNAL)

        days = (bars[-1].timestamp - bars[0].timestamp) / 86_400_000 if len(bars) > 1 else 1
        return calculate_metrics(self.trades, self.equity_curve, self.config.initial_capital, int(days))

    def _open_position(self, side: str, bar: OhlcvBar):
        entry_price = self._apply_slippage(bar.close, side, bar)

        # 복리 모드: 현재 잔고 전액 투입
        trade_capital = self.balance
        if trade_capital <= 0:
            return  # 잔고 부족
        qty = trade_capital / entry_price
        commission = entry_price * qty * self.config.commission_rate
        # 마진 차감 (포지션 종료 시 반환)
        self._locked_margin = trade_capital
        self.balance -= (self._locked_margin + commission)
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

        # 익절 (추적 손절보다 먼저 체크 — TP 도달하면 즉시 청산)
        if (pos.side == Side.LONG and pnl_high >= self.config.take_profit_pct * self.config.leverage) or \
           (pos.side == Side.SHORT and pnl_low >= self.config.take_profit_pct * self.config.leverage):
            tp_price = self._calc_exit_price(pos, self.config.take_profit_pct)
            self._close_position(tp_price, time_str, ExitReason.TAKE_PROFIT)
            return

        # 분할 익절
        if self.config.partial_exit_enabled and not pos.partial_exited:
            if pnl_close >= self.config.partial_exit_pct * self.config.leverage:
                self._partial_exit(bar.close, time_str)

        # 추적 손절 (TP 미도달 시에만 작동)
        if self.config.trailing_stop_enabled:
            if self._check_trailing_stop(bar):
                self._close_position(bar.close, time_str, ExitReason.TRAILING_STOP)
                return

    def _close_position(self, exit_price: float, time_str: str, reason: ExitReason):
        pos = self.position
        # 수수료: 종료 시 수수료만 (진입 수수료는 이미 차감됨)
        exit_fee = exit_price * pos.quantity * self.config.commission_rate
        pnl_pct = pos.unrealized_pnl(exit_price)
        # RCoinFutTrader: pnl = qty * (exit - entry) * leverage
        if pos.side == Side.LONG:
            pnl_amount = (exit_price - pos.entry_price) * pos.quantity * self.config.leverage
        else:
            pnl_amount = (pos.entry_price - exit_price) * pos.quantity * self.config.leverage
        # 마진 반환 + PnL - 종료 수수료
        self.balance += self._locked_margin + pnl_amount - exit_fee
        self._locked_margin = 0

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
        close_qty = pos.quantity * ratio
        if pos.side == Side.LONG:
            pnl = (price - pos.entry_price) * close_qty * self.config.leverage
        else:
            pnl = (pos.entry_price - price) * close_qty * self.config.leverage
        commission = abs(close_qty * price) * self.config.commission_rate
        # 마진 부분 반환
        margin_release = self._locked_margin * ratio
        self.balance += margin_release + pnl - commission
        self._locked_margin -= margin_release
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
        """SL/TP 가격 계산. target_pct는 가격 변동 % (레버리지 미포함)."""
        ratio = target_pct / 100  # -0.5% → -0.005
        if pos.side == Side.LONG:
            return pos.entry_price * (1 + ratio)
        return pos.entry_price * (1 - ratio)

    def _apply_slippage(self, price: float, side: str, bar: OhlcvBar = None) -> float:
        """동적 슬리피지 — RCoinFutTrader 방식: 변동성에 비례하여 슬리피지 증가."""
        base_pct = self.config.slippage_pct / 100  # 0.05% → 0.0005
        if bar:
            # 봉의 변동성 = (고가 - 저가) / 종가
            volatility = (bar.high - bar.low) / bar.close if bar.close > 0 else 0
            # 동적 슬리피지 = base × (1 + volatility × 10)
            slippage = base_pct * (1.0 + volatility * 10.0)
        else:
            slippage = base_pct
        if side == "long":
            return price * (1.0 + slippage)  # 매수: 비싸게
        else:
            return price * (1.0 - slippage)  # 매도: 싸게

    def _direction_allowed(self, signal: str) -> bool:
        d = self.config.direction
        if d == "both":
            return True
        return d == signal

    def _update_equity(self, bar: OhlcvBar):
        # equity = 가용 잔고 + 잠긴 마진 + 미실현 PnL
        equity = self.balance + self._locked_margin
        if self.position:
            pos = self.position
            if pos.side == Side.LONG:
                equity += (bar.close - pos.entry_price) * pos.quantity * self.config.leverage
            else:
                equity += (pos.entry_price - bar.close) * pos.quantity * self.config.leverage
        self.equity_curve.append(max(equity, 0))
