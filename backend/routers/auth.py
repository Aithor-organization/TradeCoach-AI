from fastapi import APIRouter, Depends, HTTPException, Request
from models.user import (
    WalletAuthRequest, WalletVerifyRequest, NonceResponse, AuthResponse, UserResponse,
    EmailRegisterRequest, EmailLoginRequest, EmailAuthResponse,
    PasswordResetRequest, PasswordResetConfirm, PasswordResetResponse,
)
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

# 🔴 MVP 비밀번호 재설정 토큰 저장소 (인메모리, 서버 재시작 시 휘발).
# Production에서는 `password_reset_tokens` 테이블 또는 Redis로 이전 필요.
# 토큰은 1회 사용 후 즉시 폐기, TTL 30분.
_reset_tokens: dict[str, dict] = {}
RESET_TOKEN_TTL_MINUTES = 30


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
        # 🔴 SECURITY: 이메일 존재 여부에 따라 다른 응답을 주면 사용자 열거(user enumeration) 취약점.
        # 아래 3가지 실패 케이스를 모두 동일한 401 + 동일 메시지로 통일.
        GENERIC_AUTH_ERROR = "이메일 또는 비밀번호가 일치하지 않습니다."

        if res.status_code != 200 or not res.json():
            logger.info(f"로그인 실패(미가입 이메일): {body.email}")
            raise HTTPException(status_code=401, detail=GENERIC_AUTH_ERROR)

        user = res.json()[0]

        # 비밀번호 검증
        stored_hash = user.get("password_hash")
        if not stored_hash:
            # password_hash가 NULL인 계정 (과거 wallet-only 가입자). admin1234 자동 덮어쓰기는 삭제됨.
            # 이런 계정은 비밀번호 재설정 플로우 필요 — 사용자에게는 동일한 메시지로 응답하여 이메일 존재 노출 방지.
            logger.warning(f"로그인 실패(password_hash 미설정): {body.email}")
            raise HTTPException(status_code=401, detail=GENERIC_AUTH_ERROR)
        if not bcrypt.checkpw(body.password.encode("utf-8"), stored_hash.encode("utf-8")):
            logger.info(f"로그인 실패(비밀번호 불일치): {body.email}")
            raise HTTPException(status_code=401, detail=GENERIC_AUTH_ERROR)

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
    from services.supabase_client import get_or_create_user_by_email

    if not body.email or not body.name or not body.password:
        raise HTTPException(status_code=400, detail="Name, email and password are required")

    try:
        # 비밀번호를 먼저 해싱하여 사용자 생성 시 함께 INSERT
        password_hash = bcrypt.hashpw(body.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        # 🔴 SECURITY: fail_if_exists=True — 중복 이메일 시 None 반환 받기.
        # 기존 유저 덮어쓰기/JWT 발급은 계정 탈취 취약점이므로 차단.
        user = await get_or_create_user_by_email(
            body.email, body.name, password_hash=password_hash, fail_if_exists=True,
        )

        if user is None:
            raise HTTPException(
                status_code=409,
                detail="이미 가입된 이메일입니다. 로그인해주세요.",
            )

        # DB 저장 검증 — 실제로 조회 가능한지 + password_hash도 제대로 저장됐는지 확인
        from services.supabase_client import _is_available, _get_client, _rest_url, _headers
        if _is_available():
            verify_client = _get_client()
            verify_res = await verify_client.get(
                _rest_url("users"),
                headers=_headers(),
                params={"wallet_address": f"eq.{body.email}", "select": "id,password_hash"},
            )
            if verify_res.status_code != 200 or not verify_res.json():
                logger.error(f"회원가입 DB 저장 검증 실패: 유저가 DB에 없음 (email={body.email})")
                raise HTTPException(status_code=500, detail="User created but not found in DB — please retry")
            verified_user = verify_res.json()[0]
            if not verified_user.get("password_hash"):
                # password_hash 컬럼 자체가 없거나, PATCH도 실패해서 NULL로 남은 경우.
                # 이 상태로 JWT를 발급하면 유저는 "가입 성공"으로 보이지만 로그인 불가.
                logger.error(
                    f"회원가입 후 password_hash 저장 안 됨 — Supabase 컬럼 점검 필요 (email={body.email})"
                )
                raise HTTPException(
                    status_code=500,
                    detail="비밀번호 저장에 실패했습니다. 관리자에게 문의해주세요.",
                )

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


@router.post("/password/reset-request", response_model=PasswordResetResponse)
@limiter.limit("3/minute")
async def password_reset_request(request: Request, body: PasswordResetRequest):
    """비밀번호 재설정 토큰 발급 요청.

    🔴 SECURITY: 이메일 존재 여부에 관계없이 동일한 응답을 반환해 enumeration을 차단한다.
    실제 이메일 발송 인프라가 통합되기 전까지는 재설정 링크를 서버 로그에만 기록한다
    (운영자가 수동으로 사용자에게 전달하거나, 향후 Email 서비스 연동 시 이 부분만 교체).
    """
    from services.supabase_client import _is_available, _get_client, _rest_url, _headers

    try:
        if _is_available():
            client = _get_client()
            res = await client.get(
                _rest_url("users"),
                headers=_headers(),
                params={"wallet_address": f"eq.{body.email}", "select": "id,wallet_address"},
            )
            if res.status_code == 200 and res.json():
                user = res.json()[0]
                token = secrets.token_urlsafe(48)  # 384-bit entropy
                expires_at = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_TTL_MINUTES)
                _reset_tokens[token] = {
                    "user_id": user["id"],
                    "email": body.email,
                    "expires_at": expires_at,
                }
                # TODO(email-integration): 실제 이메일 발송으로 교체. 현재는 로그로만 출력.
                reset_link = f"/auth/password/reset?token={token}"
                logger.warning(
                    "[PASSWORD_RESET] email=%s expires_at=%s link_path=%s (전송 인프라 없음: 수동 전달 필요)",
                    body.email, expires_at.isoformat(), reset_link,
                )
            else:
                logger.info(f"[PASSWORD_RESET] 미등록 이메일 요청(무시): {body.email}")
    except Exception as e:
        # 실패해도 응답은 동일 — enumeration 방지
        logger.error(f"password_reset_request 내부 오류 (email={body.email}): {e}", exc_info=True)

    return PasswordResetResponse()


@router.post("/password/reset-confirm")
@limiter.limit("5/minute")
async def password_reset_confirm(request: Request, body: PasswordResetConfirm):
    """재설정 토큰으로 새 비밀번호 설정 (1회 사용)."""
    import bcrypt
    from services.supabase_client import _is_available, _get_client, _rest_url, _headers

    token_data = _reset_tokens.get(body.token)
    if not token_data or token_data["expires_at"] < datetime.now(timezone.utc):
        # 만료된 경우 명시적 제거
        if token_data:
            _reset_tokens.pop(body.token, None)
        raise HTTPException(status_code=400, detail="유효하지 않거나 만료된 토큰입니다.")

    if not _is_available():
        raise HTTPException(status_code=503, detail="Service unavailable")

    try:
        new_hash = bcrypt.hashpw(body.new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        client = _get_client()
        res = await client.patch(
            _rest_url("users"),
            headers=_headers(),
            params={"id": f"eq.{token_data['user_id']}"},
            json={"password_hash": new_hash},
        )
        if res.status_code not in (200, 204):
            logger.error(f"password_reset_confirm: PATCH 실패 {res.status_code}")
            raise HTTPException(status_code=500, detail="비밀번호 업데이트 실패")

        # 토큰 1회 사용 후 즉시 폐기
        _reset_tokens.pop(body.token, None)
        logger.info(f"password reset success: user_id={token_data['user_id']}")
        return {"success": True, "message": "비밀번호가 재설정되었습니다. 로그인해주세요."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"password_reset_confirm 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="비밀번호 재설정 실패")
