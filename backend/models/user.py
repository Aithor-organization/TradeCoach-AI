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


class EmailRegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., max_length=254)

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
