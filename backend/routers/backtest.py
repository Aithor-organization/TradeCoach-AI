import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from models.backtest import BacktestRequest
from dependencies import get_current_user_id
from routers.auth import limiter
from pydantic import BaseModel
from typing import Optional
from datetime import date

router = APIRouter()
logger = logging.getLogger(__name__)


class AnalysisRequest(BaseModel):
    strategy: dict
    metrics: dict


class ISOOSRequest(BaseModel):
    """Request body for IS/OOS overfitting analysis."""
    token_pair: str = "BTC/USDT"
    timeframe: str = "1h"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    parsed_strategy: dict
    days: int = 365


@router.post("/run")
@limiter.limit("10/minute")
async def run_backtest(request: Request, body: BacktestRequest, user_id: str | None = Depends(get_current_user_id)):
    """백테스트 실행 (spot 또는 futures 자동 라우팅)"""
    try:
        # 선물 모드 판정: 기본은 futures, spot은 명시적 요청 시만
        is_futures = True
        if body.market_type == "spot":
            is_futures = False
        if body.parsed_strategy and body.parsed_strategy.get("market_type") == "spot":
            is_futures = False

        logger.info(f"백테스트 엔진: {'FUTURES' if is_futures else 'SPOT'} | market_type={body.market_type} | strategy_market_type={body.parsed_strategy.get('market_type') if body.parsed_strategy else 'N/A'}")
        if is_futures:
            from services.futures import execute_futures_backtest
            result = await execute_futures_backtest(
                parsed_strategy=body.parsed_strategy or {},
                symbol=body.token_pair.replace("/", ""),
                interval=body.timeframe,
                start_date=body.start_date,
                end_date=body.end_date,
                language=body.language,
            )
            # DB 저장
            from services.supabase_client import save_backtest_result
            save_data = {
                "token_pair": body.token_pair,
                "timeframe": body.timeframe,
                "metrics": result["metrics"],
                "equity_curve": result["equity_curve"],
                "trade_log": result["trade_log"],
                "ai_summary": result.get("ai_summary"),
                "parsed_strategy": body.parsed_strategy,
                "start_date": body.start_date.isoformat() if body.start_date else None,
                "end_date": body.end_date.isoformat() if body.end_date else None,
            }
            if body.strategy_id and body.strategy_id != "local":
                save_data["strategy_id"] = body.strategy_id
            saved = await save_backtest_result(save_data)
            result["id"] = saved["id"]
            return result
        else:
            from services.backtest_engine import execute_backtest
            result = await execute_backtest(
                strategy_id=body.strategy_id,
                token_pair=body.token_pair,
                timeframe=body.timeframe,
                start_date=body.start_date,
                end_date=body.end_date,
                parsed_strategy=body.parsed_strategy,
                language=body.language,
            )
            return result
    except Exception as e:
        logger.error(f"백테스트 실행 실패 (strategy_id={body.strategy_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="백테스트 실행 중 오류가 발생했습니다.")


@router.get("/result/{backtest_id}")
async def get_backtest_result(backtest_id: str):
    """백테스트 결과 조회"""
    from services.supabase_client import get_backtest_by_id

    try:
        result = await get_backtest_by_id(backtest_id)
        if not result:
            raise HTTPException(status_code=404, detail="Backtest result not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"백테스트 결과 조회 실패 (backtest_id={backtest_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="백테스트 결과를 불러올 수 없습니다.")

@router.get("/history/{strategy_id}")
async def get_backtest_history(strategy_id: str):
    """전략의 과거 백테스트 기록 조회"""
    from services.supabase_client import get_backtests_by_strategy_id

    try:
        result = await get_backtests_by_strategy_id(strategy_id)
        return result
    except Exception as e:
        logger.error(f"백테스트 히스토리 조회 실패 (strategy_id={strategy_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="백테스트 히스토리를 불러올 수 없습니다.")

@router.delete("/history/{backtest_id}")
async def delete_backtest_record(backtest_id: str, user_id: str | None = Depends(get_current_user_id)):
    """특정 백테스트 기록 삭제"""
    from services.supabase_client import delete_backtest_by_id

    try:
        success = await delete_backtest_by_id(backtest_id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to delete backtest history.")
        return {"status": "merged"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"백테스트 삭제 실패 (backtest_id={backtest_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="백테스트 삭제 중 오류가 발생했습니다.")

class LinkRequest(BaseModel):
    backtest_ids: list[str]
    strategy_id: str

@router.post("/link")
async def link_backtests_to_strategy(body: LinkRequest):
    """백테스트 결과를 전략에 연결 (메인 챗에서 저장 후)"""
    from services.supabase_client import link_backtest_to_strategy

    try:
        for bt_id in body.backtest_ids:
            await link_backtest_to_strategy(bt_id, body.strategy_id)
        return {"status": "linked", "count": len(body.backtest_ids)}
    except Exception as e:
        logger.error(f"백테스트 연결 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="백테스트 연결 중 오류가 발생했습니다.")

@router.post("/analyze")
async def analyze_backtest_result(body: AnalysisRequest):
    """백테스트 결과(전략 + 메트릭스)를 AI로 요약 분석"""
    from services.gemini import generate_backtest_summary

    try:
        summary = await generate_backtest_summary(body.strategy, body.metrics)
        return {"summary": summary}
    except Exception as e:
        logger.error(f"백테스트 AI 분석 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="백테스트 AI 분석 중 오류가 발생했습니다.")


@router.post("/isoos")
@limiter.limit("5/minute")
async def run_isoos_analysis(
    request: Request,
    body: ISOOSRequest,
    user_id: str | None = Depends(get_current_user_id),
):
    """In-Sample / Out-of-Sample 과적합 분석.

    데이터를 2/3 (IS) + 1/3 (OOS) 로 분할하여 전략의 과적합 정도를 측정합니다.

    Returns:
        ISOOSResult with overfitting_score (0~1) and recommendation
        (SAFE / CAUTIOUS / RISKY / REJECT).
    """
    try:
        import json as _json
        from datetime import datetime, timezone
        from services.futures.types import FuturesConfig
        from services.futures.data_loader import download_futures_data, load_futures_klines
        from services.futures.isoos_runner import ISOOSRunner

        parsed_strategy = body.parsed_strategy
        if isinstance(parsed_strategy, str):
            parsed_strategy = _json.loads(parsed_strategy)

        # Normalise symbol
        pair = parsed_strategy.get("target_pair", body.token_pair)
        clean_symbol = pair.replace("/", "").upper()
        if not clean_symbol.endswith("USDT"):
            clean_symbol = clean_symbol.replace("USDC", "USDT")

        config = FuturesConfig.from_strategy_json(parsed_strategy)
        config.symbol = clean_symbol

        # Load OHLCV data
        if body.days > 0:
            bars = await download_futures_data(
                symbol=clean_symbol,
                interval=body.timeframe,
                days=body.days,
            )
        else:
            bars = await load_futures_klines(
                symbol=clean_symbol,
                interval=body.timeframe,
                limit=1000,
            )

        # Apply date filter
        if body.start_date:
            start_ms = int(
                datetime.combine(body.start_date, datetime.min.time())
                .replace(tzinfo=timezone.utc)
                .timestamp() * 1000
            )
            bars = [b for b in bars if b.timestamp >= start_ms]
        if body.end_date:
            end_ms = int(
                datetime.combine(body.end_date, datetime.max.time())
                .replace(tzinfo=timezone.utc)
                .timestamp() * 1000
            )
            bars = [b for b in bars if b.timestamp <= end_ms]

        if len(bars) < 60:
            raise HTTPException(
                status_code=400,
                detail=f"IS/OOS 분석에는 최소 60개 캔들이 필요합니다 (현재 {len(bars)}개).",
            )

        runner = ISOOSRunner(config)
        result = runner.run(bars, parsed_strategy)
        return result.to_dict()

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"IS/OOS 분석 입력 오류: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"IS/OOS 분석 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="IS/OOS 분석 중 오류가 발생했습니다.")
