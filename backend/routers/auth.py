from fastapi import APIRouter, Depends, HTTPException, Request
from models.user import WalletAuthRequest, WalletVerifyRequest, NonceResponse, AuthResponse, UserResponse, EmailRegisterRequest, EmailLoginRequest, EmailAuthResponse
from config import get_settings
from dependencies import require_auth
from slowapi import Limiter
from slowapi.util import get_remote_address
import secrets
import logging
from datetime import datetime, timedelta, timezone
from jose import jwt
import nacl.signing
import nacl.exceptions
import base58

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)


def verify_solana_signature(wallet_address: str, nonce: str, signature: str) -> bool:
    """Solana 지갑 서명 검증 (Ed25519).

    서명 대상 메시지: nonce 문자열 (UTF-8 바이트).
    서명: base58 인코딩된 Ed25519 서명 (64 bytes).
    """
    try:
        # 지갑 주소(공개 키)를 base58 디코딩
        public_key_bytes = base58.b58decode(wallet_address)
        if len(public_key_bytes) != 32:
            logger.warning(f"잘못된 공개 키 길이: {len(public_key_bytes)} (expected 32)")
            return False

        # 서명을 base58 디코딩
        signature_bytes = base58.b58decode(signature)
        if len(signature_bytes) != 64:
            logger.warning(f"잘못된 서명 길이: {len(signature_bytes)} (expected 64)")
            return False

        # nacl VerifyKey로 검증
        verify_key = nacl.signing.VerifyKey(public_key_bytes)
        message_bytes = nonce.encode("utf-8")
        verify_key.verify(message_bytes, signature_bytes)
        return True
    except (nacl.exceptions.BadSignatureError, nacl.exceptions.CryptoError):
        logger.warning(f"서명 검증 실패 (wallet={wallet_address})")
        return False
    except Exception as e:
        logger.error(f"서명 검증 중 예외 (wallet={wallet_address}): {e}")
        return False


def _create_jwt_token(user_id: str, **extra_claims) -> str:
    """통일된 JWT 토큰 생성. exp는 Unix timestamp(int)로 직렬화."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.jwt_expire_minutes)
    token_data = {
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        **extra_claims,
    }
    return jwt.encode(token_data, settings.jwt_secret, algorithm=settings.jwt_algorithm)

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
        # Solana Ed25519 서명 검증
        if not verify_solana_signature(body.wallet_address, stored_nonce, body.signature):
            raise HTTPException(status_code=401, detail="Invalid signature")

        # nonce 삭제 (리플레이 방지 — 양쪽 모두)
        await delete_nonce(body.wallet_address)
        _nonce_store.pop(body.wallet_address, None)

        # Supabase에서 사용자 조회 또는 생성
        user = await get_or_create_user(body.wallet_address)

        # 통일된 JWT 생성
        access_token = _create_jwt_token(user["id"], wallet=body.wallet_address)

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


@router.post("/login", response_model=EmailAuthResponse)
@limiter.limit("10/minute")
async def login_with_email(request: Request, body: EmailLoginRequest):
    """이메일 + 비밀번호로 기존 사용자 로그인"""
    import bcrypt
    from services.supabase_client import _is_available, _rest_url, _headers, _get_client

    if not body.email or not body.password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    try:
        if not _is_available():
            raise HTTPException(status_code=503, detail="Service unavailable")

        client = _get_client()
        res = await client.get(
            _rest_url("users"),
            headers=_headers(),
            params={"wallet_address": f"eq.{body.email}", "select": "id,wallet_address,display_name,tier,password_hash,created_at"},
        )
        if res.status_code != 200 or not res.json():
            raise HTTPException(status_code=404, detail="등록되지 않은 이메일입니다. 먼저 회원가입을 해주세요.")

        user = res.json()[0]

        # 비밀번호 검증
        stored_hash = user.get("password_hash")
        if not stored_hash:
            # 기존 유저(비밀번호 미설정): 기본 비밀번호 admin1234로 해시 생성 후 저장
            default_pw = "admin1234"
            new_hash = bcrypt.hashpw(default_pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            try:
                await client.patch(
                    _rest_url("users"),
                    headers=_headers(),
                    params={"id": f"eq.{user['id']}"},
                    json={"password_hash": new_hash},
                )
                logger.info(f"기존 유저에 기본 비밀번호 설정: {body.email}")
            except Exception as e:
                logger.warning(f"기본 비밀번호 저장 실패: {e}")
            stored_hash = new_hash
        if not bcrypt.checkpw(body.password.encode("utf-8"), stored_hash.encode("utf-8")):
            raise HTTPException(status_code=401, detail="비밀번호가 일치하지 않습니다.")

        access_token = _create_jwt_token(
            user["id"],
            email=body.email,
            email_verified=False,
        )

        return EmailAuthResponse(
            access_token=access_token,
            user_id=user["id"],
            name=user.get("display_name", ""),
            email=body.email,
            email_verified=False,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"이메일 로그인 실패 (email={body.email}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Login failed")


@router.post("/register", response_model=EmailAuthResponse)
@limiter.limit("5/minute")
async def register_with_email(request: Request, body: EmailRegisterRequest):
    """이름 + 이메일 + 비밀번호로 회원가입"""
    import bcrypt
    from services.supabase_client import get_or_create_user_by_email, _get_client, _rest_url, _headers

    if not body.email or not body.name or not body.password:
        raise HTTPException(status_code=400, detail="Name, email and password are required")

    try:
        user = await get_or_create_user_by_email(body.email, body.name)

        # 비밀번호 해싱 후 저장
        if user:
            password_hash = bcrypt.hashpw(body.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            try:
                client = _get_client()
                await client.patch(
                    _rest_url("users"),
                    headers=_headers(),
                    params={"id": f"eq.{user['id']}"},
                    json={"password_hash": password_hash},
                )
            except Exception as e:
                logger.warning(f"비밀번호 저장 실패 (비치명적): {e}")
        if not user:
            raise HTTPException(status_code=500, detail="Failed to create user")

        # 통일된 JWT 생성 (email_verified는 향후 이메일 인증 플로우용)
        access_token = _create_jwt_token(
            user["id"],
            email=body.email,
            email_verified=False,
        )

        return EmailAuthResponse(
            access_token=access_token,
            user_id=user["id"],
            name=user.get("display_name", body.name),
            email=body.email,
            email_verified=False,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"이메일 가입 실패 (email={body.email}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Registration failed")
