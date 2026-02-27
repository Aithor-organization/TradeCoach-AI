from fastapi import APIRouter, Depends, HTTPException, Request
from models.user import WalletAuthRequest, WalletVerifyRequest, NonceResponse, AuthResponse, UserResponse
from config import get_settings
from dependencies import require_auth
from slowapi import Limiter
from slowapi.util import get_remote_address
import secrets
import logging
from datetime import datetime, timedelta, timezone
from jose import jwt

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

# 인메모리 폴백 (Supabase 연결 안 될 때)
_nonce_store: dict[str, str] = {}


@router.post("/wallet", response_model=NonceResponse)
@limiter.limit("10/minute")
async def request_nonce(request: Request, body: WalletAuthRequest):
    """지갑 주소로 nonce 요청"""
    try:
        from services.supabase_client import save_nonce

        nonce = secrets.token_hex(32)

        # Supabase에 저장 시도, 실패 시 인메모리 폴백
        saved = await save_nonce(body.wallet_address, nonce)
        if not saved:
            _nonce_store[body.wallet_address] = nonce

        return NonceResponse(nonce=nonce)
    except Exception as e:
        logger.error(f"Nonce 생성 실패 (wallet={body.wallet_address}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="인증 요청 처리 중 오류가 발생했습니다.")


@router.post("/verify", response_model=AuthResponse)
@limiter.limit("5/minute")
async def verify_wallet(request: Request, body: WalletVerifyRequest):
    """서명 검증 후 JWT 발급"""
    from services.supabase_client import get_nonce, delete_nonce, get_or_create_user

    # Supabase에서 nonce 조회, 없으면 인메모리 폴백
    stored_nonce = await get_nonce(body.wallet_address)
    if not stored_nonce:
        stored_nonce = _nonce_store.get(body.wallet_address)

    if not stored_nonce or stored_nonce != body.nonce:
        raise HTTPException(status_code=401, detail="Invalid or expired nonce")

    try:
        # TODO: 실제 Solana 서명 검증 (nacl.sign.detached.verify)
        # MVP에서는 nonce 매칭으로 간소화

        # nonce 삭제 (양쪽 모두)
        await delete_nonce(body.wallet_address)
        _nonce_store.pop(body.wallet_address, None)

        # Supabase에서 사용자 조회 또는 생성
        user = await get_or_create_user(body.wallet_address)

        # JWT 생성
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
        token_data = {
            "sub": user["id"],
            "wallet": body.wallet_address,
            "exp": expire,
        }
        access_token = jwt.encode(token_data, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        return AuthResponse(
            access_token=access_token,
            user=UserResponse(
                id=user["id"],
                wallet_address=user["wallet_address"],
                display_name=user.get("display_name"),
                tier=user.get("tier", "free"),
                created_at=user["created_at"],
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"지갑 인증 실패 (wallet={body.wallet_address}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="인증 처리 중 오류가 발생했습니다.")


@router.get("/me", response_model=UserResponse)
async def get_current_user(user_id: str = Depends(require_auth)):
    """현재 인증된 사용자 정보"""
    try:
        import httpx
        from services.supabase_client import _headers, _rest_url, _is_available

        if not _is_available():
            raise HTTPException(status_code=401, detail="Not authenticated")

        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(
                _rest_url("users"),
                headers=_headers(),
                params={"id": f"eq.{user_id}", "select": "*"},
            )
            if res.status_code == 200 and res.json():
                u = res.json()[0]
                return UserResponse(
                    id=u["id"],
                    wallet_address=u["wallet_address"],
                    display_name=u.get("display_name"),
                    tier=u.get("tier", "free"),
                    created_at=u["created_at"],
                )

        raise HTTPException(status_code=401, detail="User not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 조회 실패 (user_id={user_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="사용자 정보 조회 중 오류가 발생했습니다.")
