"""
Performance metrics for futures backtesting.

Ported from RCoinFutTrader/src/backtester/metrics.rs
Includes: MDD, CAGR, Sharpe, Calmar, Profit Factor, Win Rate, etc.
"""

from dataclasses import dataclass
from typing import List, Optional
import math


@dataclass
class TradeRecord:
    """Single trade record."""
    entry_price: float
    exit_price: float
    side: str  # "long" or "short"
    pnl: float
    return_pct: float
    entry_time: str
    exit_time: str
    exit_reason: str  # "tp", "sl", "trailing", "signal", "liquidation"
    leverage: int = 1


@dataclass
class BacktestMetrics:
    """Comprehensive backtest performance metrics."""
    total_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    cagr: float = 0.0
    profit_factor: float = 0.0
    calmar_ratio: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    max_consecutive_losses: int = 0
    long_trades: int = 0
    short_trades: int = 0
    long_win_rate: float = 0.0
    short_win_rate: float = 0.0
    init_cash: float = 1000.0

    def to_dict(self) -> dict:
        return {k: round(v, 4) if isinstance(v, float) else v
                for k, v in self.__dict__.items()}


def calculate_metrics(
    trades: List[TradeRecord],
    equity_curve: List[float],
    init_cash: float = 1000.0,
    days: Optional[int] = None,
) -> BacktestMetrics:
    """Calculate all performance metrics from trade list and equity curve."""
    m = BacktestMetrics(init_cash=init_cash)
    if not trades:
        return m

    m.total_trades = len(trades)
    m.total_return = ((equity_curve[-1] / init_cash) - 1) * 100 if equity_curve else 0

    # Win/Loss분류
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    m.win_rate = (len(wins) / m.total_trades * 100) if m.total_trades > 0 else 0

    # Long/Short 별도 통계
    longs = [t for t in trades if t.side == "long"]
    shorts = [t for t in trades if t.side == "short"]
    m.long_trades = len(longs)
    m.short_trades = len(shorts)
    long_wins = [t for t in longs if t.pnl > 0]
    short_wins = [t for t in shorts if t.pnl > 0]
    m.long_win_rate = (len(long_wins) / len(longs) * 100) if longs else 0
    m.short_win_rate = (len(short_wins) / len(shorts) * 100) if shorts else 0

    # Avg Win/Loss
    m.avg_win = (sum(t.pnl for t in wins) / len(wins)) if wins else 0
    m.avg_loss = (sum(t.pnl for t in losses) / len(losses)) if losses else 0

    # Profit Factor
    gross_profit = sum(t.pnl for t in wins)
    gross_loss = abs(sum(t.pnl for t in losses))
    m.profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")

    # Max Consecutive Losses
    m.max_consecutive_losses = _max_consecutive_losses(trades)

    # MDD from equity curve
    m.max_drawdown = _calculate_mdd(equity_curve) if equity_curve else 0

    # CAGR
    if days and days > 0 and equity_curve:
        years = days / 365.25
        final_ratio = equity_curve[-1] / init_cash
        m.cagr = ((final_ratio ** (1 / years)) - 1) * 100 if years > 0 and final_ratio > 0 else 0

    # Sharpe Ratio (daily returns)
    if len(equity_curve) >= 2:
        returns = [(equity_curve[i] / equity_curve[i - 1]) - 1
                   for i in range(1, len(equity_curve))]
        avg_ret = sum(returns) / len(returns)
        std_ret = math.sqrt(sum((r - avg_ret) ** 2 for r in returns) / len(returns))
        m.sharpe_ratio = (avg_ret / std_ret * math.sqrt(252)) if std_ret > 0 else 0

    # Calmar Ratio
    m.calmar_ratio = (m.cagr / abs(m.max_drawdown)) if m.max_drawdown != 0 else 0

    return m


def _calculate_mdd(equity: List[float]) -> float:
    """Calculate maximum drawdown percentage."""
    if not equity:
        return 0.0
    peak = equity[0]
    max_dd = 0.0
    for val in equity:
        if val > peak:
            peak = val
        dd = ((val - peak) / peak) * 100
        if dd < max_dd:
            max_dd = dd
    return max_dd


def _max_consecutive_losses(trades: List[TradeRecord]) -> int:
    """Count maximum consecutive losing trades."""
    max_streak = 0
    current = 0
    for t in trades:
        if t.pnl <= 0:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    return max_streak
