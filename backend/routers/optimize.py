"""
Phase 2: 파라미터 최적화 + Walk-Forward API 엔드포인트.

POST /optimize/grid          — Grid Search 최적화 (비동기 작업)
POST /optimize/walk-forward  — Walk-Forward 전진분석 (비동기 작업)
GET  /optimize/job/{job_id}  — 작업 상태/결과 조회
"""

import asyncio
import logging
from fastapi import APIRouter, HTTPException, Request, Depends
from models.optimize import OptimizeRequest, WalkForwardRequest
from dependencies import get_current_user_id
from routers.auth import limiter
from services.job_store import create_job, get_job, run_job_in_background

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/grid")
@limiter.limit("5/minute")
async def run_grid_optimization(
    request: Request,
    body: OptimizeRequest,
    user_id: str | None = Depends(get_current_user_id),
):
    """Grid Search 파라미터 최적화 — 즉시 job_id 반환, 백그라운드 실행"""
    try:
        # 전략 로드 (빠른 DB 조회만 여기서 수행)
        parsed = body.parsed_strategy
        if not parsed and body.strategy_id != "local":
            from services.supabase_client import get_strategy_by_id
            strategy = await get_strategy_by_id(body.strategy_id)
            if not strategy:
                raise HTTPException(status_code=404, detail="Strategy not found")
            parsed = strategy["parsed_strategy"]

        if not parsed:
            raise HTTPException(status_code=400, detail="No strategy provided")

        # 즉시 job_id 반환, 데이터 다운로드+연산은 모두 백그라운드
        job = create_job()
        symbol = body.symbol or parsed.get("target_pair", "BTCUSDT").replace("/", "")
        interval = body.interval
        days = body.days
        param_ranges = body.param_ranges
        objective = body.objective
        max_combos = body.max_combinations
        search_method = body.search_method

        async def _run_async():
            from services.futures.data_loader import download_futures_data
            from services.futures.optimizer import run_optimization

            bars = await download_futures_data(
                symbol=symbol, interval=interval, days=days,
            )
            if len(bars) < 50:
                raise ValueError("Insufficient data")

            results = await asyncio.to_thread(
                run_optimization,
                bars=bars,
                strategy=parsed,
                param_ranges=param_ranges,
                objective=objective,
                max_combinations=max_combos,
                top_n=10,
                search_method=search_method,
            )
            return {
                "results": results,
                "total_tested": min(max_combos, _count_combinations(param_ranges)),
                "objective": objective,
                "search_method": search_method,
            }

        run_job_in_background(job, _run_async())

        return {"job_id": job.id, "status": "pending"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"최적화 시작 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"최적화 시작 중 오류: {e}")


@router.post("/walk-forward")
@limiter.limit("5/minute")
async def run_walk_forward(
    request: Request,
    body: WalkForwardRequest,
    user_id: str | None = Depends(get_current_user_id),
):
    """Walk-Forward 전진분석 — 즉시 job_id 반환, 백그라운드 실행"""
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

        # 즉시 job_id 반환
        job = create_job()
        symbol = body.symbol or parsed.get("target_pair", "BTCUSDT").replace("/", "")
        interval = body.interval
        days = body.days
        param_ranges = body.param_ranges or {}
        in_sample_days = body.in_sample_days
        out_sample_days = body.out_sample_days
        windows = body.windows
        objective = body.objective

        async def _run_async():
            from services.futures.data_loader import download_futures_data
            from services.futures.walk_forward import run_walk_forward as wf_run

            bars = await download_futures_data(
                symbol=symbol, interval=interval, days=days,
            )
            min_bars = (in_sample_days + out_sample_days) * 24
            if len(bars) < min_bars:
                raise ValueError(
                    f"Insufficient data: need {min_bars}+ bars, got {len(bars)}"
                )

            result = await asyncio.to_thread(
                wf_run,
                bars=bars,
                strategy=parsed,
                param_ranges=param_ranges,
                in_sample_days=in_sample_days,
                out_sample_days=out_sample_days,
                windows=windows,
                objective=objective,
            )
            return result.to_dict()

        run_job_in_background(job, _run_async())

        return {"job_id": job.id, "status": "pending"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Walk-Forward 시작 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Walk-Forward 시작 중 오류: {e}")


@router.get("/job/{job_id}")
async def get_job_status(job_id: str):
    """작업 상태 및 결과 조회 (폴링용)"""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()


def _count_combinations(param_ranges: dict) -> int:
    """파라미터 조합 수 계산"""
    count = 1
    for values in param_ranges.values():
        if isinstance(values, list):
            count *= len(values)
    return count
