import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from models.backtest import BacktestRequest
from dependencies import require_auth, get_current_user_id
from routers.auth import limiter
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)

class AnalysisRequest(BaseModel):
    strategy: dict
    metrics: dict


@router.post("/run")
@limiter.limit("5/minute;30/day")
async def run_backtest(request: Request, body: BacktestRequest, user_id: str | None = Depends(get_current_user_id)):
    """백테스트 실행"""
    from services.backtest_engine import execute_backtest

    try:
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
