"""Score = return*0.4 + winrate*0.3 - drawdown*0.3, verified*2"""
import logging
logger = logging.getLogger(__name__)

class RankingService:
    def __init__(self, db=None): self._db=db
    @staticmethod
    def calculate_score(avg_return, win_rate, max_drawdown, is_verified=False):
        raw = avg_return*0.4 + (win_rate*100)*0.3 - abs(max_drawdown)*0.3
        return raw * 2 if is_verified else raw
    async def get_rankings(self, category="overall", limit=20, offset=0, verified_only=False):
        if not self._db: return []
        q = self._db.table("strategy_rankings").select("*").eq("category", category)
        if verified_only: q = q.eq("is_verified", True)
        return (q.order("score", desc=True).range(offset, offset+limit-1).execute()).data or []
    async def refresh_rankings(self, category="overall"):
        logger.info("Refreshing rankings for category: %s", category)
