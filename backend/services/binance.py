import httpx
import pandas as pd
from datetime import datetime, timedelta, timezone, date
from typing import Optional

BINANCE_BASE_URL = "https://api.binance.com/api/v3"

# 토큰 심볼 → Binance 거래 페어 매핑
PAIR_MAP = {
    "SOL/USDC": "SOLUSDT",
    "SOL/USDT": "SOLUSDT",
    "BTC/USDT": "BTCUSDT",
    "ETH/USDT": "ETHUSDT",
    "RAY/USDC": "RAYUSDT",
    "JUP/USDC": "JUPUSDT",
    "BONK/USDC": "BONKUSDT",
    "WIF/USDC": "WIFUSDT",
    "SOL": "SOLUSDT",
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "RAY": "RAYUSDT",
    "JUP": "JUPUSDT",
    "BONK": "BONKUSDT",
    "WIF": "WIFUSDT",
}

TIMEFRAME_MAP = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
}

# Binance klines 최대 1000개/요청, 페이지네이션으로 확장
MAX_KLINES_PER_REQUEST = 1000


def _resolve_symbol(token_pair: str) -> str:
    """토큰 페어 문자열을 Binance 심볼로 변환"""
    symbol = PAIR_MAP.get(token_pair.upper())
    if symbol:
        return symbol
    # "SOLUSDC" → "SOLUSDT" 패턴 시도
    cleaned = token_pair.upper().replace("/", "").replace("USDC", "USDT")
    return cleaned


async def fetch_ohlcv(
    token_symbol: str,
    timeframe: str = "1h",
    days: int = 90,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> pd.DataFrame:
    """Binance에서 OHLCV 데이터 수집 (API 키 불필요)"""
    symbol = _resolve_symbol(token_symbol)
    interval = TIMEFRAME_MAP.get(timeframe, "1h")

    now = datetime.now(timezone.utc)

    if start_date:
        dt_start = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        start_ms = int(dt_start.timestamp() * 1000)
    else:
        start_ms = int((now - timedelta(days=days)).timestamp() * 1000)

    if end_date:
        dt_end = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)
        end_ms = int(dt_end.timestamp() * 1000)
    else:
        end_ms = int(now.timestamp() * 1000)

    # 페이지네이션으로 전체 데이터 수집
    all_klines = []
    current_start = start_ms

    async with httpx.AsyncClient(timeout=30.0) as client:
        while current_start < end_ms:
            response = await client.get(
                f"{BINANCE_BASE_URL}/klines",
                params={
                    "symbol": symbol,
                    "interval": interval,
                    "startTime": current_start,
                    "endTime": end_ms,
                    "limit": MAX_KLINES_PER_REQUEST,
                },
            )
            response.raise_for_status()
            klines = response.json()

            if not klines:
                break

            all_klines.extend(klines)

            # 다음 페이지: 마지막 캔들의 close_time + 1ms
            last_close_time = klines[-1][6]
            current_start = last_close_time + 1

            # 마지막 페이지면 종료
            if len(klines) < MAX_KLINES_PER_REQUEST:
                break

    if not all_klines:
        raise ValueError(f"No OHLCV data for {token_symbol} ({symbol})")

    # Binance kline 포맷: [open_time, open, high, low, close, volume, close_time, ...]
    df = pd.DataFrame(all_klines, columns=[
        "open_time", "Open", "High", "Low", "Close", "Volume",
        "close_time", "quote_volume", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore",
    ])

    df["datetime"] = pd.to_datetime(df["open_time"], unit="ms")
    df = df.set_index("datetime")
    df = df[["Open", "High", "Low", "Close", "Volume"]].astype(float)
    df = df.sort_index()

    return df
