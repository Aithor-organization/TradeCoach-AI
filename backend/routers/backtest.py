from fastapi import APIRouter, HTTPException
from models.backtest import BacktestRequest

router = APIRouter()


@router.post("/run")
async def run_backtest(body: BacktestRequest):
    """백테스트 실행"""
    from services.backtest_engine import execute_backtest

    result = await execute_backtest(
        strategy_id=body.strategy_id,
        token_pair=body.token_pair,
        timeframe=body.timeframe,
        start_date=body.start_date,
        end_date=body.end_date,
        parsed_strategy=body.parsed_strategy,
    )
    return result


@router.get("/result/{backtest_id}")
async def get_backtest_result(backtest_id: str):
    """백테스트 결과 조회"""
    from services.supabase_client import get_backtest_by_id

    result = await get_backtest_by_id(backtest_id)
    if not result:
        raise HTTPException(status_code=404, detail="Backtest result not found")
    return result
