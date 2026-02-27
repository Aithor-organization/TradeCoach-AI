"""
TradeCoach-AI FastAPI 기본 테스트 모음

외부 서비스(Jupiter API, Supabase)는 테스트 환경에서 도달 불가능할 수 있으므로
응답 구조와 상태 코드를 중심으로 검증한다.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """GET /health - 서버 정상 동작 확인"""
    response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body


@pytest.mark.asyncio
async def test_market_prices(client: AsyncClient):
    """GET /market/prices - 주요 토큰 일괄 가격 조회

    Jupiter API 미도달 시 가격이 null일 수 있으나 응답 구조는 유효해야 한다.
    """
    response = await client.get("/market/prices")

    assert response.status_code == 200
    body = response.json()
    assert "prices" in body
    assert isinstance(body["prices"], dict)


@pytest.mark.asyncio
async def test_market_price_single(client: AsyncClient):
    """GET /market/price/SOL - SOL 단일 가격 조회

    Jupiter API 미도달 시 404 (price=None), 성공 시 200+symbol+price 반환.
    """
    response = await client.get("/market/price/SOL")

    # Jupiter API 도달 가능 시 200, 미도달 시 404
    assert response.status_code in (200, 404)
    body = response.json()
    if response.status_code == 200:
        assert body["symbol"] == "SOL"
        assert "price" in body
    else:
        assert "detail" in body


@pytest.mark.asyncio
async def test_market_price_unknown_token(client: AsyncClient):
    """GET /market/price/FAKECOIN - 알 수 없는 토큰 조회 시 404 반환"""
    response = await client.get("/market/price/FAKECOIN")

    assert response.status_code == 404
    body = response.json()
    assert "detail" in body


@pytest.mark.asyncio
async def test_wallet_auth_nonce(client: AsyncClient):
    """POST /auth/wallet - 지갑 주소로 nonce 발급

    Supabase 미연결 시 인메모리 폴백으로 동작하므로 외부 의존성 없이 200 응답이어야 한다.
    """
    payload = {"wallet_address": "TestWallet1111111111111111111111111111111111"}
    response = await client.post("/auth/wallet", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert "nonce" in body
    assert isinstance(body["nonce"], str)
    assert len(body["nonce"]) > 0
