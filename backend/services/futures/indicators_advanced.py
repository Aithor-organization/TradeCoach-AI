"""
Advanced technical indicators: MACD, Bollinger Bands, ATR, Stochastic RSI.

Ported from RCoinFutTrader/src/backtester/indicators.rs
"""

from dataclasses import dataclass, field
import math
from .indicators_base import EMA, SMA, RSI


@dataclass
class MACD:
    """MACD (Moving Average Convergence Divergence)."""

    fast_period: int = 12
    slow_period: int = 26
    signal_period: int = 9
    _fast_ema: EMA = field(default=None, repr=False)
    _slow_ema: EMA = field(default=None, repr=False)
    _signal_ema: EMA = field(default=None, repr=False)
    macd_line: float = field(default=0.0)
    signal_line: float = field(default=0.0)
    histogram: float = field(default=0.0)

    def __post_init__(self):
        self._fast_ema = EMA(self.fast_period)
        self._slow_ema = EMA(self.slow_period)
        self._signal_ema = EMA(self.signal_period)

    def update(self, close: float) -> float:
        fast = self._fast_ema.update(close)
        slow = self._slow_ema.update(close)
        self.macd_line = fast - slow
        self.signal_line = self._signal_ema.update(self.macd_line)
        self.histogram = self.macd_line - self.signal_line
        return self.histogram

    @property
    def is_ready(self) -> bool:
        return self._slow_ema.is_ready


@dataclass
class BollingerBands:
    """Bollinger Bands with configurable standard deviation multiplier."""

    period: int = 20
    std_dev: float = 2.0
    _sma: SMA = field(default=None, repr=False)
    _values: list = field(default_factory=list, repr=False)
    upper: float = field(default=0.0)
    middle: float = field(default=0.0)
    lower: float = field(default=0.0)

    def __post_init__(self):
        self._sma = SMA(self.period)
        self._values = []

    def update(self, close: float) -> float:
        self.middle = self._sma.update(close)
        self._values.append(close)
        if len(self._values) > self.period:
            self._values.pop(0)

        if len(self._values) >= self.period:
            variance = sum((v - self.middle) ** 2 for v in self._values) / self.period
            std = math.sqrt(variance)
            self.upper = self.middle + self.std_dev * std
            self.lower = self.middle - self.std_dev * std

        return self.middle

    @property
    def is_ready(self) -> bool:
        return self._sma.is_ready


@dataclass
class ATR:
    """Average True Range for volatility measurement."""

    period: int = 14
    _prev_close: float = field(default=0.0, repr=False)
    _count: int = field(default=0, repr=False)
    _atr: float = field(default=0.0, repr=False)

    def update(self, high: float, low: float, close: float) -> float:
        self._count += 1
        if self._count == 1:
            tr = high - low
        else:
            tr = max(
                high - low,
                abs(high - self._prev_close),
                abs(low - self._prev_close),
            )
        self._prev_close = close

        if self._count <= self.period:
            self._atr = (self._atr * (self._count - 1) + tr) / self._count
        else:
            self._atr = (self._atr * (self.period - 1) + tr) / self.period
        return self._atr

    @property
    def value(self) -> float:
        return self._atr

    @property
    def is_ready(self) -> bool:
        return self._count >= self.period


@dataclass
class StochasticRSI:
    """Stochastic RSI oscillator (0-100)."""

    rsi_period: int = 14
    stoch_period: int = 14
    _rsi: RSI = field(default=None, repr=False)
    _rsi_values: list = field(default_factory=list, repr=False)
    k_value: float = field(default=50.0)
    d_value: float = field(default=50.0)
    _k_sma: SMA = field(default=None, repr=False)

    def __post_init__(self):
        self._rsi = RSI(self.rsi_period)
        self._k_sma = SMA(3)  # %D = 3-period SMA of %K

    def update(self, close: float) -> float:
        rsi_val = self._rsi.update(close)
        self._rsi_values.append(rsi_val)
        if len(self._rsi_values) > self.stoch_period:
            self._rsi_values.pop(0)

        if len(self._rsi_values) >= self.stoch_period:
            rsi_min = min(self._rsi_values)
            rsi_max = max(self._rsi_values)
            rsi_range = rsi_max - rsi_min
            self.k_value = ((rsi_val - rsi_min) / rsi_range * 100.0) if rsi_range > 0 else 50.0
            self.d_value = self._k_sma.update(self.k_value)

        return self.k_value

    @property
    def is_ready(self) -> bool:
        return self._rsi.is_ready and len(self._rsi_values) >= self.stoch_period
