import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from models.strategy import StrategyCreate, StrategyResponse, StrategySave, StrategyUpdate
from dependencies import get_current_user_id, require_auth
from typing import Optional

router = APIRouter()
logger = logging.getLogger(__name__)


async def _verify_strategy_owner(strategy_id: str, user_id: str) -> dict:
    """전략 소유권 검증. 예시 전략은 읽기만 허용."""
    from services.supabase_client import get_strategy_by_id

    strategy = await get_strategy_by_id(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # 예시 전략 (user_id 없음)은 읽기 전용
    owner = strategy.get("user_id")
    if owner and owner != user_id:
        raise HTTPException(status_code=403, detail="이 전략에 대한 권한이 없습니다.")

    return strategy


@router.post("/parse")
async def parse_strategy(body: StrategyCreate):
    """자연어/텍스트 → 구조화된 전략 JSON"""
    from services.gemini import parse_strategy_text

    try:
        parsed = await parse_strategy_text(body.raw_input)
        return {"parsed_strategy": parsed}
    except Exception as e:
        logger.error(f"전략 파싱 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="전략 파싱 중 오류가 발생했습니다.")


@router.post("/save")
async def save_strategy(
    body: StrategySave,
    user_id: Optional[str] = Depends(get_current_user_id),
):
    """파싱된 전략을 DB에 저장 (로그인 시 user_id 자동 연결)"""
    from services.supabase_client import save_strategy as db_save

    try:
        saved = await db_save(
            user_id=user_id,
            name=body.name,
            raw_input=body.raw_input,
            input_type=body.input_type,
            parsed_strategy=body.parsed_strategy,
        )
        return saved
    except Exception as e:
        logger.error(f"전략 저장 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="전략 저장 중 오류가 발생했습니다.")


@router.get("/list")
async def list_strategies(
    user_id: Optional[str] = Depends(get_current_user_id),
):
    """내 전략 목록 (JWT에서 user_id 자동 추출)"""
    from services.supabase_client import get_strategies

    try:
        strategies = await get_strategies(user_id)
        return {"strategies": strategies}
    except Exception as e:
        logger.error(f"전략 목록 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="전략 목록을 불러올 수 없습니다.")


@router.get("/{strategy_id}")
async def get_strategy(
    strategy_id: str,
    user_id: Optional[str] = Depends(get_current_user_id),
):
    """전략 상세 조회 (소유권 검증)"""
    from services.supabase_client import get_strategy_by_id

    strategy = await get_strategy_by_id(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # 예시 전략(user_id 없음)은 누구나 조회 가능
    owner = strategy.get("user_id")
    if owner and user_id and owner != user_id:
        raise HTTPException(status_code=403, detail="이 전략에 대한 권한이 없습니다.")

    return strategy


class ForkRequest(BaseModel):
    name: Optional[str] = None


@router.post("/fork/{strategy_id}")
async def fork_strategy(
    strategy_id: str,
    body: Optional[ForkRequest] = None,
    user_id: Optional[str] = Depends(get_current_user_id),
):
    """예시 전략을 DB에 복사하여 수정 가능한 사본 생성"""
    from services.supabase_client import get_strategy_by_id, save_strategy as db_save

    try:
        source = await get_strategy_by_id(strategy_id)
        if not source:
            raise HTTPException(status_code=404, detail="Strategy not found")

        fork_name = (body.name if body and body.name else None) or source.get("name", "복사된 전략")

        saved = await db_save(
            user_id=user_id,
            name=fork_name,
            raw_input=source.get("raw_input", ""),
            input_type=source.get("input_type", "text"),
            parsed_strategy=source.get("parsed_strategy", {}),
        )
        return saved
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"전략 포크 실패 (strategy_id={strategy_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="전략 복사 중 오류가 발생했습니다.")


@router.put("/{strategy_id}")
async def update_strategy(
    strategy_id: str,
    body: StrategyUpdate,
    user_id: Optional[str] = Depends(get_current_user_id),
):
    """전략 수정 (소유권 검증, 비로그인 시에도 소유자 없는 전략 수정 가능)"""
    from services.supabase_client import update_strategy_by_id

    try:
        if user_id:
            await _verify_strategy_owner(strategy_id, user_id)
        updated = await update_strategy_by_id(strategy_id, body.model_dump(exclude_none=True))
        if not updated:
            raise HTTPException(status_code=404, detail="Strategy not found")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"전략 수정 실패 (strategy_id={strategy_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="전략 수정 중 오류가 발생했습니다.")


@router.delete("/{strategy_id}")
async def delete_strategy(
    strategy_id: str,
    user_id: Optional[str] = Depends(get_current_user_id),
):
    """전략 삭제 (소유권 검증)"""
    from services.supabase_client import delete_strategy_by_id

    try:
        if user_id:
            await _verify_strategy_owner(strategy_id, user_id)
        success = await delete_strategy_by_id(strategy_id)
        if not success:
            raise HTTPException(status_code=404, detail="Strategy not found")
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"전략 삭제 실패 (strategy_id={strategy_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="전략 삭제 중 오류가 발생했습니다.")
