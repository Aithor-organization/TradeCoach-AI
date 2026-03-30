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
    """파싱된 전략을 DB에 저장 (로그인 필수)"""
    if not user_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다. 전략을 저장하려면 먼저 로그인해주세요.")
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


@router.get("/public")
async def list_public_strategies():
    """공개 전략 목록 (마켓플레이스용, 인증 불필요)"""
    import httpx
    from services.supabase_client import _rest_url, _headers, _is_available

    if not _is_available():
        return {"strategies": []}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(
                _rest_url("strategies"),
                headers=_headers(),
                params={
                    "select": "id,name,parsed_strategy,created_at",
                    "is_public": "eq.true",
                    "order": "created_at.desc",
                    "limit": "50",
                },
            )
            strategies = res.json() if res.status_code == 200 else []

            # 온체인 정보 추가
            for s in strategies:
                onchain_res = await client.get(
                    _rest_url("onchain_strategies"),
                    headers=_headers(),
                    params={"strategy_id": f"eq.{s['id']}", "select": "asset_id,strategy_hash", "limit": "1"},
                )
                onchain_data = onchain_res.json() if onchain_res.status_code == 200 else []
                s["onchain"] = onchain_data[0] if onchain_data else None

        return {"strategies": strategies}
    except Exception as e:
        logger.error(f"공개 전략 목록 실패: {e}", exc_info=True)
        return {"strategies": []}


@router.post("/{strategy_id}/publish")
async def publish_to_marketplace(
    strategy_id: str,
    user_id: str | None = Depends(get_current_user_id),
):
    """전략을 마켓플레이스에 공개 등록 (DB 공개 + Anchor 블록체인 등록)"""
    from services.supabase_client import update_strategy_by_id, get_strategy_by_id

    try:
        # 1. 전략 정보 조회
        strategy = await get_strategy_by_id(strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        # 2. DB에서 is_public=true로 설정 (컬럼 없으면 스킵)
        db_result = None
        try:
            db_result = await update_strategy_by_id(strategy_id, {"is_public": True})
        except Exception as e:
            logger.warning(f"is_public 업데이트 스킵 (컬럼 미존재?): {e}")

        # 3. Anchor 블록체인에 전략 등록
        anchor_result = None
        try:
            from services.blockchain.strategy_registry_client import register_strategy_onchain
            parsed = strategy.get("parsed_strategy", {})
            anchor_result = await register_strategy_onchain(
                strategy_id=strategy_id,
                strategy_name=strategy.get("name", "Unknown"),
                strategy_data={
                    "description": parsed.get("description", str(parsed.get("entry", ""))),
                    "market": "BinanceFutures",
                    "time_frame": parsed.get("timeframe", "H4"),
                    "symbols": [parsed.get("target_pair", "BTCUSDT")],
                    "backtest": {},
                    "price_lamports": 100_000_000,
                    "rent_lamports_per_day": 10_000_000,
                },
            )
        except Exception as e:
            logger.warning(f"Anchor 블록체인 등록 실패 (비치명적): {e}")
            anchor_result = {"error": str(e)}

        return {
            "strategy_id": strategy_id,
            "is_public": db_result is not None,
            "blockchain": anchor_result,
            "message": "마켓플레이스에 등록되었습니다" + (
                f" (TX: {anchor_result.get('tx_signature', 'N/A')})" if anchor_result and not anchor_result.get("error") else ""
            ),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"마켓플레이스 등록 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{strategy_id}/unpublish")
async def unpublish_from_marketplace(
    strategy_id: str,
    user_id: str | None = Depends(get_current_user_id),
):
    """전략을 마켓플레이스에서 비공개 전환"""
    from services.supabase_client import update_strategy_by_id

    try:
        result = await update_strategy_by_id(strategy_id, {"is_public": False})
        if not result:
            raise HTTPException(status_code=404, detail="Strategy not found")
        return {"strategy_id": strategy_id, "is_public": False, "message": "마켓플레이스에서 제거되었습니다"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"마켓플레이스 해제 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        updates = body.model_dump(exclude_none=True)
        # 전략 내용이 수정되면 status를 draft로 리셋 (재민팅 필요)
        if "parsed_strategy" in updates and "status" not in updates:
            updates["status"] = "draft"
        updated = await update_strategy_by_id(strategy_id, updates)
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
