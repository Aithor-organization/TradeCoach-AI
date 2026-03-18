"""
Binance Futures Klines data loader.

Fetches USDT-M Futures OHLCV data via REST API with CSV caching.
"""

import csv
import os
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

import httpx

logger = logging.getLogger(__name__)

BINANCE_FUTURES_URL = "https://fapi.binance.com"
CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "futures_cache")


@dataclass
class OhlcvBar:
    """Single OHLCV candlestick bar."""
    timestamp: int  # ms
    open: float
    high: float
    low: float
    close: float
    volume: float

    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp / 1000, tz=timezone.utc)


async def load_futures_klines(
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    limit: int = 1000,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
) -> List[OhlcvBar]:
    """
    Fetch Binance Futures Klines.

    Args:
        symbol: Trading pair (e.g., "BTCUSDT")
        interval: Candle interval ("1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d")
        limit: Max candles per request (max 1500)
        start_time: Start timestamp in ms
        end_time: End timestamp in ms

    Returns:
        List of OhlcvBar sorted by timestamp ascending.
    """
    params = {"symbol": symbol, "interval": interval, "limit": min(limit, 1500)}
    if start_time:
        params["startTime"] = start_time
    if end_time:
        params["endTime"] = end_time

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{BINANCE_FUTURES_URL}/fapi/v1/klines", params=params)
        resp.raise_for_status()
        data = resp.json()

    return [_parse_kline(k) for k in data]


async def download_futures_data(
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    days: int = 365,
) -> List[OhlcvBar]:
    """
    Download multiple pages of futures data (up to `days` worth).

    Uses pagination to fetch more than 1500 candles.
    Results are cached to CSV for subsequent loads.
    """
    cache_file = _cache_path(symbol, interval, days)
    if os.path.exists(cache_file):
        bars = _load_from_csv(cache_file)
        if bars:
            logger.info(f"Loaded {len(bars)} bars from cache: {cache_file}")
            return bars

    all_bars: List[OhlcvBar] = []
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    interval_ms = _interval_to_ms(interval)
    start_ms = now_ms - (days * 24 * 3600 * 1000)

    current = start_ms
    while current < now_ms:
        bars = await load_futures_klines(
            symbol=symbol, interval=interval, limit=1500, start_time=current,
        )
        if not bars:
            break
        all_bars.extend(bars)
        current = bars[-1].timestamp + interval_ms
        if len(bars) < 1500:
            break

    # 중복 제거 + 정렬
    seen = set()
    unique = []
    for b in all_bars:
        if b.timestamp not in seen:
            seen.add(b.timestamp)
            unique.append(b)
    unique.sort(key=lambda b: b.timestamp)

    # 캐시 저장
    _save_to_csv(unique, cache_file)
    logger.info(f"Downloaded {len(unique)} bars for {symbol} {interval} ({days}d)")
    return unique


def _parse_kline(k: list) -> OhlcvBar:
    return OhlcvBar(
        timestamp=int(k[0]),
        open=float(k[1]),
        high=float(k[2]),
        low=float(k[3]),
        close=float(k[4]),
        volume=float(k[5]),
    )


def _interval_to_ms(interval: str) -> int:
    units = {"m": 60_000, "h": 3_600_000, "d": 86_400_000}
    num = int(interval[:-1])
    unit = interval[-1]
    return num * units.get(unit, 3_600_000)


def _cache_path(symbol: str, interval: str, days: int) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{symbol}_{interval}_{days}d.csv")


def _save_to_csv(bars: List[OhlcvBar], path: str):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        for b in bars:
            w.writerow([b.timestamp, b.open, b.high, b.low, b.close, b.volume])


def _load_from_csv(path: str) -> List[OhlcvBar]:
    bars = []
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            bars.append(OhlcvBar(
                timestamp=int(row["timestamp"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
            ))
    return bars
