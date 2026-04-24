"""
Marketplace smoke 테스트 — 입력 검증과 404 경로 중심.

Supabase 미연결 상태에서는 ListingService.get_listing() → None이므로
모든 구매/렌탈 플로우는 결제 서비스 로직에 도달하지 않고 404로 종결된다.
실제 결제 경로(95:5 분배, license 생성, idempotency 캐시)는 통합 환경에서 별도 검증.
"""

import pytest
from httpx import AsyncClient


# ── 목록/조회 ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_strategies_returns_list(client: AsyncClient):
    """GET /marketplace/strategies — DB 미연결이어도 빈 리스트 200."""
    res = await client.get("/marketplace/strategies")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


@pytest.mark.asyncio
async def test_list_strategies_rejects_invalid_limit(client: AsyncClient):
    """limit 상한 초과는 422 (Query constraint)."""
    res = await client.get("/marketplace/strategies?limit=9999")
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_get_unknown_strategy_returns_404(client: AsyncClient):
    """미존재 listing 조회는 404."""
    res = await client.get("/marketplace/strategies/nonexistent-id-12345")
    assert res.status_code == 404


# ── 구매 / 렌탈 입력 검증 ──────────────────────────────────


@pytest.mark.asyncio
async def test_purchase_missing_body_returns_422(client: AsyncClient):
    """buyer_wallet 누락은 422."""
    res = await client.post("/marketplace/strategies/any-id/purchase", json={})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_purchase_nonexistent_listing_returns_404(client: AsyncClient):
    """존재하지 않는 listing에 대한 purchase는 404 (결제 로직 미도달)."""
    res = await client.post(
        "/marketplace/strategies/nonexistent-id/purchase",
        json={"buyer_wallet": "ABC" * 11, "tx_signature": "dummy"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_purchase_accepts_idempotency_key_header(client: AsyncClient):
    """Idempotency-Key 헤더가 있어도 listing 미존재 시 404 (헤더 파싱 실패로 422 아님)."""
    res = await client.post(
        "/marketplace/strategies/nonexistent-id/purchase",
        json={"buyer_wallet": "ABC" * 11, "tx_signature": "dummy"},
        headers={"Idempotency-Key": "test-idempotency-key-123"},
    )
    # 헤더 자체가 수용되어야 하므로 422가 아닌 404를 기대
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_rent_rejects_zero_days(client: AsyncClient):
    """days=0은 422 (ge=1)."""
    res = await client.post(
        "/marketplace/strategies/any-id/rent",
        json={"renter_wallet": "ABC" * 11, "days": 0},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_rent_rejects_excess_days(client: AsyncClient):
    """days=366은 422 (le=365)."""
    res = await client.post(
        "/marketplace/strategies/any-id/rent",
        json={"renter_wallet": "ABC" * 11, "days": 366},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_rent_nonexistent_listing_returns_404(client: AsyncClient):
    """미존재 listing 렌탈은 404."""
    res = await client.post(
        "/marketplace/strategies/nonexistent-id/rent",
        json={"renter_wallet": "ABC" * 11, "days": 7},
        headers={"Idempotency-Key": "rent-key-456"},
    )
    assert res.status_code == 404


# ── 라이선스 / 랭킹 / 수익 ─────────────────────────────────


@pytest.mark.asyncio
async def test_my_licenses_rejects_short_wallet(client: AsyncClient):
    """wallet 파라미터 min_length=32 미만은 422."""
    res = await client.get("/marketplace/licenses?wallet=short")
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_my_licenses_empty_with_no_db(client: AsyncClient):
    """유효한 wallet + DB 미연결 시 빈 리스트 200."""
    res = await client.get(
        "/marketplace/licenses?wallet=" + "A" * 32
    )
    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.asyncio
async def test_rankings_default_returns_list(client: AsyncClient):
    """기본 ranking 조회는 항상 200 (DB 없을 때 빈 결과)."""
    res = await client.get("/marketplace/rankings")
    assert res.status_code == 200
