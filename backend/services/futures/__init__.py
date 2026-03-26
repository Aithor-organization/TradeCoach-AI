"""
Futures trading engine module.

Provides USDT-M futures backtesting, indicators, metrics, and data loading.
Ported from RCoinFutTrader (Rust) to Python.
"""

from .indicators_base import SMA, EMA, RSI
from .indicators_advanced import MACD, BollingerBands, ATR, StochasticRSI
from .indicators_adx import ADX, MADDIF
from .indicators_extended import (
    adx, di_plus, di_minus, sar, aroon_up, aroon_down,
    cci, mom, roc, willr, mfi, apo, ppo,
    obv, ad, adosc,
    ema_60, ema_120, sma_60,
    ddif, maddif, maddif1,
)
from .metrics import BacktestMetrics, calculate_metrics
from .data_loader import load_futures_klines, download_futures_data
from .engine import FuturesBacktestEngine
from .backtest_runner import execute_futures_backtest
from .optimizer import run_optimization, run_grid_search
from .walk_forward import run_walk_forward
from .isoos_runner import ISOOSRunner, ISOOSResult

__all__ = [
    # Stateful indicator classes (streaming / incremental)
    "SMA", "EMA", "RSI",
    "MACD", "BollingerBands", "ATR", "StochasticRSI",
    "ADX", "MADDIF",
    # Batch indicator functions (NumPy, OHLCV arrays)
    "adx", "di_plus", "di_minus", "sar", "aroon_up", "aroon_down",
    "cci", "mom", "roc", "willr", "mfi", "apo", "ppo",
    "obv", "ad", "adosc",
    "ema_60", "ema_120", "sma_60",
    "ddif", "maddif", "maddif1",
    # Metrics
    "BacktestMetrics", "calculate_metrics",
    # Data
    "load_futures_klines", "download_futures_data",
    # Engine
    "FuturesBacktestEngine",
    "execute_futures_backtest",
    # Optimisation
    "run_optimization",
    "run_grid_search",
    "run_walk_forward",
    # IS/OOS
    "ISOOSRunner", "ISOOSResult",
]
