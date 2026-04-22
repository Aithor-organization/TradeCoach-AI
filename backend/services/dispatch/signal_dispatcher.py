"""Multi-channel parallel dispatch with 3 retries (1s→2s→4s exponential backoff)"""
import asyncio, logging
from typing import Any, List, Protocol
logger = logging.getLogger(__name__)

class Channel(Protocol):
    name: str
    async def send(self, payload: dict) -> None: ...

class SignalDispatcher:
    def __init__(self, channels: List[Any]=None):
        self._ch = channels or []
    def add_channel(self, ch): self._ch.append(ch)
    async def dispatch(self, payload: dict) -> List[dict]:
        if not self._ch: return []
        results = await asyncio.gather(*[self._send_retry(ch, payload) for ch in self._ch])
        ok=sum(1 for r in results if r["success"]); logger.info("Dispatch: %d/%d ok",ok,len(results))
        return results
    async def _send_retry(self, ch, payload, max_retries=3):
        for attempt in range(max_retries):
            try:
                await ch.send(payload)
                return {"channel":ch.name,"success":True,"attempts":attempt+1}
            except Exception as e:
                if attempt<max_retries-1: await asyncio.sleep(1*(2**attempt))
                else: logger.error("Channel %s failed: %s",ch.name,e); return {"channel":ch.name,"success":False,"error":str(e),"attempts":max_retries}
