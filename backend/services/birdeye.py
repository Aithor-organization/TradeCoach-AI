import httpx
import pandas as pd
from datetime import datetime, timedelta, timezone, date
from typing import Optional

from config import get_settings

settings = get_settings()

BIRDEYE_BASE_URL = "https://public-api.birdeye.so"

# 주요 토큰 주소 (Solana Mainnet)
TOKEN_ADDRESSES = {
    "SOL": "So11111111111111111111111111111111111111112",
    "RAY": "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
    "JUP": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
    "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "WIF": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
}

# USDC 주소
USDC_ADDRESS = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

TIMEFRAME_MAP = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1H",
    "4h": "4H",
    "1d": "1D",
}


async def fetch_ohlcv(
    token_symbol: str,
    timeframe: str = "1h",
    days: int = 90,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> pd.DataFrame:
    """Birdeye에서 OHLCV 데이터 수집"""
    token_address = TOKEN_ADDRESSES.get(token_symbol.upper().split("/")[0])
    if not token_address:
        raise ValueError(f"Unsupported token: {token_symbol}")

    birdeye_tf = TIMEFRAME_MAP.get(timeframe, "1H")
    now = datetime.now(timezone.utc)
    
    if start_date:
        dt_start = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        time_from = int(dt_start.timestamp())
    else:
        time_from = int((now - timedelta(days=days)).timestamp())
        
    if end_date:
        dt_end = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)
        time_to = int(dt_end.timestamp())
    else:
        time_to = int(now.timestamp())

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{BIRDEYE_BASE_URL}/defi/ohlcv",
            params={
                "address": token_address,
                "type": birdeye_tf,
                "time_from": time_from,
                "time_to": time_to,
            },
            headers={
                "X-API-KEY": settings.birdeye_api_key,
                "x-chain": "solana",
            },
        )
        response.raise_for_status()
        data = response.json()

    items = data.get("data", {}).get("items", [])
    if not items:
        raise ValueError(f"No OHLCV data for {token_symbol}")

    df = pd.DataFrame(items)
    df["datetime"] = pd.to_datetime(df["unixTime"], unit="s")
    df = df.set_index("datetime")
    df = df.rename(columns={
        "o": "Open",
        "h": "High",
        "l": "Low",
        "c": "Close",
        "v": "Volume",
    })
    df = df[["Open", "High", "Low", "Close", "Volume"]].astype(float)
    df = df.sort_index()

    return df
