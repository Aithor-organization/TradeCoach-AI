"""
라이센스 만료 시 전략 접근 차단 미들웨어
StrategyVault의 Token-2022 Transfer Hook 패턴을 Python으로 구현
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import Request, HTTPException

logger = logging.getLogger(__name__)


async def check_license_access(
    strategy_id: str,
    user_wallet: str,
    db=None,
) -> bool:
    """
    사용자가 해당 전략에 대한 유효한 라이센스를 보유하는지 확인.

    Returns:
        True: 접근 허용 (유효한 라이센스 있음 또는 전략 소유자)
        False: 접근 거부

    Raises:
        HTTPException 403: 라이센스 만료 또는 없음
    """
    if not db:
        return True  # DB 없으면 검증 스킵

    try:
        # 1. 전략 소유자인지 확인
        listing = db.table("strategy_listings").select("creator_address").eq(
            "strategy_id", strategy_id
        ).single().execute()

        if listing.data and listing.data.get("creator_address") == user_wallet:
            return True  # 소유자는 항상 접근 가능

        # 2. 유효한 라이센스 확인 (구매 또는 미만료 렌탈)
        licenses = db.table("licenses").select("*").eq(
            "strategy_id", strategy_id
        ).eq(
            "holder_address", user_wallet
        ).eq(
            "status", "active"
        ).execute()

        if not licenses.data:
            raise HTTPException(
                status_code=403,
                detail="이 전략에 대한 유효한 라이센스가 없습니다. 구매 또는 대여가 필요합니다."
            )

        for lic in licenses.data:
            # 영구 구매 라이센스
            if lic.get("license_type") == "purchase":
                return True

            # 렌탈 라이센스 — 만료 확인
            if lic.get("license_type") == "rental":
                expires = lic.get("expires_at")
                if expires:
                    exp_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
                    if exp_dt > datetime.now(timezone.utc):
                        return True
                    else:
                        # 만료된 렌탈 → 비활성화
                        db.table("licenses").update(
                            {"status": "expired"}
                        ).eq("id", lic["id"]).execute()
                        logger.info(
                            "렌탈 라이센스 만료 처리: license_id=%s strategy=%s",
                            lic["id"], strategy_id
                        )

        raise HTTPException(
            status_code=403,
            detail="라이센스가 만료되었습니다. 갱신이 필요합니다."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.warning("라이센스 확인 실패 (접근 허용): %s", e)
        return True  # DB 오류 시 접근 허용 (서비스 중단 방지)


def require_license(strategy_id_param: str = "strategy_id"):
    """
    FastAPI Depends로 사용할 라이센스 검증 의존성 팩토리.

    Usage:
        @router.get("/strategy/{strategy_id}/signals")
        async def get_signals(
            strategy_id: str,
            _license = Depends(require_license("strategy_id"))
        ):
            ...
    """
    from fastapi import Depends

    async def _check(request: Request):
        strategy_id = request.path_params.get(strategy_id_param)
        user_wallet = request.headers.get("x-wallet-address", "")

        if not strategy_id or not user_wallet:
            return True  # 파라미터 없으면 스킵

        try:
            from database import get_supabase
            db = get_supabase()
        except Exception:
            db = None

        return await check_license_access(strategy_id, user_wallet, db)

    return Depends(_check)
