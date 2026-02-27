"""JWT 인증 의존성 모듈"""
from fastapi import Depends, HTTPException, Header
from typing import Optional
from jose import jwt, JWTError
from config import get_settings

settings = get_settings()


async def get_current_user_id(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """Authorization 헤더에서 JWT를 디코딩하여 user_id 반환.
    토큰이 없으면 None 반환 (비로그인 허용 엔드포인트용).
    """
    if not authorization:
        return None
    if not authorization.startswith("Bearer "):
        return None
    token = authorization[len("Bearer "):]
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload.get("sub")
    except JWTError:
        return None


async def require_auth(authorization: Optional[str] = Header(None)) -> str:
    """인증 필수 엔드포인트용. 토큰 없거나 유효하지 않으면 401."""
    user_id = await get_current_user_id(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_id
