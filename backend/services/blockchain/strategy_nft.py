"""
전략 cNFT 민팅/삭제/검증 — Solana State Compression + Helius DAS.

전략을 SHA256 해시하여 온체인에 기록하고,
Helius DAS API로 조회/검증합니다.

민팅 트랜잭션은 프론트엔드에서 사용자 지갑으로 서명.
백엔드는 트랜잭션 생성 + 검증만 담당.
"""

import hashlib
import json
import logging
from typing import Optional

try:
    SOLANA_AVAILABLE = True
except ImportError:
    SOLANA_AVAILABLE = False

from .solana_client import (
    get_rpc_client, SOLANA_RPC_URL, SOLANA_NETWORK,
    helius_get_asset, helius_get_asset_proof, helius_get_assets_by_owner,
)

logger = logging.getLogger(__name__)


def _hash_strategy(strategy_json: dict) -> str:
    """전략 JSON의 SHA256 해시 생성"""
    canonical = json.dumps(strategy_json, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


async def mint_strategy_nft(
    strategy_id: str,
    strategy_json: dict,
    owner_address: Optional[str] = None,
) -> dict:
    """
    전략 cNFT 민팅을 위한 트랜잭션 데이터 생성.

    실제 서명은 프론트엔드에서 사용자 Phantom 지갑으로 수행.
    백엔드는 메타데이터 준비 + 해시 생성만 담당.

    Returns:
        {
            "strategy_hash": "...",
            "metadata": {...},    # cNFT 메타데이터
            "network": "devnet",
            "rpc_url": "...",
            "ready_to_sign": true  # 프론트에서 서명 필요
        }
    """
    strategy_hash = _hash_strategy(strategy_json)
    strategy_name = strategy_json.get("name", f"Strategy {strategy_id[:8]}")

    logger.info(f"전략 cNFT 민팅 준비: {strategy_id}, hash={strategy_hash[:16]}...")

    # cNFT 메타데이터 (Metaplex 표준)
    metadata = {
        "name": f"TC: {strategy_name}",
        "symbol": "TCAI",
        "description": f"TradeCoach AI Strategy - {strategy_name}",
        "attributes": [
            {"trait_type": "strategy_hash", "value": strategy_hash},
            {"trait_type": "strategy_id", "value": strategy_id},
            {"trait_type": "leverage", "value": str(strategy_json.get("leverage", 1))},
            {"trait_type": "direction", "value": strategy_json.get("direction", "both")},
            {"trait_type": "immutable", "value": "true"},
        ],
        "properties": {
            "category": "trading_strategy",
            "creators": [],
        },
    }

    # 소유자 주소가 있으면 creator로 추가
    if owner_address:
        metadata["properties"]["creators"].append({
            "address": owner_address,
            "share": 100,
        })

    return {
        "strategy_hash": strategy_hash,
        "strategy_id": strategy_id,
        "metadata": metadata,
        "network": SOLANA_NETWORK,
        "rpc_url": SOLANA_RPC_URL,
        "ready_to_sign": True,
        "strategy_json_for_upload": strategy_json,
    }


async def confirm_mint(
    asset_id: str,
    tx_signature: str,
    strategy_id: str,
    strategy_hash: str,
) -> dict:
    """
    프론트엔드에서 민팅 완료 후 확인.
    Helius DAS로 온체인 에셋 확인.
    """
    asset = await helius_get_asset(asset_id)
    if asset:
        logger.info(f"cNFT 민팅 확인: asset_id={asset_id}")
        return {
            "confirmed": True,
            "asset_id": asset_id,
            "tx_signature": tx_signature,
            "onchain_data": asset,
        }
    return {
        "confirmed": False,
        "asset_id": asset_id,
        "error": "Asset not found on chain",
    }


async def burn_strategy_nft(asset_id: str, owner_signature: str) -> dict:
    """
    전략 cNFT 삭제 요청.
    실제 burn 트랜잭션은 프론트엔드에서 사용자 지갑으로 서명.
    """
    logger.info(f"전략 cNFT 삭제 요청: {asset_id}")
    return {
        "asset_id": asset_id,
        "action": "burn",
        "network": SOLANA_NETWORK,
        "ready_to_sign": True,
    }


async def verify_strategy(
    strategy_id: str,
    strategy_json: dict,
    asset_id: str,
) -> dict:
    """
    전략 무결성 검증 (DB 해시 vs 온체인 해시).
    Helius DAS API로 온체인 메타데이터 조회 후 비교.
    """
    db_hash = _hash_strategy(strategy_json)

    # Helius DAS로 온체인 에셋 조회
    onchain_hash = None
    onchain_data = None

    if asset_id and not asset_id.startswith("sim_"):
        asset = await helius_get_asset(asset_id)
        if asset:
            onchain_data = asset
            # 메타데이터에서 strategy_hash 추출
            attributes = asset.get("content", {}).get("metadata", {}).get("attributes", [])
            for attr in attributes:
                if attr.get("trait_type") == "strategy_hash":
                    onchain_hash = attr.get("value")
                    break

    # 온체인 해시가 없으면 DB 해시와 비교 불가
    if onchain_hash is None:
        return {
            "verified": False,
            "db_hash": db_hash,
            "onchain_hash": None,
            "match": False,
            "reason": "asset_not_found_or_no_hash",
            "network": SOLANA_NETWORK,
        }

    match = db_hash == onchain_hash
    return {
        "verified": match,
        "db_hash": db_hash,
        "onchain_hash": onchain_hash,
        "match": match,
        "network": SOLANA_NETWORK,
    }


async def get_strategies_by_owner(owner_address: str) -> list:
    """소유자의 모든 전략 cNFT 목록 조회 (Helius DAS)"""
    assets = await helius_get_assets_by_owner(owner_address)
    # TradeCoach 전략만 필터
    strategies = []
    for asset in assets:
        symbol = asset.get("content", {}).get("metadata", {}).get("symbol", "")
        if symbol == "TCAI":
            strategies.append(asset)
    return strategies
