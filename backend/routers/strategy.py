from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.strategy import StrategyCreate, StrategyResponse, StrategySave, StrategyUpdate
from typing import Optional

router = APIRouter()


@router.post("/parse")
async def parse_strategy(body: StrategyCreate):
    """자연어/텍스트 → 구조화된 전략 JSON"""
    from services.gemini import parse_strategy_text

    parsed = await parse_strategy_text(body.raw_input)
    return {"parsed_strategy": parsed}


@router.post("/save")
async def save_strategy(body: StrategySave):
    """파싱된 전략을 DB에 저장"""
    from services.supabase_client import save_strategy as db_save

    saved = await db_save(
        user_id=None,
        name=body.name,
        raw_input=body.raw_input,
        input_type=body.input_type,
        parsed_strategy=body.parsed_strategy,
    )
    return saved


@router.get("/list")
async def list_strategies(user_id: Optional[str] = None):
    """내 전략 목록 (MVP: user_id 파라미터로 필터)"""
    from services.supabase_client import get_strategies

    strategies = await get_strategies(user_id)
    return {"strategies": strategies}


@router.get("/{strategy_id}")
async def get_strategy(strategy_id: str):
    """전략 상세 조회"""
    from services.supabase_client import get_strategy_by_id

    strategy = await get_strategy_by_id(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy


class ForkRequest(BaseModel):
    name: Optional[str] = None


@router.post("/fork/{strategy_id}")
async def fork_strategy(strategy_id: str, body: Optional[ForkRequest] = None):
    """예시 전략을 DB에 복사하여 수정 가능한 사본 생성"""
    from services.supabase_client import get_strategy_by_id, save_strategy as db_save

    source = await get_strategy_by_id(strategy_id)
    if not source:
        raise HTTPException(status_code=404, detail="Strategy not found")

    fork_name = (body.name if body and body.name else None) or source.get("name", "복사된 전략")

    saved = await db_save(
        user_id=None,
        name=fork_name,
        raw_input=source.get("raw_input", ""),
        input_type=source.get("input_type", "text"),
        parsed_strategy=source.get("parsed_strategy", {}),
    )
    return saved


@router.put("/{strategy_id}")
async def update_strategy(strategy_id: str, body: StrategyUpdate):
    """전략 수정"""
    from services.supabase_client import update_strategy_by_id

    updated = await update_strategy_by_id(strategy_id, body.model_dump(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return updated


@router.delete("/{strategy_id}")
async def delete_strategy(strategy_id: str):
    """전략 삭제"""
    from services.supabase_client import delete_strategy_by_id

    success = await delete_strategy_by_id(strategy_id)
    if not success:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return {"deleted": True}
