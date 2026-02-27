import logging
import time
import httpx

logger = logging.getLogger(__name__)

COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price"

# 심볼 → CoinGecko ID 매핑
COINGECKO_IDS: dict[str, str] = {
    "SOL": "solana",
    "JUP": "jupiter-exchange-solana",
    "RAY": "raydium",
    "BONK": "bonk",
    "WIF": "dogwifcoin",
}

# 간단 캐시: {symbol: (price, timestamp)}
_price_cache: dict[str, tuple[float, float]] = {}
CACHE_TTL = 15  # 초


async def get_token_price(symbol: str) -> float | None:
    """CoinGecko API로 토큰의 USD 가격 조회"""
    symbol = symbol.upper()
    now = time.time()

    if symbol in _price_cache:
        price, cached_at = _price_cache[symbol]
        if now - cached_at < CACHE_TTL:
            return price

    cg_id = COINGECKO_IDS.get(symbol)
    if not cg_id:
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(COINGECKO_API, params={
                "ids": cg_id,
                "vs_currencies": "usd",
            })
            resp.raise_for_status()
            data = resp.json()

        price = data.get(cg_id, {}).get("usd")
        if price is not None:
            _price_cache[symbol] = (float(price), now)
        return float(price) if price is not None else None
    except Exception as e:
        logger.warning(f"가격 조회 실패 ({symbol}): {e}")
        if symbol in _price_cache:
            return _price_cache[symbol][0]
        return None


async def get_all_prices() -> dict[str, float | None]:
    """모든 주요 토큰 가격 일괄 조회 (단일 API 호출)"""
    now = time.time()

    # 캐시가 전부 유효하면 캐시 반환
    all_cached = all(
        sym in _price_cache and now - _price_cache[sym][1] < CACHE_TTL
        for sym in COINGECKO_IDS
    )
    if all_cached:
        return {sym: _price_cache[sym][0] for sym in COINGECKO_IDS}

    ids_str = ",".join(COINGECKO_IDS.values())
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(COINGECKO_API, params={
                "ids": ids_str,
                "vs_currencies": "usd",
            })
            resp.raise_for_status()
            data = resp.json()

        prices: dict[str, float | None] = {}
        for symbol, cg_id in COINGECKO_IDS.items():
            price = data.get(cg_id, {}).get("usd")
            if price is not None:
                _price_cache[symbol] = (float(price), now)
                prices[symbol] = float(price)
            else:
                prices[symbol] = _price_cache.get(symbol, (None,))[0]
        return prices
    except Exception as e:
        logger.warning(f"일괄 가격 조회 실패: {e}")
        return {
            sym: _price_cache[sym][0] if sym in _price_cache else None
            for sym in COINGECKO_IDS
        }
