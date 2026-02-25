from fastapi import APIRouter, Depends, HTTPException
from models.user import WalletAuthRequest, WalletVerifyRequest, NonceResponse, AuthResponse, UserResponse
from config import get_settings
import secrets
from datetime import datetime, timedelta, timezone
from jose import jwt

router = APIRouter()
settings = get_settings()

# 임시 nonce 저장 (MVP: 메모리, 프로덕션: Redis)
_nonce_store: dict[str, str] = {}


@router.post("/wallet", response_model=NonceResponse)
async def request_nonce(body: WalletAuthRequest):
    """지갑 주소로 nonce 요청"""
    nonce = secrets.token_hex(32)
    _nonce_store[body.wallet_address] = nonce
    return NonceResponse(nonce=nonce)


@router.post("/verify", response_model=AuthResponse)
async def verify_wallet(body: WalletVerifyRequest):
    """서명 검증 후 JWT 발급"""
    stored_nonce = _nonce_store.get(body.wallet_address)
    if not stored_nonce or stored_nonce != body.nonce:
        raise HTTPException(status_code=401, detail="Invalid or expired nonce")

    # TODO: 실제 Solana 서명 검증 (nacl.sign.detached.verify)
    # MVP에서는 nonce 매칭으로 간소화, Day 6에서 구현

    del _nonce_store[body.wallet_address]

    # Supabase에서 사용자 조회 또는 생성
    from services.supabase_client import get_or_create_user
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


@router.get("/me", response_model=UserResponse)
async def get_current_user():
    """현재 인증된 사용자 정보 (Day 6에서 JWT 미들웨어 추가)"""
    raise HTTPException(status_code=401, detail="Not authenticated")
