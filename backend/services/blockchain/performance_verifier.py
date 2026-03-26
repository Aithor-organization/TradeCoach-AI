"""Independent strategy performance verification (StrategyVault pattern)"""
import logging
from dataclasses import dataclass
from typing import Optional, List
logger = logging.getLogger(__name__)

VERIFY_CRITERIA = {"min_signals":100, "min_days":90, "min_signals_per_week":2, "min_verifications":3}

@dataclass
class PerformanceMetrics:
    total_signals: int=0; win_rate: float=0; avg_return: float=0
    max_drawdown: float=0; sharpe_ratio: float=0; trading_days: int=0
    meets_all_criteria: bool=False

@dataclass
class VerificationResult:
    strategy_id: str; verifier_id: str; is_valid: bool
    metrics: Optional[PerformanceMetrics]=None; reason: str=""

class PerformanceVerifier:
    def _calculate_metrics(self, strategy_id, signals) -> PerformanceMetrics:
        m = PerformanceMetrics()
        if not signals: return m
        m.total_signals = len(signals)
        wins = [s for s in signals if s.get("pnl_pct", 0) > 0]
        m.win_rate = len(wins)/len(signals) if signals else 0
        pnls = [s.get("pnl_pct", 0) for s in signals]
        m.avg_return = sum(pnls)/len(pnls) if pnls else 0
        m.max_drawdown = self._calculate_max_drawdown(pnls)
        if len(pnls) >= 30:
            import statistics; mean=statistics.mean(pnls); std=statistics.stdev(pnls)
            m.sharpe_ratio = (mean/std)*252**0.5 if std > 0 else 0
        dates = set(s.get("date") for s in signals if s.get("date"))
        m.trading_days = len(dates)
        m.meets_all_criteria = (m.total_signals>=VERIFY_CRITERIA["min_signals"] and m.trading_days>=VERIFY_CRITERIA["min_days"])
        return m
    def _calculate_max_drawdown(self, pnls):
        if not pnls: return 0
        peak=0; max_dd=0; cumulative=0
        for p in pnls:
            cumulative+=p; peak=max(peak,cumulative); dd=peak-cumulative; max_dd=max(max_dd,dd)
        return max_dd
    async def verify_track_record(self, strategy_id, verifier_id, signals=None) -> VerificationResult:
        if signals is None: signals=[]
        metrics = self._calculate_metrics(strategy_id, signals)
        if not metrics.meets_all_criteria:
            return VerificationResult(strategy_id, verifier_id, False, metrics, "기준 미달")
        return VerificationResult(strategy_id, verifier_id, True, metrics, "검증 통과")
