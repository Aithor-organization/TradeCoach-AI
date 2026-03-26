"""
Solana 클라이언트 — RPC 연결 + Helius DAS API 래퍼.

devnet/mainnet 전환: SOLANA_RPC_URL 환경변수로 제어.
"""

import os
import logging
import httpx
from typing import Optional
try:
    from solana.rpc.async_api import AsyncClient
    from solders.pubkey import Pubkey  # type: ignore
    SOLANA_AVAILABLE = True
except ImportError:
    SOLANA_AVAILABLE = False
    AsyncClient = None
    Pubkey = None

logger = logging.getLogger(__name__)

# 환경변수에서 RPC URL 로드
SOLANA_RPC_URL = os.getenv(
    "SOLANA_RPC_URL",
    "https://api.devnet.solana.com",
)
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")
SOLANA_NETWORK = os.getenv("SOLANA_NETWORK", "devnet")


def get_rpc_client() -> AsyncClient:
    """Solana RPC 비동기 클라이언트 생성"""
    return AsyncClient(SOLANA_RPC_URL)


_HELIUS_TIMEOUT = 10.0  # 모든 Helius 호출에 10초 타임아웃


def get_helius_url() -> str:
    """Helius DAS API URL (API 키는 Authorization 헤더로 전송 — URL에 노출하지 않음)"""
    return "https://api.helius.xyz/v0"


def _helius_headers() -> dict:
    """Helius API 요청 헤더 (Authorization 헤더에 API 키 포함)"""
    headers = {"Content-Type": "application/json"}
    if HELIUS_API_KEY:
        headers["Authorization"] = f"Bearer {HELIUS_API_KEY}"
    return headers


async def get_balance(address: str) -> float:
    """지갑 SOL 잔고 조회 (lamports → SOL)"""
    client = get_rpc_client()
    try:
        resp = await client.get_balance(Pubkey.from_string(address))
        lamports = resp.value
        return lamports / 1_000_000_000  # 1 SOL = 10^9 lamports
    finally:
        await client.close()


async def request_airdrop(address: str, sol_amount: float = 2.0) -> Optional[str]:
    """devnet 에어드랍 요청 (테스트용)"""
    if SOLANA_NETWORK != "devnet":
        logger.warning("에어드랍은 devnet에서만 가능합니다")
        return None

    client = get_rpc_client()
    try:
        lamports = int(sol_amount * 1_000_000_000)
        resp = await client.request_airdrop(
            Pubkey.from_string(address), lamports,
        )
        sig = str(resp.value)
        logger.info(f"에어드랍 성공: {sol_amount} SOL → {address}, tx={sig}")
        return sig
    except Exception as e:
        logger.error(f"에어드랍 실패: {e}")
        return None
    finally:
        await client.close()


async def helius_get_asset(asset_id: str) -> Optional[dict]:
    """Helius DAS API로 cNFT 에셋 조회"""
    url = get_helius_url()
    async with httpx.AsyncClient(timeout=_HELIUS_TIMEOUT) as client:
        resp = await client.post(
            url,
            headers=_helius_headers(),
            json={
                "jsonrpc": "2.0",
                "id": "tradecoach",
                "method": "getAsset",
                "params": {"id": asset_id},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            logger.error(f"Helius getAsset 오류: {data['error']}")
            return None
        return data.get("result")


async def helius_get_asset_proof(asset_id: str) -> Optional[dict]:
    """Helius DAS API로 Merkle proof 조회"""
    url = get_helius_url()
    async with httpx.AsyncClient(timeout=_HELIUS_TIMEOUT) as client:
        resp = await client.post(
            url,
            headers=_helius_headers(),
            json={
                "jsonrpc": "2.0",
                "id": "tradecoach",
                "method": "getAssetProof",
                "params": {"id": asset_id},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            logger.error(f"Helius getAssetProof 오류: {data['error']}")
            return None
        return data.get("result")


async def helius_get_assets_by_owner(owner: str, limit: int = 100) -> list:
    """Helius DAS API로 소유자의 모든 에셋 조회"""
    url = get_helius_url()
    async with httpx.AsyncClient(timeout=_HELIUS_TIMEOUT) as client:
        resp = await client.post(
            url,
            headers=_helius_headers(),
            json={
                "jsonrpc": "2.0",
                "id": "tradecoach",
                "method": "getAssetsByOwner",
                "params": {
                    "ownerAddress": owner,
                    "page": 1,
                    "limit": limit,
                },
            },
        )
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            logger.error(f"Helius getAssetsByOwner 오류: {data['error']}")
            return []
        result = data.get("result", {})
        return result.get("items", [])
