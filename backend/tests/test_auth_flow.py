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


# ── Password Reset 플로우 (Wallet 서명 기반) ────────────────

# 유효한 base58 더미 Solana 주소 (실제 키 쌍은 아님 — 서명 검증에서 실패할 뿐 형식 검증은 통과)
_DUMMY_WALLET = "TestWaketABCDEFGHJKMN2345678PQRSTUVWXYZabc"


@pytest.mark.asyncio
async def test_reset_wallet_nonce_issues_token_without_user_check(client: AsyncClient):
    """reset-wallet-nonce는 지갑 등록 여부와 무관하게 nonce를 발급 (enumeration 방지)."""
    res = await client.post(
        "/auth/password/reset-wallet-nonce",
        json={"wallet_address": _DUMMY_WALLET},
    )
    assert res.status_code == 200
    body = res.json()
    assert "nonce" in body
    assert isinstance(body["nonce"], str) and len(body["nonce"]) > 0


@pytest.mark.asyncio
async def test_reset_wallet_nonce_rejects_invalid_address(client: AsyncClient):
    """Solana 주소 형식이 아닌 값은 422."""
    res = await client.post(
        "/auth/password/reset-wallet-nonce",
        json={"wallet_address": "not-a-wallet"},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_reset_wallet_confirm_rejects_unknown_nonce(client: AsyncClient):
    """발급된 적 없는 nonce는 400."""
    res = await client.post(
        "/auth/password/reset-wallet-confirm",
        json={
            "wallet_address": _DUMMY_WALLET,
            "nonce": "a" * 64,
            "signature": "1" * 88,  # base58 더미
            "new_password": "newsecret123",
        },
    )
    assert res.status_code == 400
    assert "nonce" in res.json().get("detail", "").lower() or "nonce" in res.json().get("detail", "")


@pytest.mark.asyncio
async def test_reset_wallet_confirm_rejects_short_password(client: AsyncClient):
    """6자 미만 새 비밀번호는 422."""
    res = await client.post(
        "/auth/password/reset-wallet-confirm",
        json={
            "wallet_address": _DUMMY_WALLET,
            "nonce": "a" * 64,
            "signature": "1" * 88,
            "new_password": "abc",
        },
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_reset_wallet_confirm_rejects_bad_signature(client: AsyncClient):
    """nonce 발급 후 잘못된 서명으로 confirm 시 401."""
    # Step 1: nonce 발급
    nonce_res = await client.post(
        "/auth/password/reset-wallet-nonce",
        json={"wallet_address": _DUMMY_WALLET},
    )
    assert nonce_res.status_code == 200
    nonce = nonce_res.json()["nonce"]

    # Step 2: 가짜 서명으로 confirm — 401 expected
    res = await client.post(
        "/auth/password/reset-wallet-confirm",
        json={
            "wallet_address": _DUMMY_WALLET,
            "nonce": nonce,
            "signature": "1" * 88,  # base58 형식이나 실제 서명 아님
            "new_password": "newsecret123",
        },
    )
    assert res.status_code == 401
    assert "서명" in res.json().get("detail", "")


# ── Wallet auth 기본 검증 ─────────────────────────────────


@pytest.mark.asyncio
async def test_wallet_nonce_rejects_invalid_address(client: AsyncClient):
    """Solana 주소 형식 아닌 값은 422"""
    res = await client.post(
        "/auth/wallet",
        json={"wallet_address": "not-a-solana-address"},
    )
    assert res.status_code == 422
