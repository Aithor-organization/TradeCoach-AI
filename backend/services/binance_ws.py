"""Binance Futures aggTrade WebSocket 스트리밍 + OHLCV 바 집계 서비스."""

from __future__ import annotations

import json
import logging
from typing import Callable, Optional

import websockets
import websockets.exceptions

logger = logging.getLogger(__name__)

_FSTREAM_BASE = "wss://fstream.binance.com/ws"

# 지원 인터벌 → 초 매핑
_INTERVAL_SECONDS: dict[str, int] = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
}


def interval_to_seconds(interval: str) -> int:
    """인터벌 문자열을 초 단위로 변환한다 (예: "3m" → 180).

    Raises:
        ValueError: 지원하지 않는 인터벌 문자열인 경우.
    """
    try:
        return _INTERVAL_SECONDS[interval]
    except KeyError:
        raise ValueError(
            f"지원하지 않는 인터벌: '{interval}'. 지원 목록: {', '.join(_INTERVAL_SECONDS)}"
        )


class BarAggregator:
    """틱 스트림을 단일 타임프레임의 OHLCV 바로 집계한다.

    바 경계(인터벌 배수)를 최초로 넘는 틱이 들어오면 직전 완성 바를 반환한다.
    """

    def __init__(self, interval_seconds: int, label: str) -> None:
        # 바 크기(ms)와 레이블("3m" 등) 저장
        self._interval_ms = interval_seconds * 1000
        self._label = label
        # 현재 진행 중인 바 상태
        self._open: Optional[float] = None
        self._high = float("-inf")
        self._low = float("inf")
        self._close = 0.0
        self._volume = 0.0
        self._open_ts: Optional[int] = None  # 현재 바 시작 타임스탬프(ms)

    def _boundary(self, ts_ms: int) -> int:
        """타임스탬프가 속한 바의 시작 타임스탬프를 반환한다."""
        return (ts_ms // self._interval_ms) * self._interval_ms

    def _flush(self) -> dict:
        """현재 바를 완성 바 dict로 반환하고 상태를 초기화한다."""
        bar = {
            "open": self._open,
            "high": self._high,
            "low": self._low,
            "close": self._close,
            "volume": self._volume,
            "timestamp": self._open_ts,
            "interval": self._label,
        }
        self._open = None
        self._high = float("-inf")
        self._low = float("inf")
        self._close = 0.0
        self._volume = 0.0
        self._open_ts = None
        return bar

    def on_trade(
        self, price: float, quantity: float, timestamp_ms: int
    ) -> Optional[dict]:
        """틱 하나를 처리한다.

        Returns:
            바 경계를 넘어 새 바가 시작될 때 이전 완성 바 dict를 반환한다.
            바가 아직 진행 중이면 None을 반환한다.

        완성 바 형식::

            {"open": float, "high": float, "low": float, "close": float,
             "volume": float, "timestamp": int, "interval": str}
        """
        boundary = self._boundary(timestamp_ms)
        completed: Optional[dict] = None

        if self._open_ts is None:
            # 첫 틱: 새 바 시작
            self._open_ts = boundary
            self._open = price
        elif boundary != self._open_ts:
            # 바 경계 돌파 → 이전 바 완성 후 새 바 시작
            completed = self._flush()
            self._open_ts = boundary
            self._open = price

        # 현재 바 업데이트
        self._high = max(self._high, price)
        self._low = min(self._low, price)
        self._close = price
        self._volume += quantity

        return completed


class BinanceWSClient:
    """Binance Futures aggTrade WebSocket 클라이언트.

    지정된 심볼의 aggTrade 스트림에 연결하고,
    타임프레임별 BarAggregator를 통해 완성 바를 콜백으로 전달한다.

    사용 예::

        async def handle_bar(bar: dict) -> None:
            print(bar)

        client = BinanceWSClient("btcusdt", ["3m", "15m"], handle_bar)
        await client.run()
    """

    def __init__(
        self,
        symbol: str,
        intervals: list[str],
        on_bar: Callable[[dict], None],
    ) -> None:
        """
        Args:
            symbol: Binance 선물 심볼 (예: "btcusdt").
            intervals: 집계할 인터벌 목록 (예: ["3m", "15m"]).
            on_bar: 완성 바 생성 시 호출되는 콜백.
        """
        self._symbol = symbol.lower()
        self._on_bar = on_bar
        # 인터벌별 집계기 생성
        self._aggregators: dict[str, BarAggregator] = {
            iv: BarAggregator(interval_to_seconds(iv), iv) for iv in intervals
        }
        self._running = False
        self._uri = f"{_FSTREAM_BASE}/{self._symbol}@aggTrade"

    def _handle_message(self, raw: str) -> None:
        """aggTrade 메시지를 파싱하여 모든 집계기에 전달한다."""
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("JSON 파싱 실패: %.120s", raw)
            return

        if msg.get("e") != "aggTrade":
            return

        price = float(msg["p"])       # 체결 가격
        quantity = float(msg["q"])    # 체결 수량
        ts_ms = int(msg["T"])         # 체결 타임스탬프(ms)

        for aggregator in self._aggregators.values():
            bar = aggregator.on_trade(price, quantity, ts_ms)
            if bar is not None:
                try:
                    self._on_bar(bar)
                except Exception:
                    logger.exception("on_bar 콜백 처리 중 오류 발생")

    async def run(self) -> None:
        """WebSocket 연결을 유지하며 aggTrade 스트림을 수신한다.

        연결이 끊어지면 자동으로 재연결을 시도한다.
        `stop()` 호출 시 루프를 종료한다.
        """
        self._running = True
        logger.info("Binance WS 연결 시작: %s", self._uri)

        while self._running:
            try:
                async with websockets.connect(
                    self._uri, ping_interval=20, ping_timeout=10
                ) as ws:
                    logger.info("WebSocket 연결 완료: %s", self._symbol)
                    async for raw in ws:
                        if not self._running:
                            break
                        self._handle_message(raw)
            except websockets.exceptions.ConnectionClosed as exc:
                if not self._running:
                    break
                logger.warning("연결 종료 (재연결 예정): %s", exc)
            except OSError as exc:
                if not self._running:
                    break
                logger.error("네트워크 오류 (재연결 예정): %s", exc)

        logger.info("BinanceWSClient 종료: %s", self._symbol)

    def stop(self) -> None:
        """스트리밍 루프를 중단한다."""
        self._running = False
