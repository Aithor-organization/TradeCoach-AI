"""BalanceManager: margin deduction/release, balance checks, unrealized PnL tracking"""
import asyncio, logging
from typing import Dict
logger = logging.getLogger(__name__)

class InsufficientBalance(Exception): pass

class BalanceManager:
    def __init__(self):
        self._bal: Dict[str,Dict[str,float]] = {}
        self._locks: Dict[str,asyncio.Lock] = {}
    def _lock(self, uid):
        if uid not in self._locks: self._locks[uid]=asyncio.Lock()
        return self._locks[uid]
    async def init_user(self, uid, balance):
        async with self._lock(uid):
            self._bal[uid]={"total":balance,"available":balance,"margin":0.0,"upnl":0.0}
    async def has_sufficient(self, uid, amount) -> bool:
        async with self._lock(uid):
            b=self._bal.get(uid); return b is not None and b["available"]>=amount
    async def deduct_margin(self, uid, amount) -> bool:
        async with self._lock(uid):
            b=self._bal.get(uid)
            if not b or b["available"]<amount: raise InsufficientBalance(f"{uid}: need {amount}, have {b['available'] if b else 0}")
            b["available"]-=amount; b["margin"]+=amount; return True
    async def release_margin(self, uid, margin, pnl=0.0):
        async with self._lock(uid):
            b=self._bal.get(uid)
            if not b: return
            b["available"]+=margin+pnl; b["total"]+=pnl; b["margin"]=max(0,b["margin"]-margin)
    async def update_unrealized_pnl(self, uid, upnl):
        async with self._lock(uid):
            b=self._bal.get(uid)
            if b: b["upnl"]=upnl
    async def get_snapshot(self, uid):
        async with self._lock(uid):
            b=self._bal.get(uid)
            return {**b,"equity":b["total"]+b["upnl"]} if b else None
