"""PositionManager: open/close positions, update prices, FEE_RATE=0.0004"""
import asyncio, uuid, logging
from datetime import datetime, timezone
from typing import Dict, Optional
logger = logging.getLogger(__name__)
FEE_RATE = 0.0004

class Position:
    def __init__(self, pid, uid, sym, side, entry, qty, leverage):
        self.id=pid; self.uid=uid; self.symbol=sym; self.side=side
        self.entry_price=entry; self.quantity=qty; self.leverage=leverage
        self.notional=entry*qty; self.margin=self.notional/leverage+self.notional*FEE_RATE
        self.open_fee=self.notional*FEE_RATE; self.status="open"
        self.current_price=entry; self.unrealized_pnl=0.0
        self.opened_at=datetime.now(timezone.utc)
    def update_price(self, price):
        self.current_price=price
        self.unrealized_pnl=(price-self.entry_price)*self.quantity if self.side=="LONG" else (self.entry_price-price)*self.quantity

class PositionManager:
    def __init__(self):
        self._pos: Dict[str,Position]={}; self._lock=asyncio.Lock()
    async def open_position(self, uid, sym, side, price, qty, leverage) -> Position:
        pid=str(uuid.uuid4())
        p=Position(pid,uid,sym.upper(),side,price,qty,leverage)
        async with self._lock: self._pos[pid]=p
        logger.info("[%s] open %s %s %.4f@%.4f lev=%dx margin=%.4f",uid,side,sym,qty,price,leverage,p.margin)
        return p
    async def close_position(self, pid, close_price) -> Optional[Position]:
        async with self._lock:
            p=self._pos.get(pid)
            if not p or p.status!="open": return None
            gross=(close_price-p.entry_price)*p.quantity if p.side=="LONG" else (p.entry_price-close_price)*p.quantity
            fee=close_price*p.quantity*FEE_RATE
            p.status="closed"; p.current_price=close_price; p.unrealized_pnl=0.0
            p._net_pnl=gross-fee; p._close_fee=fee
            logger.info("[%s] close %s pnl=%.4f fee=%.4f",p.uid,p.side,p._net_pnl,fee)
            return p
    async def update_prices(self, sym, price):
        async with self._lock:
            for p in self._pos.values():
                if p.symbol==sym.upper() and p.status=="open": p.update_price(price)
