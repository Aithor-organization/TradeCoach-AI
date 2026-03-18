"""
Futures trading engine module.

Provides USDT-M futures backtesting, indicators, metrics, and data loading.
Ported from RCoinFutTrader (Rust) to Python.
"""

from .indicators_base import SMA, EMA, RSI
from .indicators_advanced import MACD, BollingerBands, ATR, StochasticRSI
from .indicators_adx import ADX, MADDIF
from .metrics import BacktestMetrics, calculate_metrics
from .data_loader import load_futures_klines, download_futures_data
from .engine import FuturesBacktestEngine

__all__ = [
    "SMA", "EMA", "RSI",
    "MACD", "BollingerBands", "ATR", "StochasticRSI",
    "ADX", "MADDIF",
    "BacktestMetrics", "calculate_metrics",
    "load_futures_klines", "download_futures_data",
    "FuturesBacktestEngine",
]
