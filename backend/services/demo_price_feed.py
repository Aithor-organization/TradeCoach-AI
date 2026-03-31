"""
모의투자용 실시간 가격 피드 + 신호 평가.

Binance REST API에서 주기적으로 가격을 가져와 DemoEngine에 주입하고,
전략 조건을 평가하여 진입 신호를 자동 생성한다.
"""


# WebSocket 모드 활성화 시 REST 폴링 대신 Binance aggTrade WebSocket 사용
# 환경변수 PRICE_FEED_MODE=ws 로 설정하면 WebSocket 모드로 전환
import os
PRICE_FEED_MODE = os.getenv("PRICE_FEED_MODE", "rest")  # "rest" | "ws"

import asyncio
import logging
import time
from typing import Optional, Dict, Any

import httpx

logger = logging.getLogger(__name__)

BINANCE_KLINES_URL = "https://fapi.binance.com/fapi/v1/klines"
BINANCE_PRICE_URL = "https://fapi.binance.com/fapi/v2/ticker/price"


async def fetch_current_price(symbol: str) -> Optional[float]:
    """Binance Futures에서 현재 가격 조회."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(BINANCE_PRICE_URL, params={"symbol": symbol})
            if res.status_code == 200:
                return float(res.json()["price"])
    except Exception as e:
        logger.warning(f"가격 조회 실패 ({symbol}): {e}")
    return None


async def fetch_recent_klines(symbol: str, interval: str = "1m", limit: int = 100):
    """Binance Futures에서 최근 OHLCV 데이터 조회."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(BINANCE_KLINES_URL, params={
                "symbol": symbol,
                "interval": interval,
                "limit": limit,
            })
            if res.status_code == 200:
                return res.json()
    except Exception as e:
        logger.warning(f"Klines 조회 실패 ({symbol}): {e}")
    return None


def evaluate_simple_signal(strategy: Dict[str, Any], klines: list) -> Optional[str]:
    """
    간이 신호 평가: Binance klines 데이터에서 전략 조건을 평가.
    futures signal_evaluator를 사용하되, OhlcvBar로 변환.
    """
    if not klines or len(klines) < 20:
        return None

    try:
        from services.futures.data_loader import OhlcvBar
        from services.futures.signal_evaluator import evaluate_entry_signal

        bars = []
        for k in klines:
            bars.append(OhlcvBar(
                timestamp=int(k[0]),
                open=float(k[1]),
                high=float(k[2]),
                low=float(k[3]),
                close=float(k[4]),
                volume=float(k[5]),
            ))
        return evaluate_entry_signal(strategy, bars)
    except Exception as e:
        logger.debug(f"신호 평가 실패: {e}")
        return None


def _calc_required_bars(strategy_config: Dict[str, Any]) -> int:
    """전략의 지표에서 필요한 최소 봉 수를 계산."""
    max_period = 100  # 기본값
    entry = strategy_config.get("entry", {})
    for cond in entry.get("conditions", []):
        indicator = cond.get("indicator", "")
        params = cond.get("params", {})
        # ema_N, sma_N 패턴 (예: ema_200)
        for prefix in ("ema_", "sma_"):
            if indicator.startswith(prefix) and indicator[len(prefix):].isdigit():
                max_period = max(max_period, int(indicator[len(prefix):]))
        # params에서 period 추출
        for key in ("period", "long_period", "slow_period", "rsi_period", "stoch_period"):
            if key in params:
                max_period = max(max_period, int(params[key]))
    # 20% 여유 + 최소 200
    return max(max_period + max(50, int(max_period * 0.2)), 200)


async def run_price_feed(
    session_id: str,
    engine,
    strategy_config: Dict[str, Any],
    sessions_ref: dict,
    interval_sec: float = 3.0,
):
    """
    백그라운드 가격 피드 루프.

    interval_sec마다 Binance에서 가격을 가져와 엔진에 주입하고,
    포지션이 없으면 신호를 평가하여 자동 진입한다.
    """
    symbol = engine.session.symbol
    required_bars = _calc_required_bars(strategy_config)
    # Binance klines API 최대 1500개
    kline_limit = min(required_bars, 1500)
    logger.info(f"가격 피드 시작: {session_id} ({symbol}), 필요 봉 수: {kline_limit}")

    # 초기 klines 로드
    klines = await fetch_recent_klines(symbol, "1m", kline_limit)

    while session_id in sessions_ref:
        entry = sessions_ref.get(session_id)
        if not entry or entry["engine"].session.status != "active":
            break

        try:
            price = await fetch_current_price(symbol)
            if price is None:
                await asyncio.sleep(interval_sec)
                continue

            now_ms = int(time.time() * 1000)

            # 가격 업데이트 → SL/TP/트레일링 스탑 자동 처리
            trade = engine.on_price_update(price, now_ms)

            # 포지션이 없으면 신호 평가
            if engine.session.position is None and klines:
                # klines 마지막 봉의 close를 현재 가격으로 업데이트
                if klines:
                    klines[-1][4] = str(price)

                signal = evaluate_simple_signal(strategy_config, klines)
                if signal:
                    # signal_evaluator 반환값 ("long"/"short") → 4종 진입 신호로 매핑
                    signal_type = "BUY_LONG" if signal == "long" else "SELL_SHORT"
                    engine.signal(signal_type)
                    engine.on_price_update(price, now_ms)
                    logger.info(f"[{session_id}] 신호 감지: {signal_type} @ {price}")

            # 주기적으로 klines 갱신 (30초마다)
            if now_ms % 30000 < int(interval_sec * 1000):
                new_klines = await fetch_recent_klines(symbol, "1m", kline_limit)
                if new_klines:
                    klines = new_klines

        except Exception as e:
            logger.error(f"가격 피드 에러 ({session_id}): {e}")

        await asyncio.sleep(interval_sec)

    logger.info(f"가격 피드 종료: {session_id}")
