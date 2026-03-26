"""
Type definitions for futures trading.

Strategy configuration, position management, and order types.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List


class Side(str, Enum):
    LONG = "long"
    SHORT = "short"


class ExitReason(str, Enum):
    TAKE_PROFIT = "tp"
    STOP_LOSS = "sl"
    TRAILING_STOP = "trailing"
    PARTIAL_EXIT = "partial"
    SIGNAL = "signal"
    LIQUIDATION = "liquidation"


def _binance_maintenance_margin(leverage: int) -> float:
    """Return Binance maintenance margin rate based on leverage tier.

    Binance USDT-M Futures maintenance margin table:
      1–10x  : 0.50%
      11–20x : 1.00%
      21–50x : 2.50%
      51–125x: 5.00%
    """
    if leverage <= 10:
        return 0.005
    elif leverage <= 20:
        return 0.01
    elif leverage <= 50:
        return 0.025
    else:
        return 0.05


@dataclass
class FuturesConfig:
    """Futures backtest configuration."""
    symbol: str = "BTCUSDT"
    leverage: int = 10
    direction: str = "both"  # "long", "short", "both"
    commission_rate: float = 0.0004  # 0.04% taker fee
    slippage_ticks: int = 1
    slippage_pct: float = 0.05  # 0.05% slippage (현실적 크립토 선물)

    # Risk management
    stop_loss_pct: float = -0.4
    take_profit_pct: float = 1.5

    # Partial exit
    partial_exit_enabled: bool = True
    partial_exit_pct: float = 1.2
    partial_exit_ratio: float = 0.5

    # Trailing stop
    trailing_stop_enabled: bool = True
    trailing_trigger_pct: float = 0.9
    trailing_callback_pct: float = 0.2

    # Capital & Position — 전체 자본 투입 (BinanceTrader 방식)
    initial_capital: float = 1000.0  # 초기 총 자본금
    investment: float = 1000.0  # 포지션당 투자금 = 전체 자본

    @classmethod
    def from_strategy_json(cls, strategy: dict) -> "FuturesConfig":
        """Create config from parsed strategy JSON."""
        risk = strategy.get("risk", {})
        exit_cfg = strategy.get("exit", {})
        tp = exit_cfg.get("take_profit", {})
        sl = exit_cfg.get("stop_loss", {})
        pe = risk.get("partial_exit", exit_cfg.get("partial_exit", {}))
        ts = risk.get("trailing_stop", exit_cfg.get("trailing_stop", {}))
        pos = strategy.get("position", {})

        return cls(
            symbol=strategy.get("target_pair", "BTCUSDT").replace("/", ""),
            leverage=strategy.get("leverage", 10),
            direction=strategy.get("direction", "both"),
            stop_loss_pct=sl.get("value", -0.4),
            take_profit_pct=tp.get("value", 1.5),
            partial_exit_enabled=pe.get("enabled", False),
            partial_exit_pct=pe.get("at_pct", pe.get("at_percent", 1.2)),
            partial_exit_ratio=pe.get("ratio", pe.get("sell_ratio", 0.5)),
            trailing_stop_enabled=ts.get("enabled", False),
            trailing_trigger_pct=ts.get("trigger_pct", 0.9),
            trailing_callback_pct=ts.get("callback_pct", 0.2),
            investment=pos.get("size_value", 1000.0),
        )


@dataclass
class Position:
    """Active futures position."""
    side: Side
    entry_price: float
    quantity: float
    leverage: int
    entry_time: str
    highest_price: float = 0.0
    lowest_price: float = 0.0
    partial_exited: bool = False

    @property
    def liquidation_price(self) -> float:
        """Liquidation price based on Binance maintenance margin table.

        Formula:
          LONG : entry * (1 - (1/leverage - maintenance_margin))
          SHORT: entry * (1 + (1/leverage - maintenance_margin))
        """
        mm = _binance_maintenance_margin(self.leverage)
        factor = (1.0 / self.leverage) - mm
        if self.side == Side.LONG:
            return self.entry_price * (1.0 - factor)
        return self.entry_price * (1.0 + factor)

    def unrealized_pnl(self, current_price: float) -> float:
        if self.side == Side.LONG:
            return (current_price - self.entry_price) / self.entry_price * 100 * self.leverage
        return (self.entry_price - current_price) / self.entry_price * 100 * self.leverage
