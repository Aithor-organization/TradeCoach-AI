"""
멀티 전략 동시 실행 매니저
여러 전략을 동시에 모의투자/실거래로 실행하고 포트폴리오 합산 PnL을 추적한다.
"""
import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class StrategySession:
    """개별 전략 세션"""
    session_id: str
    strategy_id: str
    strategy_name: str
    symbol: str
    leverage: int
    status: str = "active"  # active | stopped | error
    balance: float = 0.0
    pnl: float = 0.0
    trades: int = 0
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MultiStrategyManager:
    """
    여러 전략을 동시에 실행하는 포트폴리오 매니저.
    
    각 전략은 독립적인 세션으로 실행되며, 전체 포트폴리오의
    합산 PnL, 총 거래 수, 활성 포지션 수를 추적한다.
    
    사용 예:
        mgr = MultiStrategyManager(user_id="user1")
        sid1 = await mgr.start_strategy("RSI Gold", "BTCUSDT", 10, strategy_config)
        sid2 = await mgr.start_strategy("EMA Cross", "ETHUSDT", 5, strategy_config)
        portfolio = mgr.get_portfolio_summary()
        await mgr.stop_strategy(sid1)
    """

    def __init__(self, user_id: str, max_strategies: int = 5):
        self.user_id = user_id
        self.max_strategies = max_strategies
        self._sessions: Dict[str, StrategySession] = {}
        self._tasks: Dict[str, asyncio.Task] = {}

    async def start_strategy(
        self,
        strategy_name: str,
        symbol: str,
        leverage: int,
        strategy_config: dict,
        initial_balance: float = 1000.0,
    ) -> str:
        """새 전략 세션을 시작한다."""
        active_count = sum(1 for s in self._sessions.values() if s.status == "active")
        if active_count >= self.max_strategies:
            raise ValueError(
                f"최대 {self.max_strategies}개 전략만 동시 실행 가능합니다. "
                f"현재 {active_count}개 활성."
            )

        session_id = str(uuid.uuid4())
        session = StrategySession(
            session_id=session_id,
            strategy_id=strategy_config.get("id", session_id),
            strategy_name=strategy_name,
            symbol=symbol.upper(),
            leverage=leverage,
            balance=initial_balance,
        )
        self._sessions[session_id] = session

        logger.info(
            "[%s] 전략 시작: %s %s %dx (session=%s)",
            self.user_id, strategy_name, symbol, leverage, session_id,
        )
        return session_id

    async def stop_strategy(self, session_id: str) -> Optional[StrategySession]:
        """전략 세션을 종료한다."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        session.status = "stopped"

        # 백그라운드 태스크가 있으면 취소
        task = self._tasks.pop(session_id, None)
        if task and not task.done():
            task.cancel()

        logger.info(
            "[%s] 전략 종료: %s pnl=%.4f trades=%d",
            self.user_id, session.strategy_name, session.pnl, session.trades,
        )
        return session

    async def stop_all(self) -> List[StrategySession]:
        """모든 활성 전략을 종료한다."""
        results = []
        for sid in list(self._sessions.keys()):
            s = await self.stop_strategy(sid)
            if s:
                results.append(s)
        return results

    def update_session(self, session_id: str, pnl: float, trades: int, balance: float):
        """세션의 PnL/거래 수/잔고를 업데이트한다."""
        session = self._sessions.get(session_id)
        if session:
            session.pnl = pnl
            session.trades = trades
            session.balance = balance

    def get_portfolio_summary(self) -> dict:
        """전체 포트폴리오 요약을 반환한다."""
        active = [s for s in self._sessions.values() if s.status == "active"]
        all_sessions = list(self._sessions.values())

        total_pnl = sum(s.pnl for s in all_sessions)
        total_trades = sum(s.trades for s in all_sessions)
        total_balance = sum(s.balance for s in active)

        return {
            "user_id": self.user_id,
            "active_strategies": len(active),
            "total_strategies": len(all_sessions),
            "total_pnl": round(total_pnl, 4),
            "total_trades": total_trades,
            "total_balance": round(total_balance, 4),
            "strategies": [
                {
                    "session_id": s.session_id,
                    "name": s.strategy_name,
                    "symbol": s.symbol,
                    "leverage": s.leverage,
                    "status": s.status,
                    "pnl": round(s.pnl, 4),
                    "trades": s.trades,
                    "balance": round(s.balance, 4),
                }
                for s in all_sessions
            ],
        }

    def get_session(self, session_id: str) -> Optional[StrategySession]:
        """개별 세션 정보를 반환한다."""
        return self._sessions.get(session_id)
