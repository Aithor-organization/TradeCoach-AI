"""
Walk-Forward Analysis — 과최적화(Overfitting) 탐지를 위한 전진 검증 모듈.

In-Sample(IS) 구간에서 최적 파라미터를 탐색하고,
Out-of-Sample(OOS) 구간에서 실 성능을 측정해 전략의 강건성을 판단한다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal

from .data_loader import OhlcvBar
from .engine import FuturesBacktestEngine
from .optimizer import run_optimization
from .types import FuturesConfig

logger = logging.getLogger(__name__)

# OOS/IS 비율이 이 값 이상이면 과최적화 없음으로 판정
_PASS_THRESHOLD = 0.5

# objective → BacktestMetrics 속성 매핑
_OBJECTIVE_ATTR: Dict[str, str] = {
    "sharpe": "sharpe_ratio",
    "calmar": "calmar_ratio",
    "profit_factor": "profit_factor",
    "total_return": "total_return",
}


@dataclass
class WindowResult:
    """단일 윈도우(IS+OOS) 분석 결과."""

    window_index: int
    is_start_ts: int       # In-Sample 시작 timestamp (ms)
    is_end_ts: int         # In-Sample 종료 timestamp (ms)
    oos_start_ts: int      # OOS 시작 timestamp (ms)
    oos_end_ts: int        # OOS 종료 timestamp (ms)
    best_params: Dict[str, Any]
    is_metrics: Dict[str, Any]
    oos_metrics: Dict[str, Any]
    ratio: float           # OOS목표지표 / IS목표지표 (클수록 과최적화 없음)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "window_index": self.window_index,
            "is_period": {
                "start_ts": self.is_start_ts,
                "end_ts": self.is_end_ts,
            },
            "oos_period": {
                "start_ts": self.oos_start_ts,
                "end_ts": self.oos_end_ts,
            },
            "best_params": self.best_params,
            "is_metrics": self.is_metrics,
            "oos_metrics": self.oos_metrics,
            "ratio": round(self.ratio, 4),
        }


@dataclass
class WalkForwardResult:
    """Walk-Forward Analysis 최종 결과."""

    windows: List[WindowResult] = field(default_factory=list)
    avg_ratio: float = 0.0
    passed: bool = False           # avg_ratio >= 0.5 → 강건성 검증 통과
    recommended_params: Dict[str, Any] = field(default_factory=dict)
    method: Literal["anchored", "sliding"] = "anchored"
    objective: str = "sharpe"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "objective": self.objective,
            "avg_ratio": round(self.avg_ratio, 4),
            "avg_oos_is_ratio": round(self.avg_ratio, 4),  # 별칭
            "passed": self.passed,
            "recommended_params": self.recommended_params,
            "windows": [w.to_dict() for w in self.windows],
        }


def run_walk_forward(
    bars: List[OhlcvBar],
    strategy: Dict[str, Any],
    param_ranges: Dict[str, Any],
    *,
    in_sample_days: int = 270,
    out_sample_days: int = 90,
    windows: int = 4,
    objective: str = "sharpe",
    mode: Literal["anchored", "sliding"] = "anchored",
) -> WalkForwardResult:
    """
    Walk-Forward Analysis 실행.

    Args:
        bars: 시계열 순 정렬된 OHLCV 캔들 목록.
        strategy: 전략 JSON (entry/exit 조건, 리스크 파라미터 등).
        param_ranges: 최적화 파라미터 탐색 범위 dict.
        in_sample_days: IS 구간 길이 (일).
        out_sample_days: OOS 구간 길이 (일).
        windows: 분석 윈도우 수.
        objective: 최적화 목표 지표 ("sharpe" | "calmar" | "profit_factor" | "total_return").
        mode: "anchored" — IS 시작점 고정, 늘어남 / "sliding" — IS 슬라이딩.

    Returns:
        WalkForwardResult: 윈도우별 결과, 평균 비율, 합격 여부, 추천 파라미터.
    """
    if not bars:
        raise ValueError("bars 목록이 비어 있습니다.")
    if objective not in _OBJECTIVE_ATTR:
        raise ValueError(
            f"지원하지 않는 objective: '{objective}'. "
            f"허용 값: {list(_OBJECTIVE_ATTR)}"
        )

    # 캔들 하나당 ms 간격 추정 (첫 두 캔들 차이)
    bar_ms = bars[1].timestamp - bars[0].timestamp if len(bars) > 1 else 3_600_000

    ms_per_day = 86_400_000
    is_ms = in_sample_days * ms_per_day
    oos_ms = out_sample_days * ms_per_day
    window_step_ms = oos_ms  # 각 윈도우는 OOS 길이만큼 전진

    # 첫 윈도우: 앵커드 → 인덱스 0부터 IS, 슬라이딩 → 동일
    first_is_start = bars[0].timestamp

    window_results: List[WindowResult] = []

    for idx in range(windows):
        # ── IS/OOS 시간 범위 계산 ──────────────────────────────────────────
        if mode == "anchored":
            is_start_ts = first_is_start
            is_end_ts = first_is_start + is_ms + idx * window_step_ms
        else:  # sliding
            is_start_ts = first_is_start + idx * window_step_ms
            is_end_ts = is_start_ts + is_ms

        oos_start_ts = is_end_ts
        oos_end_ts = oos_start_ts + oos_ms

        # 데이터 범위 초과 시 조기 종료
        if oos_end_ts > bars[-1].timestamp + bar_ms:
            logger.warning(
                "윈도우 %d: OOS 종료(%s)가 데이터 범위를 벗어납니다. 중단.",
                idx,
                oos_end_ts,
            )
            break

        # ── 해당 구간 캔들 슬라이싱 ──────────────────────────────────────
        is_bars = _slice_bars(bars, is_start_ts, is_end_ts)
        oos_bars = _slice_bars(bars, oos_start_ts, oos_end_ts)

        if len(is_bars) < 10 or len(oos_bars) < 5:
            logger.warning(
                "윈도우 %d: 캔들 수 부족 (IS=%d, OOS=%d). 건너뜀.",
                idx, len(is_bars), len(oos_bars),
            )
            continue

        # ── IS 구간 최적화 ───────────────────────────────────────────────
        logger.info(
            "윈도우 %d | IS %d봉 최적화 시작 (objective=%s)...",
            idx, len(is_bars), objective,
        )
        opt_results = run_optimization(
            bars=is_bars,
            strategy=strategy,
            param_ranges=param_ranges,
            objective=objective,
            top_n=1,
        )
        if not opt_results:
            logger.warning("윈도우 %d: 최적화 결과 없음. 건너뜀.", idx)
            continue

        best_params: Dict[str, Any] = opt_results[0]["params"]
        is_metrics_raw = opt_results[0]["metrics"]

        # ── OOS 구간 백테스트 ────────────────────────────────────────────
        oos_strategy = {**strategy, **best_params}
        config = FuturesConfig.from_strategy_json(oos_strategy)
        engine = FuturesBacktestEngine(config)
        oos_metrics_obj = engine.run(oos_bars, oos_strategy)

        # ── OOS/IS 비율 산출 ─────────────────────────────────────────────
        attr = _OBJECTIVE_ATTR[objective]
        is_score = (
            is_metrics_raw.get(attr, 0.0)
            if isinstance(is_metrics_raw, dict)
            else getattr(is_metrics_raw, attr, 0.0)
        )
        oos_score = getattr(oos_metrics_obj, attr, 0.0)
        ratio = _safe_ratio(oos_score, is_score)

        # IS 메트릭을 dict 형태로 정규화
        if isinstance(is_metrics_raw, dict):
            is_metrics_dict = is_metrics_raw
        else:
            is_metrics_dict = is_metrics_raw.to_dict()

        window_results.append(
            WindowResult(
                window_index=idx,
                is_start_ts=is_start_ts,
                is_end_ts=is_end_ts,
                oos_start_ts=oos_start_ts,
                oos_end_ts=oos_end_ts,
                best_params=best_params,
                is_metrics=is_metrics_dict,
                oos_metrics=oos_metrics_obj.to_dict(),
                ratio=ratio,
            )
        )
        logger.info(
            "윈도우 %d 완료 | IS %.4f / OOS %.4f → ratio=%.3f",
            idx, is_score, oos_score, ratio,
        )

    # ── 전체 집계 ─────────────────────────────────────────────────────────
    if not window_results:
        logger.error("유효한 윈도우가 없습니다. 빈 결과 반환.")
        return WalkForwardResult(method=mode, objective=objective)

    avg_ratio = sum(w.ratio for w in window_results) / len(window_results)
    passed = avg_ratio >= _PASS_THRESHOLD

    # 추천 파라미터: 마지막 윈도우(가장 최근 IS)의 최적 파라미터
    recommended_params = window_results[-1].best_params

    logger.info(
        "Walk-Forward 완료 | 윈도우=%d, avg_ratio=%.3f, passed=%s",
        len(window_results), avg_ratio, passed,
    )

    return WalkForwardResult(
        windows=window_results,
        avg_ratio=avg_ratio,
        passed=passed,
        recommended_params=recommended_params,
        method=mode,
        objective=objective,
    )


# ── 내부 유틸리티 ──────────────────────────────────────────────────────────


def _slice_bars(
    bars: List[OhlcvBar], start_ts: int, end_ts: int
) -> List[OhlcvBar]:
    """[start_ts, end_ts) 범위에 속하는 캔들만 반환."""
    return [b for b in bars if start_ts <= b.timestamp < end_ts]


def _safe_ratio(oos_score: float, is_score: float) -> float:
    """
    OOS/IS 비율을 안전하게 계산.

    IS 점수가 0이거나 음수인 엣지 케이스를 처리한다:
    - IS=0, OOS=0 → 0.0 (성과 없음)
    - IS≤0, OOS>0 → 1.0 (IS가 나쁜데 OOS가 좋으면 강건하다고 간주)
    - IS≤0, OOS≤0 → 0.0
    """
    if is_score <= 0:
        return 1.0 if oos_score > 0 else 0.0
    return oos_score / is_score
