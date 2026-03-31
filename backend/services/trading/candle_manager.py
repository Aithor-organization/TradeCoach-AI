"""CandleManager: aggTrade ticks → OHLCV candles for 1m/3m/15m, 300 rolling buffer"""
import asyncio
from collections import deque
from dataclasses import dataclass
from typing import Callable, Optional

@dataclass
class Candle:
    tf: str; open_time: int; close_time: int
    o: float; h: float; l: float; c: float; v: float; trades: int = 0; closed: bool = False
    def to_dict(self): return {"tf":self.tf,"ot":self.open_time,"ct":self.close_time,"o":self.o,"h":self.h,"l":self.l,"c":self.c,"v":self.v,"n":self.trades,"closed":self.closed}

TF_MS = {"1m":60000,"3m":180000,"15m":900000}

class _Bucket:
    def __init__(self, tf):
        self.tf=tf; self.ms=TF_MS[tf]; self.candles=deque(maxlen=300); self._cur=None
    def tick(self, price, qty, ts_ms):
        ot=(ts_ms//self.ms)*self.ms; ct=ot+self.ms-1; done=None
        if self._cur is None:
            self._cur=Candle(self.tf,ot,ct,price,price,price,price,qty,1)
        elif ts_ms>self._cur.close_time:
            self._cur.closed=True; done=self._cur; self.candles.append(done)
            self._cur=Candle(self.tf,ot,ct,price,price,price,price,qty,1)
        else:
            c=self._cur; c.h=max(c.h,price); c.l=min(c.l,price); c.c=price; c.v+=qty; c.trades+=1
        return done

class CandleManager:
    def __init__(self, symbol):
        self.symbol=symbol.upper()
        self._b={tf:_Bucket(tf) for tf in TF_MS}
        self.on_candle_complete: Optional[Callable]=None
    async def process_tick(self, price, qty, ts_ms):
        for b in self._b.values():
            done=b.tick(price,qty,ts_ms)
            if done and self.on_candle_complete:
                if asyncio.iscoroutinefunction(self.on_candle_complete): await self.on_candle_complete(done)
                else: self.on_candle_complete(done)
    def get_candles(self, tf): return list(self._b[tf].candles) if tf in self._b else []
