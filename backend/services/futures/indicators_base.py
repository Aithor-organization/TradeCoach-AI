"""
Base technical indicators with incremental O(1) updates.

Ported from RCoinFutTrader/src/backtester/indicators.rs
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class SMA:
    """Simple Moving Average with ring buffer for O(1) updates."""

    period: int
    _buffer: List[float] = field(default_factory=list, repr=False)
    _sum: float = field(default=0.0, repr=False)
    _pos: int = field(default=0, repr=False)
    _filled: bool = field(default=False, repr=False)

    def __post_init__(self):
        self._buffer = [0.0] * self.period

    def update(self, value: float) -> float:
        """Add new value and return current SMA."""
        self._sum -= self._buffer[self._pos]
        self._sum += value
        self._buffer[self._pos] = value
        self._pos += 1
        if self._pos >= self.period:
            self._pos = 0
            self._filled = True
        return self.value

    @property
    def value(self) -> float:
        if self._filled:
            return self._sum / self.period
        return self._sum / max(self._pos, 1)

    @property
    def is_ready(self) -> bool:
        return self._filled

    def reset(self):
        self._buffer = [0.0] * self.period
        self._sum = 0.0
        self._pos = 0
        self._filled = False


@dataclass
class EMA:
    """Exponential Moving Average with O(1) updates."""

    period: int
    _value: float = field(default=0.0, repr=False)
    _multiplier: float = field(default=0.0, repr=False)
    _count: int = field(default=0, repr=False)

    def __post_init__(self):
        self._multiplier = 2.0 / (self.period + 1.0)

    def update(self, price: float) -> float:
        """Add new price and return current EMA."""
        self._count += 1
        if self._count == 1:
            self._value = price
        else:
            self._value = (price - self._value) * self._multiplier + self._value
        return self._value

    @property
    def value(self) -> float:
        return self._value

    @property
    def is_ready(self) -> bool:
        return self._count >= self.period

    def reset(self):
        self._value = 0.0
        self._count = 0


@dataclass
class RSI:
    """Relative Strength Index using Wilder's smoothing."""

    period: int = 14
    _avg_gain: float = field(default=0.0, repr=False)
    _avg_loss: float = field(default=0.0, repr=False)
    _prev_close: float = field(default=0.0, repr=False)
    _count: int = field(default=0, repr=False)
    _gains_sum: float = field(default=0.0, repr=False)
    _losses_sum: float = field(default=0.0, repr=False)

    def update(self, close: float) -> float:
        """Add new close price and return current RSI (0-100)."""
        self._count += 1
        if self._count == 1:
            self._prev_close = close
            return 50.0

        change = close - self._prev_close
        self._prev_close = close
        gain = max(change, 0.0)
        loss = max(-change, 0.0)

        if self._count <= self.period + 1:
            self._gains_sum += gain
            self._losses_sum += loss
            if self._count == self.period + 1:
                self._avg_gain = self._gains_sum / self.period
                self._avg_loss = self._losses_sum / self.period
        else:
            p = self.period
            self._avg_gain = (self._avg_gain * (p - 1) + gain) / p
            self._avg_loss = (self._avg_loss * (p - 1) + loss) / p

        return self.value

    @property
    def value(self) -> float:
        if self._avg_loss == 0.0:
            return 50.0 if self._avg_gain == 0.0 else 100.0
        rs = self._avg_gain / self._avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    @property
    def is_ready(self) -> bool:
        return self._count > self.period

    def reset(self):
        self._avg_gain = self._avg_loss = 0.0
        self._prev_close = 0.0
        self._count = 0
        self._gains_sum = self._losses_sum = 0.0
