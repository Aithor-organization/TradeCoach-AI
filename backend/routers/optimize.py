"""
Phase 2: 파라미터 최적화 + Walk-Forward API 엔드포인트.

POST /optimize/grid    — Grid Search 최적화
POST /optimize/walk-forward — Walk-Forward 전진분석
"""

import logging
from fastapi import APIRouter, HTTPException, Request, Depends
from models.optimize import OptimizeRequest, WalkForwardRequest
from dependencies import get_current_user_id
from routers.auth import limiter

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/grid")
@limiter.limit("5/minute")
async def run_grid_optimization(
    request: Request,
    body: OptimizeRequest,
    user_id: str | None = Depends(get_current_user_id),
):
    """Grid Search 파라미터 최적화 실행"""
    from services.futures.data_loader import download_futures_data
    from services.futures.optimizer import run_optimization

    try:
        # 전략 로드
        parsed = body.parsed_strategy
        if not parsed and body.strategy_id != "local":
            from services.supabase_client import get_strategy_by_id
            strategy = await get_strategy_by_id(body.strategy_id)
            if not strategy:
                raise HTTPException(status_code=404, detail="Strategy not found")
            parsed = strategy["parsed_strategy"]

        if not parsed:
            raise HTTPException(status_code=400, detail="No strategy provided")

        # 데이터 로드
        symbol = body.symbol or parsed.get("target_pair", "BTCUSDT").replace("/", "")
        bars = await download_futures_data(
            symbol=symbol, interval=body.interval, days=body.days,
        )

        if len(bars) < 50:
            raise HTTPException(status_code=400, detail="Insufficient data")

        # 최적화 실행 (asyncio.to_thread로 이벤트 루프 블로킹 방지)
        import asyncio
        results = await asyncio.to_thread(
            run_optimization,
            bars=bars,
            strategy=parsed,
            param_ranges=body.param_ranges,
            objective=body.objective,
            max_combinations=body.max_combinations,
            top_n=10,
        )

        return {
            "results": results,
            "total_tested": min(
                body.max_combinations,
                _count_combinations(body.param_ranges),
            ),
            "objective": body.objective,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"최적화 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="최적화 실행 중 오류")


@router.post("/walk-forward")
@limiter.limit("5/minute")
async def run_walk_forward(
    request: Request,
    body: WalkForwardRequest,
    user_id: str | None = Depends(get_current_user_id),
):
    """Walk-Forward 전진분석 실행"""
    from services.futures.data_loader import download_futures_data
    from services.futures.walk_forward import run_walk_forward

    try:
        parsed = body.parsed_strategy
        if not parsed and body.strategy_id != "local":
            from services.supabase_client import get_strategy_by_id
            strategy = await get_strategy_by_id(body.strategy_id)
            if not strategy:
                raise HTTPException(status_code=404, detail="Strategy not found")
            parsed = strategy["parsed_strategy"]

        if not parsed:
            raise HTTPException(status_code=400, detail="No strategy provided")

        # 데이터 로드
        symbol = body.symbol or parsed.get("target_pair", "BTCUSDT").replace("/", "")
        bars = await download_futures_data(
            symbol=symbol, interval=body.interval, days=body.days,
        )

        min_bars = (body.in_sample_days + body.out_sample_days) * 24
        if len(bars) < min_bars:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient data: need {min_bars}+ bars, got {len(bars)}",
            )

        # Walk-Forward 실행 (asyncio.to_thread로 이벤트 루프 블로킹 방지)
        import asyncio
        result = await asyncio.to_thread(
            run_walk_forward,
            bars=bars,
            strategy=parsed,
            param_ranges=body.param_ranges or {},
            in_sample_days=body.in_sample_days,
            out_sample_days=body.out_sample_days,
            windows=body.windows,
            objective=body.objective,
        )

        return result.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Walk-Forward 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Walk-Forward 분석 중 오류")


def _count_combinations(param_ranges: dict) -> int:
    """파라미터 조합 수 계산"""
    count = 1
    for values in param_ranges.values():
        if isinstance(values, list):
            count *= len(values)
    return count
