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


class WalletResetNonceRequest(BaseModel):
    """비밀번호 재설정용 nonce 요청 (지갑 주소만 필요).

    이메일 전송 인프라 없이 Phantom 지갑 서명으로 본인을 증명하는 방식.
    """
    wallet_address: str = Field(..., min_length=32, max_length=44)

    @field_validator("wallet_address")
    @classmethod
    def validate_wallet(cls, v: str) -> str:
        if not re.match(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$", v):
            raise ValueError("유효하지 않은 Solana 지갑 주소 형식")
        return v


class WalletResetConfirm(BaseModel):
    """Wallet 서명으로 본인 증명 + 새 비밀번호 설정."""
    wallet_address: str = Field(..., min_length=32, max_length=44)
    nonce: str = Field(..., min_length=1, max_length=128)
    signature: str = Field(..., min_length=1, max_length=200)
    new_password: str = Field(..., min_length=6, max_length=128)

    @field_validator("wallet_address")
    @classmethod
    def validate_wallet(cls, v: str) -> str:
        if not re.match(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$", v):
            raise ValueError("유효하지 않은 Solana 지갑 주소 형식")
        return v


class WalletResetNonceResponse(BaseModel):
    """재설정 nonce 응답.

    🔴 SECURITY: 지갑 등록 여부와 무관하게 항상 nonce를 발급한다.
    - 미등록 지갑: nonce는 발급되지만 confirm 단계에서 404 반환
    - 공격자가 지갑 주소로 가입 여부를 enumerate 하려면 서명까지 위조해야 하므로 사실상 불가
    """
    nonce: str
    message: str = "이 nonce를 연결된 Phantom 지갑으로 서명한 뒤 reset-wallet-confirm 엔드포인트로 전송하세요."
