from fastapi import APIRouter, HTTPException
from models.backtest import BacktestRequest
from pydantic import BaseModel

router = APIRouter()

class AnalysisRequest(BaseModel):
    strategy: dict
    metrics: dict


@router.post("/run")
async def run_backtest(body: BacktestRequest):
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
        )
        return result
    except Exception as e:
        import logging
        logging.error(f"Backtest error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/result/{backtest_id}")
async def get_backtest_result(backtest_id: str):
    """백테스트 결과 조회"""
    from services.supabase_client import get_backtest_by_id

    result = await get_backtest_by_id(backtest_id)
    if not result:
        raise HTTPException(status_code=404, detail="Backtest result not found")
    return result

@router.get("/history/{strategy_id}")
async def get_backtest_history(strategy_id: str):
    """전략의 과거 백테스트 기록 조회"""
    from services.supabase_client import get_backtests_by_strategy_id

    result = await get_backtests_by_strategy_id(strategy_id)
    return result

@router.delete("/history/{backtest_id}")
async def delete_backtest_record(backtest_id: str):
    """특정 백테스트 기록 삭제"""
    from services.supabase_client import delete_backtest_by_id

    success = await delete_backtest_by_id(backtest_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete backtest history.")
    return {"status": "merged"}

@router.post("/analyze")
async def analyze_backtest_result(body: AnalysisRequest):
    """백테스트 결과(전략 + 메트릭스)를 AI로 요약 분석"""
    from services.gemini import generate_backtest_summary

    try:
        summary = await generate_backtest_summary(body.strategy, body.metrics)
        return {"summary": summary}
    except Exception as e:
        import logging
        logging.error(f"Backtest Analysis error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
