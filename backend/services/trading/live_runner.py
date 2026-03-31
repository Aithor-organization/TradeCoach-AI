"""LiveRunner: same pipeline as PaperRunner but real Binance orders + User Stream + SignalDispatcher"""
import logging
from .binance_order_api import BinanceOrderAPI
logger = logging.getLogger(__name__)

class LiveRunner:
    def __init__(self, api_key, secret_key, dispatcher=None, testnet=False):
        self._api=BinanceOrderAPI(api_key,secret_key,testnet)
        self._dispatcher=dispatcher; self._running=False
    async def start(self): self._running=True; logger.info("LiveRunner started")
    async def stop(self): self._running=False; await self._api.close(); logger.info("LiveRunner stopped")
    async def execute_signal(self, symbol, side, qty, leverage):
        await self._api.set_leverage(symbol, leverage)
        result = await self._api.place_market_order(symbol, side, qty)
        logger.info("Order filled: %s %s qty=%s", side, symbol, qty)
        if self._dispatcher:
            try: await self._dispatcher.dispatch({"event":"trade_filled","symbol":symbol,"side":side,"qty":qty,"leverage":leverage})
            except Exception as e: logger.warning("Dispatch failed (ignored): %s",e)
        return result
