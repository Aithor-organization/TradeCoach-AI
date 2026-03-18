"""
ADX, DI+/DI-, and MADDIF indicators for DDIF strategy.

Ported from RCoinFutTrader/src/strategy/indicators.rs
"""

from dataclasses import dataclass, field
from .indicators_base import EMA


@dataclass
class ADX:
    """Average Directional Index with DI+/DI- components."""

    period: int = 14
    _prev_high: float = field(default=0.0, repr=False)
    _prev_low: float = field(default=0.0, repr=False)
    _prev_close: float = field(default=0.0, repr=False)
    _count: int = field(default=0, repr=False)
    _smoothed_plus_dm: float = field(default=0.0, repr=False)
    _smoothed_minus_dm: float = field(default=0.0, repr=False)
    _smoothed_tr: float = field(default=0.0, repr=False)
    _adx_ema: EMA = field(default=None, repr=False)
    di_plus: float = field(default=0.0)
    di_minus: float = field(default=0.0)
    adx_value: float = field(default=0.0)

    def __post_init__(self):
        self._adx_ema = EMA(self.period)

    def update(self, high: float, low: float, close: float) -> float:
        """Update with new OHLC bar. Returns ADX value."""
        self._count += 1
        if self._count == 1:
            self._prev_high = high
            self._prev_low = low
            self._prev_close = close
            return 0.0

        # Directional Movement
        up_move = high - self._prev_high
        down_move = self._prev_low - low
        plus_dm = max(up_move, 0.0) if up_move > down_move else 0.0
        minus_dm = max(down_move, 0.0) if down_move > up_move else 0.0

        # True Range
        tr = max(
            high - low,
            abs(high - self._prev_close),
            abs(low - self._prev_close),
        )

        self._prev_high = high
        self._prev_low = low
        self._prev_close = close

        # Wilder's smoothing
        p = self.period
        if self._count <= p + 1:
            self._smoothed_plus_dm += plus_dm
            self._smoothed_minus_dm += minus_dm
            self._smoothed_tr += tr
            if self._count == p + 1:
                self._smoothed_plus_dm /= p
                self._smoothed_minus_dm /= p
                self._smoothed_tr /= p
        else:
            self._smoothed_plus_dm = (self._smoothed_plus_dm * (p - 1) + plus_dm) / p
            self._smoothed_minus_dm = (self._smoothed_minus_dm * (p - 1) + minus_dm) / p
            self._smoothed_tr = (self._smoothed_tr * (p - 1) + tr) / p

        # DI+, DI-
        if self._smoothed_tr > 0:
            self.di_plus = (self._smoothed_plus_dm / self._smoothed_tr) * 100
            self.di_minus = (self._smoothed_minus_dm / self._smoothed_tr) * 100
        else:
            self.di_plus = 0.0
            self.di_minus = 0.0

        # DX → ADX
        di_sum = self.di_plus + self.di_minus
        dx = (abs(self.di_plus - self.di_minus) / di_sum * 100) if di_sum > 0 else 0.0
        self.adx_value = self._adx_ema.update(dx)

        return self.adx_value

    @property
    def is_ready(self) -> bool:
        return self._count > self.period * 2


@dataclass
class MADDIF:
    """Moving Average of DIF (DI+ - DI-) for DDIF strategy signals."""

    fast_period: int = 5
    slow_period: int = 20
    _fast_ema: EMA = field(default=None, repr=False)
    _slow_ema: EMA = field(default=None, repr=False)
    fast_value: float = field(default=0.0)
    slow_value: float = field(default=0.0)

    def __post_init__(self):
        self._fast_ema = EMA(self.fast_period)
        self._slow_ema = EMA(self.slow_period)

    def update(self, di_plus: float, di_minus: float) -> float:
        """Update with DI+ and DI- values. Returns fast MADDIF."""
        dif = di_plus - di_minus
        self.fast_value = self._fast_ema.update(dif)
        self.slow_value = self._slow_ema.update(dif)
        return self.fast_value

    @property
    def crossover_up(self) -> bool:
        """Fast MADDIF crossed above slow MADDIF."""
        return self.fast_value > self.slow_value

    @property
    def crossover_down(self) -> bool:
        """Fast MADDIF crossed below slow MADDIF."""
        return self.fast_value < self.slow_value

    @property
    def is_ready(self) -> bool:
        return self._slow_ema.is_ready
