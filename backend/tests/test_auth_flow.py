"""
Auth 플로우 테스트 — signup / login / password reset 핵심 케이스.

외부 서비스(Supabase)는 테스트에서 도달 불가능할 수 있으므로,
- Supabase 미구성 상태에서 기대되는 응답(503, 400 등)
- 입력 검증(pydantic validator)
- Password reset token lifecycle (인메모리 저장소)
위주로 검증한다. 실제 DB 통합 테스트는 staging 환경에서 별도로 수행한다.
"""

import pytest
from httpx import AsyncClient


# ── 입력 검증 ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_rejects_invalid_email(client: AsyncClient):
    """잘못된 이메일 형식은 422 (Pydantic validator)"""
    res = await client.post(
        "/auth/register",
        json={"name": "Tester", "email": "not-an-email", "password": "secret123"},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_register_rejects_short_password(client: AsyncClient):
    """6자 미만 비밀번호는 422"""
    res = await client.post(
        "/auth/register",
        json={"name": "Tester", "email": "test@example.com", "password": "abc"},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_login_rejects_missing_fields(client: AsyncClient):
    """이메일 또는 비밀번호 누락은 422"""
    res = await client.post("/auth/login", json={"email": "test@example.com"})
    assert res.status_code == 422


# ── User Enumeration 방어 (login) ──────────────────────────


@pytest.mark.asyncio
async def test_login_returns_same_error_for_missing_email(client: AsyncClient):
    """미가입 이메일도 비가입 노출 없이 401만 반환"""
    res = await client.post(
        "/auth/login",
        json={"email": "nonexistent@example.com", "password": "whatever123"},
    )
    # Supabase 비가용 시 503, 가용하나 없으면 401 — 둘 다 "이메일 존재 여부" 미노출
    assert res.status_code in (401, 503)
    if res.status_code == 401:
        detail = res.json().get("detail", "")
        # "등록되지 않은 이메일" 같은 enumeration 문구가 없어야 함
        assert "등록되지" not in detail
        assert "일치하지 않습니다" in detail or "올바르지" in detail or "일치" in detail


# ── Password Reset 플로우 (인메모리 토큰) ──────────────────


@pytest.mark.asyncio
async def test_password_reset_request_always_returns_generic(client: AsyncClient):
    """reset-request는 이메일 존재 여부와 무관하게 항상 200 + 일반 메시지."""
    res = await client.post(
        "/auth/password/reset-request",
        json={"email": "nobody@example.com"},
    )
    assert res.status_code == 200
    msg = res.json().get("message", "")
    # 존재/미존재 구분 가능한 문구는 없어야 함
    assert "등록되지" not in msg
    assert "발송" in msg or "이메일" in msg


@pytest.mark.asyncio
async def test_password_reset_confirm_rejects_invalid_token(client: AsyncClient):
    """존재하지 않는 토큰은 400"""
    res = await client.post(
        "/auth/password/reset-confirm",
        json={"token": "a" * 48, "new_password": "newsecret123"},
    )
    assert res.status_code == 400
    assert "토큰" in res.json().get("detail", "")


@pytest.mark.asyncio
async def test_password_reset_confirm_rejects_short_password(client: AsyncClient):
    """6자 미만 새 비밀번호는 422"""
    res = await client.post(
        "/auth/password/reset-confirm",
        json={"token": "a" * 48, "new_password": "abc"},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_password_reset_confirm_rejects_short_token(client: AsyncClient):
    """32자 미만 토큰은 422"""
    res = await client.post(
        "/auth/password/reset-confirm",
        json={"token": "short", "new_password": "newsecret123"},
    )
    assert res.status_code == 422


# ── Wallet auth 기본 검증 ─────────────────────────────────


@pytest.mark.asyncio
async def test_wallet_nonce_rejects_invalid_address(client: AsyncClient):
    """Solana 주소 형식 아닌 값은 422"""
    res = await client.post(
        "/auth/wallet",
        json={"wallet_address": "not-a-solana-address"},
    )
    assert res.status_code == 422
