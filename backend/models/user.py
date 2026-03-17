from __future__ import annotations

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class WalletAuthRequest(BaseModel):
    wallet_address: str


class WalletVerifyRequest(BaseModel):
    wallet_address: str
    signature: str
    nonce: str


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
    name: str
    email: str


class EmailAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    name: str
    email: str
