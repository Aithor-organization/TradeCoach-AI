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


@dataclass
class FuturesConfig:
    """Futures backtest configuration."""
    symbol: str = "BTCUSDT"
    leverage: int = 10
    direction: str = "both"  # "long", "short", "both"
    commission_rate: float = 0.0004  # 0.04% taker fee
    slippage_ticks: int = 1

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

    # Position
    investment: float = 1000.0

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
        """Approximate liquidation price (simplified)."""
        margin_ratio = 1.0 / self.leverage
        if self.side == Side.LONG:
            return self.entry_price * (1 - margin_ratio + 0.006)
        return self.entry_price * (1 + margin_ratio - 0.006)

    def unrealized_pnl(self, current_price: float) -> float:
        if self.side == Side.LONG:
            return (current_price - self.entry_price) / self.entry_price * 100 * self.leverage
        return (self.entry_price - current_price) / self.entry_price * 100 * self.leverage
