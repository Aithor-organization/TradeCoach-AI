import logging
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from models.strategy import StrategyCreate, StrategySave, StrategyUpdate
from dependencies import get_current_user_id
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
async def list_public_strategies(response: Response):
    """공개 전략 목록 (마켓플레이스용, 인증 불필요) - 전략 상세는 숨기고 요약만 반환"""
    import httpx
    from services.supabase_client import _rest_url, _headers, _is_available
    # 60초 캐시 — CDN/브라우저 레벨에서 불필요한 재조회 방지
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=30"

    if not _is_available():
        return {"strategies": []}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(
                _rest_url("strategies"),
                headers=_headers(),
                params={
                    "select": "id,name,parsed_strategy,created_at,status,mint_tx,mint_hash,marketplace_summary,marketplace_metrics",
                    "is_public": "eq.true",
                    "order": "created_at.desc",
                    "limit": "50",
                },
            )
            strategies = res.json() if res.status_code == 200 else []

            # 1단계: summary 처리 + strategy_ids 수집
            strategy_ids = []
            for s in strategies:
                ps = s.get("parsed_strategy", {}) or {}
                s["summary"] = {
                    "timeframe": ps.get("timeframe", ""),
                    "target_pair": ps.get("target_pair") or (ps.get("target_pairs", [""])[0] if ps.get("target_pairs") else ""),
                    "market_type": ps.get("market_type", ""),
                    "leverage": ps.get("leverage", 1),
                    "direction": ps.get("direction", "both"),
                    "indicator_count": len(ps.get("entry", {}).get("conditions", [])),
                }
                del s["parsed_strategy"]
                strategy_ids.append(s["id"])

            # 2단계: 온체인 정보를 IN 쿼리로 1회 배치 조회 (N+1 → 1)
            onchain_map: dict = {}
            if strategy_ids:
                ids_str = ",".join(str(sid) for sid in strategy_ids)
                onchain_res = await client.get(
                    _rest_url("onchain_strategies"),
                    headers=_headers(),
                    params={
                        "strategy_id": f"in.({ids_str})",
                        "select": "asset_id,strategy_hash,strategy_id",
                    },
                )
                if onchain_res.status_code == 200:
                    for row in onchain_res.json():
                        sid = row.get("strategy_id")
                        if sid and sid not in onchain_map:
                            onchain_map[sid] = {"asset_id": row.get("asset_id"), "strategy_hash": row.get("strategy_hash")}

            # 3단계: 매핑
            for s in strategies:
                s["onchain"] = onchain_map.get(s["id"])

        return {"strategies": strategies}
    except Exception as e:
        logger.error(f"공개 전략 목록 실패: {e}", exc_info=True)
        return {"strategies": []}


@router.get("/public/{strategy_id}")
async def get_public_strategy(strategy_id: str):
    """공개 전략 상세 (마켓플레이스 상세 페이지용, 인증 불필요, IP 보호)"""
    from services.supabase_client import get_strategy_by_id

    strategy = await get_strategy_by_id(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    if not strategy.get("is_public"):
        raise HTTPException(status_code=403, detail="비공개 전략입니다.")

    # parsed_strategy에서 공개 가능한 요약만 추출 (IP 보호)
    ps = strategy.get("parsed_strategy", {}) or {}
    strategy["summary"] = {
        "timeframe": ps.get("timeframe", ""),
        "target_pair": ps.get("target_pair") or (ps.get("target_pairs", [""])[0] if ps.get("target_pairs") else ""),
        "market_type": ps.get("market_type", ""),
        "leverage": ps.get("leverage", 1),
        "direction": ps.get("direction", "both"),
        "indicator_count": len(ps.get("entry", {}).get("conditions", [])),
    }
    # 전략 상세 제거
    strategy.pop("parsed_strategy", None)
    strategy.pop("raw_input", None)
    strategy.pop("user_id", None)

    return strategy


@router.post("/{strategy_id}/publish")
async def publish_to_marketplace(
    strategy_id: str,
    user_id: str | None = Depends(get_current_user_id),
):
    """전략을 마켓플레이스에 공개 등록 (트레이드 분석 + AI 요약 + DB 공개 + 블록체인 등록)"""
    from services.supabase_client import update_strategy_by_id, get_strategy_by_id
    import httpx
    from services.supabase_client import _rest_url, _headers, _is_available

    try:
        # 1. 전략 정보 조회
        strategy = await get_strategy_by_id(strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        # 2. 트레이드 세션 수집 + 성과 분석 + AI 요약 생성
        marketplace_metrics = {}
        marketplace_summary = ""
        try:
            # trade_sessions에서 해당 전략의 모든 세션 조회
            sessions = []
            if _is_available():
                async with httpx.AsyncClient(timeout=5.0) as client:
                    res = await client.get(
                        _rest_url("trade_sessions"),
                        headers=_headers(),
                        params={
                            "strategy_id": f"eq.{strategy_id}",
                            "select": "*",
                            "order": "created_at.desc",
                            "limit": "50",
                        },
                    )
                    sessions = res.json() if res.status_code == 200 else []

            if sessions:
                # 성과 지표 집계
                total_trades = sum(s.get("total_trades", 0) for s in sessions)
                winning_trades = sum(s.get("winning_trades", 0) for s in sessions)
                total_pnl = sum(s.get("total_pnl", 0) for s in sessions)
                win_rate = round(winning_trades / total_trades * 100, 1) if total_trades > 0 else 0
                avg_pnl = round(total_pnl / len(sessions), 2) if sessions else 0

                marketplace_metrics = {
                    "total_sessions": len(sessions),
                    "total_trades": total_trades,
                    "winning_trades": winning_trades,
                    "win_rate": win_rate,
                    "total_pnl": round(total_pnl, 2),
                    "avg_session_pnl": avg_pnl,
                }

                # AI 요약 생성 (Gemini)
                try:
                    from services.gemini import generate_marketplace_summary
                    marketplace_summary = await generate_marketplace_summary(
                        strategy_name=strategy.get("name", ""),
                        metrics=marketplace_metrics,
                        sessions=sessions[:10],  # 최근 10개 세션만
                    )
                except Exception as e:
                    logger.warning(f"AI 요약 생성 실패: {e}")
                    marketplace_summary = (
                        f"Strategy with {total_trades} trades across {len(sessions)} sessions. "
                        f"Win rate: {win_rate}%, Total PnL: {total_pnl}%."
                    )
        except Exception as e:
            logger.warning(f"트레이드 분석 실패: {e}")

        # 3. DB에서 is_public=true + 마켓플레이스 데이터 저장
        db_result = None
        update_data: dict = {"is_public": True}
        if marketplace_metrics:
            update_data["marketplace_metrics"] = marketplace_metrics
        if marketplace_summary:
            update_data["marketplace_summary"] = marketplace_summary
        try:
            db_result = await update_strategy_by_id(strategy_id, update_data)
        except Exception as e:
            logger.warning(f"마켓플레이스 데이터 저장 실패: {e}")
            try:
                db_result = await update_strategy_by_id(strategy_id, {"is_public": True})
            except Exception:
                pass

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
            "marketplace_metrics": marketplace_metrics or None,
            "marketplace_summary": marketplace_summary or None,
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


@router.get("/{strategy_id}/versions")
async def get_strategy_versions(
    strategy_id: str,
    user_id: Optional[str] = Depends(get_current_user_id),
):
    """전략의 민팅 버전 히스토리 조회"""
    from services.supabase_client import get_strategy_versions as db_get_versions

    try:
        versions = await db_get_versions(strategy_id)
        return {"versions": versions}
    except Exception as e:
        logger.error(f"버전 조회 실패: {e}", exc_info=True)
        return {"versions": []}


@router.post("/{strategy_id}/restore/{version_id}")
async def restore_strategy_version(
    strategy_id: str,
    version_id: str,
    user_id: Optional[str] = Depends(get_current_user_id),
):
    """민팅된 버전으로 전략 되돌리기"""
    from services.supabase_client import get_strategy_version, update_strategy_by_id

    try:
        if user_id:
            await _verify_strategy_owner(strategy_id, user_id)

        version = await get_strategy_version(version_id)
        if not version:
            raise HTTPException(status_code=404, detail="Version not found")
        if version.get("strategy_id") != strategy_id:
            raise HTTPException(status_code=403, detail="Version does not belong to this strategy")

        updated = await update_strategy_by_id(strategy_id, {
            "parsed_strategy": version["parsed_strategy"],
            "status": "verified",
            "mint_tx": version.get("mint_tx"),
            "mint_hash": version.get("mint_hash"),
            "mint_network": version.get("mint_network", "devnet"),
        })
        if not updated:
            raise HTTPException(status_code=404, detail="Strategy not found")

        return {
            "restored": True,
            "version": version.get("version"),
            "label": version.get("label"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"버전 복원 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="버전 복원 실패")


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
