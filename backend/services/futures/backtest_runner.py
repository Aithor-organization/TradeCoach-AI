"""
Futures backtest execution wrapper.

Bridges the API layer with FuturesBacktestEngine.
Handles data loading, engine execution, and result formatting.
"""

import json
import logging
from typing import Optional
from datetime import date, timezone, datetime

from .types import FuturesConfig
from .engine import FuturesBacktestEngine
from .data_loader import download_futures_data, load_futures_klines

logger = logging.getLogger(__name__)


async def execute_futures_backtest(
    parsed_strategy: dict,
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    days: int = 365,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    language: str = "ko",
) -> dict:
    """
    선물 백테스트 실행 + 결과 포맷팅.

    Args:
        parsed_strategy: 파싱된 전략 JSON
        symbol: 거래쌍 (예: BTCUSDT)
        interval: 캔들 간격
        days: 데이터 기간 (일)
        start_date: 시작 날짜 (선택)
        end_date: 종료 날짜 (선택)
        language: 응답 언어

    Returns:
        백테스트 결과 딕셔너리
    """
    if isinstance(parsed_strategy, str):
        parsed_strategy = json.loads(parsed_strategy)

    # 심볼 정규화: SOL/USDC → SOLUSDC, BTC/USDT → BTCUSDT
    pair = parsed_strategy.get("target_pair", symbol)
    clean_symbol = pair.replace("/", "").upper()

    # 선물은 USDT 페어만 지원
    if not clean_symbol.endswith("USDT"):
        clean_symbol = clean_symbol.replace("USDC", "USDT")

    # FuturesConfig 생성
    config = FuturesConfig.from_strategy_json(parsed_strategy)
    config.symbol = clean_symbol

    # 초기 자본금 $1,000 고정, 전체 자본 투입 (BinanceTrader 방식)
    INITIAL_CAPITAL = 1000.0
    config.initial_capital = INITIAL_CAPITAL
    config.investment = INITIAL_CAPITAL  # 포지션당 = 전체 자본 (올인)

    # 데이터 로드
    if days > 0:
        bars = await download_futures_data(
            symbol=clean_symbol, interval=interval, days=days,
        )
    else:
        bars = await load_futures_klines(
            symbol=clean_symbol, interval=interval, limit=1000,
        )

    if len(bars) < 20:
        raise ValueError(f"Insufficient data: {len(bars)} bars for {clean_symbol}")

    # 날짜 필터 적용
    if start_date:
        start_ms = int(datetime.combine(start_date, datetime.min.time())
                        .replace(tzinfo=timezone.utc).timestamp() * 1000)
        bars = [b for b in bars if b.timestamp >= start_ms]
    if end_date:
        end_ms = int(datetime.combine(end_date, datetime.max.time())
                      .replace(tzinfo=timezone.utc).timestamp() * 1000)
        bars = [b for b in bars if b.timestamp <= end_ms]

    if len(bars) < 20:
        raise ValueError(f"Insufficient data after date filter: {len(bars)} bars")

    # 엔진 실행
    engine = FuturesBacktestEngine(config)
    metrics = engine.run(bars, parsed_strategy)

    # 결과 포맷팅
    actual_start = bars[0].datetime.isoformat()
    actual_end = bars[-1].datetime.isoformat()

    # 에쿼티 커브 샘플링 (최대 200포인트, 마지막 값 항상 포함)
    equity = engine.equity_curve
    step = max(1, len(equity) // 200)
    sampled_equity = [
        {"date": int(bars[min(i, len(bars) - 1)].timestamp / 1000), "value": round(v, 2)}
        for i, v in enumerate(equity) if i % step == 0
    ]
    # 마지막 값이 누락되면 추가
    if equity and (not sampled_equity or sampled_equity[-1]["value"] != round(equity[-1], 2)):
        sampled_equity.append({
            "date": int(bars[-1].timestamp / 1000),
            "value": round(equity[-1], 2),
        })
    # total_return을 에쿼티 마지막 값과 일치시킴
    metrics_dict = metrics.to_dict()
    metrics_dict["total_return"] = round(((equity[-1] / config.initial_capital) - 1) * 100, 4) if equity else 0

    # 트레이드 로그 포맷팅
    trade_log = [
        {
            "entry_date": t.entry_time,
            "exit_date": t.exit_time,
            "pnl": round(t.pnl, 2),
            "return_pct": round(t.return_pct, 2),
            "side": t.side,
            "exit_reason": t.exit_reason,
            "leverage": t.leverage,
        }
        for t in engine.trades
    ]

    # AI 분석 리포트
    ai_summary = None
    try:
        from services.gemini import generate_backtest_summary
        ai_summary = await generate_backtest_summary(
            parsed_strategy, metrics_dict, language=language,
        )
    except Exception as e:
        logger.warning(f"AI 분석 리포트 생성 실패: {e}")

    return {
        "metrics": metrics_dict,
        "equity_curve": sampled_equity,
        "trade_log": trade_log,
        "ai_summary": ai_summary,
        "actual_period": {
            "start": actual_start,
            "end": actual_end,
            "candles": len(bars),
        },
        "market_type": "futures",
        "config": {
            "leverage": config.leverage,
            "direction": config.direction,
            "commission_rate": config.commission_rate,
            "slippage_ticks": config.slippage_ticks,
        },
    }
