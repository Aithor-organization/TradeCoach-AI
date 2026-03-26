"""
매매 신호 압축 기록 — Solana State Compression.

모의투자 매매 신호를 SHA256 해시로 변환하여
로컬 DB에 저장하고, 배치로 온체인 Merkle Tree에 기록.

개별 신호의 온체인 기록은 비용 효율을 위해 배치 처리.
즉시 검증은 DB 해시로, 추후 온체인 proof로 검증 가능.
"""

import hashlib
import json
import logging
import time
from typing import Optional

from .solana_client import (
    SOLANA_NETWORK, helius_get_asset_proof, helius_get_assets_by_owner,
)

logger = logging.getLogger(__name__)

# 배치 기록용 버퍼 (메모리)
_signal_buffer: list[dict] = []
_BATCH_SIZE = 100  # 100개 신호마다 온체인 배치 기록


def _hash_signal(signal_data: dict) -> str:
    """신호 데이터의 SHA256 해시"""
    canonical = json.dumps(signal_data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


_VALID_SIGNAL_TYPES = {"long_entry", "short_entry", "close", "take_profit", "stop_loss"}
_SYMBOL_MAX_LEN = 20


async def record_signal(
    strategy_nft_id: str,
    signal_type: str,
    symbol: str,
    price: float,
    leverage: int,
    timestamp: int,
) -> dict:
    """
    매매 신호 기록 (로컬 해시 + 버퍼).

    1. 입력값 검증
    2. 신호 데이터 SHA256 해시 생성
    3. 로컬 버퍼에 추가
    4. 버퍼가 BATCH_SIZE에 도달하면 온체인 배치 기록 트리거

    Returns:
        {
            "signal_hash": "...",
            "leaf_index": N,         # 로컬 순서 번호
            "buffered": true,        # 아직 온체인 미기록
            "buffer_count": N,       # 현재 버퍼 크기
            "network": "devnet"
        }
    """
    # 입력 검증
    if price <= 0:
        raise ValueError(f"price must be > 0, got {price}")
    if not 1 <= leverage <= 125:
        raise ValueError(f"leverage must be 1-125, got {leverage}")
    if len(symbol) > _SYMBOL_MAX_LEN or not symbol.isalnum():
        raise ValueError(f"symbol must be alphanumeric, max {_SYMBOL_MAX_LEN} chars")
    if signal_type not in _VALID_SIGNAL_TYPES:
        raise ValueError(f"signal_type must be one of {_VALID_SIGNAL_TYPES}, got '{signal_type}'")

    if timestamp == 0:
        timestamp = int(time.time())

    signal_data = {
        "strategy_nft_id": strategy_nft_id,
        "signal_type": signal_type,
        "symbol": symbol,
        "price": price,
        "leverage": leverage,
        "timestamp": timestamp,
    }
    signal_hash = _hash_signal(signal_data)

    # 로컬 버퍼에 추가
    leaf_index = len(_signal_buffer)
    _signal_buffer.append({
        "hash": signal_hash,
        "data": signal_data,
        "leaf_index": leaf_index,
        "recorded_at": int(time.time()),
    })

    logger.info(
        f"신호 기록: {signal_type} {symbol} @{price}, "
        f"hash={signal_hash[:16]}..., buffer={len(_signal_buffer)}/{_BATCH_SIZE}"
    )

    # 배치 크기 도달 시 온체인 기록 트리거
    should_flush = len(_signal_buffer) >= _BATCH_SIZE
    if should_flush:
        logger.info(f"배치 크기 도달: {len(_signal_buffer)}개 신호 온체인 기록 대기")

    return {
        "signal_hash": signal_hash,
        "leaf_index": leaf_index,
        "buffered": True,
        "buffer_count": len(_signal_buffer),
        "batch_ready": should_flush,
        "network": SOLANA_NETWORK,
    }


async def flush_signals_to_chain(
    session_id: str = "",
    strategy_id: str = "",
) -> dict:
    """
    버퍼의 모든 신호를 Solana Devnet에 실제 기록.

    Tier 1: Memo Program으로 trade log 해시 기록 (즉시 사용)
    Tier 2: StrategyVault record_signal (프로그램 배포 후)

    Returns:
        {"flushed": N, "merkle_root": "...", "tx_signature": "...", "explorer_url": "..."}
    """
    if not _signal_buffer:
        return {"flushed": 0, "message": "buffer empty"}

    count = len(_signal_buffer)
    hashes = [s["hash"] for s in _signal_buffer]

    # Merkle root 계산
    combined = "".join(hashes)
    merkle_root = hashlib.sha256(combined.encode()).hexdigest()

    logger.info(f"온체인 배치 기록: {count}개 신호, root={merkle_root[:16]}...")

    # 실제 온체인 기록 (Tier 1: Memo Program)
    onchain_result = {}
    try:
        from .onchain_client import record_trades_onchain
        trades_data = [s["data"] for s in _signal_buffer]
        onchain_result = await record_trades_onchain(
            trades=trades_data,
            session_id=session_id,
            strategy_id=strategy_id,
        )
    except Exception as e:
        logger.warning(f"온체인 기록 실패 (비치명적): {e}")
        onchain_result = {"error": str(e), "tx_signature": None}

    # 버퍼 클리어
    _signal_buffer.clear()

    return {
        "flushed": count,
        "merkle_root": onchain_result.get("merkle_root", merkle_root),
        "hashes": hashes[:5],
        "network": SOLANA_NETWORK,
        "tx_signature": onchain_result.get("tx_signature"),
        "explorer_url": onchain_result.get("explorer_url"),
        "trade_hash": onchain_result.get("trade_hash"),
        "merkle_proofs": onchain_result.get("merkle_proofs"),
        "onchain_error": onchain_result.get("error"),
    }


async def get_signal_history(
    strategy_nft_id: str,
    limit: int = 100,
) -> list[dict]:
    """
    전략의 매매 신호 히스토리 조회.

    1. 로컬 버퍼에서 해당 전략의 신호 필터
    2. (향후) Helius DAS API로 온체인 기록 조회

    Returns:
        [{"signal_hash": "...", "signal_type": "...", "price": N, ...}]
    """
    # 로컬 버퍼에서 필터
    result = [
        {
            "signal_hash": s["hash"],
            "leaf_index": s["leaf_index"],
            **s["data"],
        }
        for s in _signal_buffer
        if s["data"].get("strategy_nft_id") == strategy_nft_id
    ]

    return result[:limit]


async def verify_signal(
    signal_hash: str,
    leaf_index: int,
    merkle_tree: Optional[str] = None,
) -> dict:
    """
    개별 신호의 무결성 검증.

    1. 로컬 버퍼에서 해시 확인
    2. (향후) 온체인 Merkle proof 검증

    Returns:
        {"verified": bool, "source": "local"|"onchain", "proof": [...]}
    """
    # 로컬 버퍼에서 확인
    for s in _signal_buffer:
        if s["hash"] == signal_hash:
            return {
                "verified": True,
                "source": "local_buffer",
                "leaf_index": s["leaf_index"],
                "network": SOLANA_NETWORK,
            }

    # 온체인 proof 조회 (asset_id가 있을 때)
    if merkle_tree:
        proof = await helius_get_asset_proof(signal_hash)
        if proof:
            return {
                "verified": True,
                "source": "onchain",
                "proof": proof,
                "network": SOLANA_NETWORK,
            }

    return {
        "verified": False,
        "source": "not_found",
        "network": SOLANA_NETWORK,
    }


def get_buffer_status() -> dict:
    """현재 신호 버퍼 상태"""
    return {
        "buffer_count": len(_signal_buffer),
        "batch_size": _BATCH_SIZE,
        "ready_to_flush": len(_signal_buffer) >= _BATCH_SIZE,
        "network": SOLANA_NETWORK,
    }


# ================================================================
# 배치 신호 기록 (StrategyVault batch_record 패턴, 최대 5건/TX)
# ================================================================

async def batch_record_signals(signals: list, max_batch: int = 5) -> dict:
    """
    최대 5건의 신호를 하나의 배치로 기록한다 (TX 비용 절감).
    
    Args:
        signals: [{strategy_nft_id, signal_type, symbol, price, leverage, timestamp}, ...]
        max_batch: 배치 최대 크기 (기본 5, StrategyVault 동일)
    
    Returns:
        {recorded: N, hashes: [...], batch_id: "..."}
    """
    import hashlib, json, time
    
    if not signals:
        return {"recorded": 0, "hashes": [], "batch_id": None}
    
    batch = signals[:max_batch]  # 최대 5건으로 제한
    hashes = []
    
    for sig in batch:
        # 개별 신호 해시
        data = {
            "strategy_nft_id": sig.get("strategy_nft_id", ""),
            "signal_type": sig.get("signal_type", ""),
            "symbol": sig.get("symbol", ""),
            "price": sig.get("price", 0),
            "leverage": sig.get("leverage", 1),
            "timestamp": sig.get("timestamp", 0) or int(time.time()),
        }
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
        h = hashlib.sha256(canonical.encode()).hexdigest()
        hashes.append(h)
        _signal_buffer.append({
            "hash": h,
            "data": data,
            "leaf_index": len(_signal_buffer),
            "recorded_at": int(time.time()),
        })
    
    # 배치 해시 (모든 개별 해시의 해시)
    batch_hash = hashlib.sha256("".join(hashes).encode()).hexdigest()
    
    return {
        "recorded": len(batch),
        "skipped": max(0, len(signals) - max_batch),
        "hashes": hashes,
        "batch_hash": batch_hash,
        "batch_id": batch_hash[:16],
        "network": SOLANA_NETWORK,
    }
