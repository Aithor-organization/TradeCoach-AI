"""
In-Sample / Out-of-Sample (IS/OOS) overfitting detection runner.

Splits historical data 2/3 (IS) + 1/3 (OOS), runs a backtest on each
segment and on the full dataset, then computes an overfitting score and
a plain-language recommendation.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from .data_loader import OhlcvBar
from .types import FuturesConfig
from .engine import FuturesBacktestEngine
from .metrics import BacktestMetrics


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ISOOSResult:
    """Holds IS/OOS analysis results."""

    # Segment metrics
    is_metrics: BacktestMetrics
    oos_metrics: BacktestMetrics
    full_metrics: BacktestMetrics

    # Counts
    is_bars: int
    oos_bars: int
    total_bars: int

    # Overfitting score: 0.0 (no overfitting) → 1.0 (complete overfitting)
    # Formula: max(0, 1 - oos_return / is_return)
    # When is_return <= 0 the strategy is already losing in-sample; score = 1.0
    overfitting_score: float

    # "SAFE", "CAUTIOUS", "RISKY", "REJECT"
    recommendation: str

    # Human-readable explanation
    explanation: str

    def to_dict(self) -> dict:
        """Serialise to a JSON-safe dictionary."""
        return {
            "is_metrics": self.is_metrics.to_dict(),
            "oos_metrics": self.oos_metrics.to_dict(),
            "full_metrics": self.full_metrics.to_dict(),
            "is_bars": self.is_bars,
            "oos_bars": self.oos_bars,
            "total_bars": self.total_bars,
            "overfitting_score": round(self.overfitting_score, 4),
            "recommendation": self.recommendation,
            "explanation": self.explanation,
        }


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

class ISOOSRunner:
    """
    Runs IS/OOS split analysis to detect strategy overfitting.

    Algorithm
    ---------
    1. Split ``bars`` into IS (first 2/3) and OOS (last 1/3).
    2. Run ``FuturesBacktestEngine`` on each segment and on the full dataset.
    3. Compute ``overfitting_score = max(0, 1 - oos_return / is_return)``.
       - If ``is_return <= 0``: score = 1.0 (strategy fails in-sample).
       - If ``oos_return >= is_return``: score = 0.0 (no degradation).
    4. Map score to recommendation tier:
       - SAFE     : score <= 0.50 (OOS ≥ 50 % of IS performance)
       - CAUTIOUS : 0.50 < score <= 0.75 (OOS 25–50 % of IS)
       - RISKY    : 0.75 < score <= 0.90 (OOS 10–25 % of IS)
       - REJECT   : score > 0.90 (OOS < 10 % of IS)
    """

    MIN_BARS_PER_SEGMENT = 20  # minimum bars needed for a meaningful backtest

    def __init__(self, config: FuturesConfig):
        self.config = config

    def run(self, bars: List[OhlcvBar], strategy: Dict[str, Any]) -> ISOOSResult:
        """
        Execute IS/OOS analysis.

        Args:
            bars: Full OHLCV bar list (chronological order).
            strategy: Parsed strategy JSON dict.

        Returns:
            ISOOSResult with metrics, overfitting score and recommendation.

        Raises:
            ValueError: If there are not enough bars for a valid split.
        """
        total = len(bars)
        split = total * 2 // 3
        is_bars = bars[:split]
        oos_bars = bars[split:]

        if len(is_bars) < self.MIN_BARS_PER_SEGMENT:
            raise ValueError(
                f"IS segment has only {len(is_bars)} bars "
                f"(minimum {self.MIN_BARS_PER_SEGMENT} required)."
            )
        if len(oos_bars) < self.MIN_BARS_PER_SEGMENT:
            raise ValueError(
                f"OOS segment has only {len(oos_bars)} bars "
                f"(minimum {self.MIN_BARS_PER_SEGMENT} required)."
            )

        is_metrics = self._run_segment(is_bars, strategy)
        oos_metrics = self._run_segment(oos_bars, strategy)
        full_metrics = self._run_segment(bars, strategy)

        overfitting_score, recommendation, explanation = self._evaluate(
            is_metrics, oos_metrics
        )

        return ISOOSResult(
            is_metrics=is_metrics,
            oos_metrics=oos_metrics,
            full_metrics=full_metrics,
            is_bars=len(is_bars),
            oos_bars=len(oos_bars),
            total_bars=total,
            overfitting_score=overfitting_score,
            recommendation=recommendation,
            explanation=explanation,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _run_segment(
        self, bars: List[OhlcvBar], strategy: Dict[str, Any]
    ) -> BacktestMetrics:
        """Run a fresh engine instance on a bar segment."""
        engine = FuturesBacktestEngine(self.config)
        return engine.run(bars, strategy)

    @staticmethod
    def _evaluate(
        is_metrics: BacktestMetrics,
        oos_metrics: BacktestMetrics,
    ):
        """
        Compute overfitting score and recommendation.

        Returns:
            (overfitting_score, recommendation, explanation)
        """
        is_ret = is_metrics.total_return
        oos_ret = oos_metrics.total_return

        # If IS itself is losing, no point deploying
        if is_ret <= 0:
            score = 1.0
            rec = "REJECT"
            explanation = (
                f"In-sample return is {is_ret:.2f}% (non-positive). "
                "The strategy does not work even on training data. "
                "Do not deploy."
            )
            return score, rec, explanation

        # Core score
        ratio = oos_ret / is_ret  # can be negative
        score = max(0.0, 1.0 - ratio)

        # Recommendation tiers
        if score <= 0.50:
            rec = "SAFE"
            explanation = (
                f"OOS return ({oos_ret:.2f}%) is ≥ 50% of IS return ({is_ret:.2f}%). "
                "Performance degradation is within acceptable limits. "
                "The strategy generalises well."
            )
        elif score <= 0.75:
            rec = "CAUTIOUS"
            explanation = (
                f"OOS return ({oos_ret:.2f}%) is 25–50% of IS return ({is_ret:.2f}%). "
                "Moderate overfitting detected. "
                "Consider loosening entry conditions or reducing parameter complexity."
            )
        elif score <= 0.90:
            rec = "RISKY"
            explanation = (
                f"OOS return ({oos_ret:.2f}%) is only 10–25% of IS return ({is_ret:.2f}%). "
                "Significant overfitting. "
                "The strategy is unlikely to perform well live without major revisions."
            )
        else:
            rec = "REJECT"
            explanation = (
                f"OOS return ({oos_ret:.2f}%) is < 10% of IS return ({is_ret:.2f}%). "
                "Severe overfitting. "
                "The strategy is curve-fitted to historical data and should be rejected."
            )

        return score, rec, explanation
