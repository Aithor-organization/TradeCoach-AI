"""Binance aggTrade WebSocket with auto-reconnect (exponential backoff, max 60s)"""
import asyncio, json, logging
from typing import Callable
logger = logging.getLogger(__name__)

class BinanceAggTradeWs:
    def __init__(self, symbol: str, on_tick: Callable, use_futures=True):
        self._sym=symbol.lower(); self._on_tick=on_tick; self._futures=use_futures
        self._running=False; self._backoff=1.0
    @property
    def url(self):
        base="wss://fstream.binance.com" if self._futures else "wss://stream.binance.com:9443"
        return f"{base}/ws/{self._sym}@aggTrade"
    async def start(self):
        import websockets
        self._running=True
        while self._running:
            try:
                async with websockets.connect(self.url, ping_interval=20) as ws:
                    self._backoff=1.0; logger.info("WS connected: %s",self.url)
                    async for msg in ws:
                        if not self._running: break
                        try: await self._on_tick(json.loads(msg))
                        except Exception as e: logger.warning("tick error: %s",e)
            except asyncio.CancelledError: break
            except Exception as e:
                if not self._running: break
                logger.warning("WS disconnected: %s, reconnect in %.0fs",e,self._backoff)
                await asyncio.sleep(self._backoff)
                self._backoff=min(self._backoff*2, 60.0)
    async def stop(self): self._running=False
