from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
import re


class WalletAuthRequest(BaseModel):
    wallet_address: str = Field(..., min_length=32, max_length=44)

    @field_validator("wallet_address")
    @classmethod
    def validate_wallet(cls, v: str) -> str:
        # Solana 주소는 base58 문자 (32-44자)
        if not re.match(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$", v):
            raise ValueError("유효하지 않은 Solana 지갑 주소 형식")
        return v


class WalletVerifyRequest(BaseModel):
    wallet_address: str = Field(..., min_length=32, max_length=44)
    signature: str = Field(..., min_length=1, max_length=200)
    nonce: str = Field(..., min_length=1, max_length=128)

    @field_validator("wallet_address")
    @classmethod
    def validate_wallet(cls, v: str) -> str:
        if not re.match(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$", v):
            raise ValueError("유효하지 않은 Solana 지갑 주소 형식")
        return v


class UserResponse(BaseModel):
    id: str
    wallet_address: str
    display_name: Optional[str]
    tier: str
    created_at: datetime


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class NonceResponse(BaseModel):
    nonce: str


class EmailLoginRequest(BaseModel):
    email: str = Field(..., max_length=254)
    password: str = Field(..., min_length=6, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("유효하지 않은 이메일 형식")
        return v.lower()


class EmailRegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., max_length=254)
    password: str = Field(..., min_length=6, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        # 기본 이메일 형식 검증
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("유효하지 않은 이메일 형식")
        return v.lower()


class EmailAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    name: str
    email: str
    email_verified: bool = False


class PasswordResetRequest(BaseModel):
    """비밀번호 재설정 링크 요청 (이메일 입력)"""
    email: str = Field(..., max_length=254)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("유효하지 않은 이메일 형식")
        return v.lower()


class PasswordResetConfirm(BaseModel):
    """재설정 토큰으로 새 비밀번호 설정"""
    token: str = Field(..., min_length=32, max_length=128)
    new_password: str = Field(..., min_length=6, max_length=128)


class PasswordResetResponse(BaseModel):
    """재설정 링크 요청 응답.

    🔴 SECURITY: 이메일 존재 여부 노출 방지를 위해 모든 경우 동일한 응답을 반환한다.
    실제 발송 여부는 서버 내부 로그로만 확인 가능.
    """
    message: str = "이메일이 등록되어 있다면 재설정 링크를 발송했습니다. 메일함을 확인해주세요."
