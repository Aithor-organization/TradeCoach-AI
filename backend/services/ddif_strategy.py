"""
DDIF 전략 엔진 — ADX/DI + 볼린저 + MADDIF 멀티타임프레임 전략.

15분봉 필터: MADDIF1 > threshold → 매수/매도 준비 상태
3분봉 진입: 준비 상태에서 MADDIF 크로스오버 → Long/Short 진입
15분봉 반전 신호 → 포지션 청산

포팅 원본: RCoinFutTrader/src/strategy/logic.rs
"""

import logging
from dataclasses import dataclass
from typing import Optional

from services.futures.indicators_adx import ADX, MADDIF

logger = logging.getLogger(__name__)


@dataclass
class DDIFSignal:
    """DDIF 전략 신호"""
    side: Optional[str] = None  # "long", "short", None
    reason: str = ""
    strength: float = 0.0


class DDIFStrategy:
    """
    DDIF 멀티타임프레임 전략.

    15분봉으로 방향 필터링, 3분봉으로 진입 시점 포착.
    """

    def __init__(
        self,
        maddif_threshold: float = 0.05,
        adx_period: int = 14,
        ema_period: int = 9,
    ):
        self.maddif_threshold = maddif_threshold
        self.adx_period = adx_period
        self.ema_period = ema_period

        # 15분봉 필터 상태
        self._filter_bias: Optional[str] = None  # "long" | "short" | None
        self._filter_maddif_prev: float = 0.0

        # 3분봉 진입 인디케이터
        self._entry_maddif_prev: float = 0.0
        self._entry_adx_values: list[float] = []
        self._entry_di_plus: list[float] = []
        self._entry_di_minus: list[float] = []

    def update_filter(self, bar: dict) -> None:
        """
        15분봉 필터 업데이트.

        MADDIF1이 threshold를 상향 돌파하면 매수 준비,
        하향 돌파하면 매도 준비 상태로 전환.
        """
        high = bar.get("high", 0)
        low = bar.get("low", 0)
        close = bar.get("close", 0)

        # 간소화된 MADDIF 계산 (ADX 기반)
        adx = ADX(period=self.adx_period)
        adx.update(high, low, close)
        maddif1 = adx.di_plus - adx.di_minus

        # 크로스오버 감지
        if self._filter_maddif_prev <= self.maddif_threshold < maddif1:
            self._filter_bias = "long"
        elif self._filter_maddif_prev >= -self.maddif_threshold > maddif1:
            self._filter_bias = "short"

        # 반전 감지 (포지션 청산 시그널)
        if self._filter_bias == "long" and maddif1 < -self.maddif_threshold:
            self._filter_bias = None
        elif self._filter_bias == "short" and maddif1 > self.maddif_threshold:
            self._filter_bias = None

        self._filter_maddif_prev = maddif1

    def evaluate_entry(self, bar: dict) -> DDIFSignal:
        """
        3분봉 진입 신호 평가.

        필터가 활성 상태일 때만 진입 신호 생성.
        """
        if self._filter_bias is None:
            return DDIFSignal(reason="no_filter_bias")

        high = bar.get("high", 0)
        low = bar.get("low", 0)
        close = bar.get("close", 0)

        # 3분봉 MADDIF
        adx = ADX(period=self.adx_period)
        adx.update(high, low, close)
        maddif_entry = adx.di_plus - adx.di_minus

        # 크로스오버 감지
        signal = DDIFSignal()
        crossed_up = self._entry_maddif_prev < 0 <= maddif_entry
        crossed_down = self._entry_maddif_prev > 0 >= maddif_entry

        if self._filter_bias == "long" and crossed_up:
            signal.side = "long"
            signal.reason = "maddif_crossover_up"
            signal.strength = abs(maddif_entry)
        elif self._filter_bias == "short" and crossed_down:
            signal.side = "short"
            signal.reason = "maddif_crossover_down"
            signal.strength = abs(maddif_entry)

        self._entry_maddif_prev = maddif_entry
        return signal

    def should_close(self) -> bool:
        """
        15분봉 반전으로 포지션 청산이 필요한지 확인.

        filter_bias가 None이 되면 청산 시그널.
        """
        return self._filter_bias is None

    @property
    def current_bias(self) -> Optional[str]:
        """현재 필터 방향"""
        return self._filter_bias

    def reset(self) -> None:
        """상태 초기화"""
        self._filter_bias = None
        self._filter_maddif_prev = 0.0
        self._entry_maddif_prev = 0.0
