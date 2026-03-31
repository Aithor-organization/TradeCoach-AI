"""Binance Futures Market Order API: timeout=5s, recvWindow=5000"""
import asyncio, logging
logger = logging.getLogger(__name__)
try:
    from binance import AsyncClient
    HAS_BINANCE = True
except ImportError:
    HAS_BINANCE = False

class BinanceOrderAPI:
    def __init__(self, api_key, secret_key, testnet=False):
        self._key=api_key; self._secret=secret_key; self._testnet=testnet; self._client=None
    async def _get(self):
        if not self._client:
            self._client = await AsyncClient.create(self._key, self._secret, testnet=self._testnet)
        return self._client
    async def close(self):
        if self._client: await self._client.close_connection(); self._client=None
    async def place_market_order(self, symbol, side, qty):
        c=await self._get()
        return await asyncio.wait_for(c.futures_create_order(symbol=symbol,side=side,type="MARKET",quantity=qty,recvWindow=5000),5)
    async def set_leverage(self, symbol, leverage):
        c=await self._get()
        return await asyncio.wait_for(c.futures_change_leverage(symbol=symbol,leverage=leverage,recvWindow=5000),5)
    async def get_account_balance(self):
        c=await self._get()
        resp=await asyncio.wait_for(c.futures_account_balance(recvWindow=5000),5)
        for a in resp:
            if a.get("asset")=="USDT": return float(a.get("availableBalance",0))
        return 0.0
    async def get_positions(self, symbol=None):
        c=await self._get(); params={"recvWindow":5000}
        if symbol: params["symbol"]=symbol
        resp=await asyncio.wait_for(c.futures_position_information(**params),5)
        return [p for p in resp if float(p.get("positionAmt",0))!=0]
    async def get_symbol_info(self, symbol):
        c=await self._get(); info=await asyncio.wait_for(c.futures_exchange_info(),5)
        for s in info.get("symbols",[]): 
            if s["symbol"]==symbol: return s
        raise ValueError(f"Symbol not found: {symbol}")
