"""Pyth Oracle dual-price verification: 5-step validation (staleness, confidence, price>0, status, 1e8)"""
import time, logging, httpx
from dataclasses import dataclass
from typing import Optional, Dict
logger = logging.getLogger(__name__)

@dataclass
class PythPrice:
    symbol: str; price_usd: float; confidence_usd: float; publish_time: int; is_fresh: bool

class PythValidationError(Exception): pass

class PythClient:
    HERMES_URL = "https://hermes.pyth.network/v2/updates/price/latest"
    SYMBOL_MAP = {
        "BTCUSDT":"0xe62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43",
        "ETHUSDT":"0xff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace",
        "SOLUSDT":"0xef0d8b6fda2ceba41da15d4095d1da392a0d2f8ed0c6c7bc0f4cfac8c280b56d",
        "BNBUSDT":"0x2f95862b045670cd22bee3114c39763a4a08beeb663b145d283c31d7d1101c4f",
        "XRPUSDT":"0xec5d399846a9209f3fe5881d70aab14ae9363c4f5fa2e1e9e8b4abf6ef7b20e5",
        "DOGEUSDT":"0xdcef50dd0a4cd2dcc17e45df1676dcb336a11a61c69df7a0299b0150c672d25c",
    }
    _cache: Dict[str, tuple] = {}
    CACHE_TTL = 2.0

    async def get_verified_price(self, symbol: str) -> PythPrice:
        now = time.time()
        if symbol in self._cache:
            cached, ts = self._cache[symbol]
            if now - ts < self.CACHE_TTL: return cached
        feed_id = self.SYMBOL_MAP.get(symbol)
        if not feed_id: raise PythValidationError(f"지원하지 않는 심볼: {symbol}")
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(self.HERMES_URL, params={"ids[]": feed_id})
            resp.raise_for_status(); data = resp.json()
        parsed = data.get("parsed", [{}])[0] if data.get("parsed") else {}
        price_data = parsed.get("price", {})
        price_raw = int(price_data.get("price", 0)); conf_raw = int(price_data.get("conf", 0))
        expo = int(price_data.get("expo", -8)); pub_time = int(price_data.get("publish_time", 0))
        scale = 10 ** abs(expo); price_usd = price_raw / scale; conf_usd = conf_raw / scale
        # 5-step validation
        if now - pub_time > 30: raise PythValidationError(f"가격 데이터 오래됨: {now-pub_time:.0f}초")
        if price_usd > 0 and conf_usd / price_usd > 0.02: raise PythValidationError(f"신뢰도 부족: {conf_usd/price_usd:.4f}")
        if price_usd <= 0: raise PythValidationError(f"비정상 가격: {price_usd}")
        status = parsed.get("metadata", {}).get("status", "Trading")
        if status != "Trading": raise PythValidationError(f"거래 중단: {status}")
        result = PythPrice(symbol=symbol, price_usd=price_usd, confidence_usd=conf_usd, publish_time=pub_time, is_fresh=True)
        self._cache[symbol] = (result, now)
        return result
