"""
Phase 5: 블록체인 통합 API — Solana cNFT + 매매 신호 기록.
"""

import logging
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional
from dependencies import get_current_user_id
from routers.auth import limiter

router = APIRouter()
logger = logging.getLogger(__name__)


class MintRequest(BaseModel):
    strategy_id: str
    parsed_strategy: dict


class BurnRequest(BaseModel):
    asset_id: str
    owner_signature: str = ""


class SignalRecordRequest(BaseModel):
    strategy_nft_id: str
    signal_type: str
    symbol: str
    price: float
    leverage: int = 10
    timestamp: int = 0


@router.post("/strategy/mint")
async def mint_strategy(
    body: MintRequest,
    user_id: str | None = Depends(get_current_user_id),
):
    """전략을 cNFT로 민팅"""
    from services.blockchain import mint_strategy_nft

    try:
        result = await mint_strategy_nft(
            strategy_id=body.strategy_id,
            strategy_json=body.parsed_strategy,
        )
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"민팅 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"민팅 실패: {str(e)}")


class ConfirmMintRequest(BaseModel):
    tx_signature: str
    strategy_hash: str
    network: str = "devnet"


@router.post("/strategy/{strategy_id}/confirm-mint")
async def confirm_mint(
    strategy_id: str,
    body: ConfirmMintRequest,
    user_id: str | None = Depends(get_current_user_id),
):
    """민팅 트랜잭션 확인 후 전략 status를 verified로 업데이트"""
    from services.supabase_client import update_strategy_by_id

    try:
        updated = await update_strategy_by_id(strategy_id, {
            "status": "verified",
            "mint_tx": body.tx_signature,
            "mint_hash": body.strategy_hash,
            "mint_network": body.network,
        })
        if not updated:
            raise HTTPException(status_code=404, detail="Strategy not found")
        return {"strategy_id": strategy_id, "status": "verified", "tx_signature": body.tx_signature}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"민팅 확인 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="민팅 상태 업데이트 실패")


@router.post("/strategy/{strategy_id}/burn")
async def burn_strategy(
    strategy_id: str,
    body: BurnRequest,
    user_id: str | None = Depends(get_current_user_id),
):
    """전략 cNFT 삭제 (소유자만)"""
    from services.blockchain import burn_strategy_nft

    try:
        result = await burn_strategy_nft(body.asset_id, body.owner_signature)
        return result
    except Exception as e:
        logger.error(f"삭제 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="삭제 실패")


@router.get("/strategy/{strategy_id}/verify")
async def verify_strategy_endpoint(
    strategy_id: str,
    user_id: str | None = Depends(get_current_user_id),
):
    """전략 무결성 검증 (DB vs 온체인 해시)"""
    from services.blockchain import verify_strategy
    from services.supabase_client import get_strategy_by_id

    try:
        strategy = await get_strategy_by_id(strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        result = await verify_strategy(
            strategy_id=strategy_id,
            strategy_json=strategy.get("parsed_strategy", {}),
            asset_id=strategy.get("asset_id", ""),
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"검증 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="검증 실패")


@router.post("/signal")
async def record_signal_endpoint(body: SignalRecordRequest):
    """매매 신호 압축 기록 (자동 호출)"""
    from services.blockchain import record_signal

    try:
        result = await record_signal(
            strategy_nft_id=body.strategy_nft_id,
            signal_type=body.signal_type,
            symbol=body.symbol,
            price=body.price,
            leverage=body.leverage,
            timestamp=body.timestamp,
        )
        return result
    except Exception as e:
        logger.error(f"신호 기록 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="신호 기록 실패")


@router.get("/signal/history/{strategy_id}")
async def get_signal_history_endpoint(strategy_id: str, limit: int = 100):
    """신호 히스토리 조회"""
    from services.blockchain import get_signal_history

    return await get_signal_history(strategy_id, limit)


@router.get("/signal/{signal_id}/proof")
async def verify_signal_endpoint(signal_id: str, leaf_index: int = 0):
    """개별 신호 Merkle proof 검증"""
    from services.blockchain import verify_signal

    return await verify_signal(signal_id, leaf_index)


# === Solana 유틸리티 (devnet) ===

@router.get("/balance/{address}")
async def get_wallet_balance(address: str):
    """지갑 SOL 잔고 조회"""
    from services.blockchain import get_balance

    try:
        balance = await get_balance(address)
        return {"address": address, "balance_sol": balance}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/airdrop/{address}")
async def request_devnet_airdrop(address: str, amount: float = 2.0):
    """devnet SOL 에어드랍 요청 (테스트용)"""
    from services.blockchain import request_airdrop

    sig = await request_airdrop(address, amount)
    if sig:
        return {"address": address, "amount_sol": amount, "tx_signature": sig}
    raise HTTPException(status_code=400, detail="에어드랍 실패 (devnet만 가능)")


@router.get("/signal/buffer/status")
async def signal_buffer_status():
    """신호 버퍼 상태 조회"""
    from services.blockchain import get_buffer_status

    return get_buffer_status()


@router.post("/signal/flush")
async def flush_signal_buffer(session_id: str = "", strategy_id: str = ""):
    """신호 버퍼를 온체인에 배치 기록"""
    from services.blockchain import flush_signals_to_chain

    return await flush_signals_to_chain(session_id=session_id, strategy_id=strategy_id)


@router.get("/server/status")
async def server_blockchain_status():
    """서버 블록체인 연결 상태 조회"""
    from services.blockchain.onchain_client import get_server_balance, load_server_keypair

    keypair = load_server_keypair()
    if not keypair:
        return {"connected": False, "error": "서버 키페어 없음"}

    balance = await get_server_balance()
    return {
        "connected": True,
        "server_pubkey": str(keypair.pubkey()),
        "balance_sol": balance,
        "network": "devnet",
    }


class StrategyRegisterRequest(BaseModel):
    strategy_id: str
    strategy_name: str
    strategy_data: dict


class InitializePlatformRequest(BaseModel):
    fee_bps: int = 500  # 5% 기본값


@router.post("/platform/initialize")
async def initialize_platform_endpoint(
    body: InitializePlatformRequest,
    user_id: str | None = Depends(get_current_user_id),
):
    """Platform PDA 초기화 (1회성, Anchor instruction)"""
    from services.blockchain.anchor_client import initialize_platform

    result = await initialize_platform(fee_bps=body.fee_bps)
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@router.get("/platform/info")
async def get_platform_info_endpoint():
    """Platform PDA 계정 정보 조회"""
    from services.blockchain.anchor_client import get_platform_info
    from config import get_settings

    settings = get_settings()
    info = await get_platform_info(settings.program_strategy_registry)
    if not info:
        return {"initialized": False, "message": "Platform 미초기화"}
    return {"initialized": True, **info}


@router.post("/strategy/register-onchain")
async def register_strategy_onchain_endpoint(
    body: StrategyRegisterRequest,
    user_id: str | None = Depends(get_current_user_id),
):
    """전략을 온체인에 등록 (Anchor 우선, Memo 폴백)"""
    from services.blockchain.strategy_registry_client import register_strategy_onchain

    result = await register_strategy_onchain(
        strategy_id=body.strategy_id,
        strategy_name=body.strategy_name,
        strategy_data=body.strategy_data,
    )
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@router.get("/strategy/{strategy_id}/performance")
async def get_strategy_performance(strategy_id: str):
    """전략 성과 조회 — DB 우선, 인메모리 폴백"""
    # 1. DB에서 조회 (영속, 서버 재시작 무관)
    try:
        from services.supabase_client import get_strategy_performance_db
        db_perf = await get_strategy_performance_db(strategy_id)
        if db_perf and db_perf.get("total_trades", 0) > 0:
            db_perf["source"] = "database"
            return db_perf
    except Exception:
        pass

    # 2. 인메모리 폴백
    from services.blockchain.strategy_registry_client import get_performance
    perf = get_performance(strategy_id)
    if not perf:
        return {"strategy_id": strategy_id, "verified": False, "total_trades": 0, "message": "성과 데이터 없음"}
    perf["source"] = "memory"
    return perf


@router.get("/strategy/{strategy_id}/trade-history")
async def get_strategy_trade_history(strategy_id: str, limit: int = 50):
    """전략 거래 히스토리 — DB 우선, 인메모리 폴백"""
    # 1. DB에서 조회
    try:
        from services.supabase_client import get_trade_records_db
        db_trades = await get_trade_records_db(strategy_id, limit)
        if db_trades:
            return {"strategy_id": strategy_id, "trades": db_trades, "source": "database"}
    except Exception:
        pass

    # 2. 인메모리 폴백
    from services.blockchain.strategy_registry_client import get_trade_history
    return {"strategy_id": strategy_id, "trades": get_trade_history(strategy_id, limit), "source": "memory"}


class MerkleVerifyRequest(BaseModel):
    signal_data: dict
    proof: list[str]
    root: str
    leaf_index: int


@router.post("/merkle/verify")
async def verify_merkle_proof_endpoint(body: MerkleVerifyRequest):
    """개별 신호의 Merkle proof 검증 (온체인 root 대비)"""
    from services.blockchain.merkle_tree import compute_leaf, verify_merkle_proof

    leaf = compute_leaf(body.signal_data)
    proof_bytes = [bytes.fromhex(p) for p in body.proof]
    root_bytes = bytes.fromhex(body.root)

    verified = verify_merkle_proof(leaf, proof_bytes, root_bytes, body.leaf_index)

    return {
        "verified": verified,
        "leaf_hash": leaf.hex(),
        "root": body.root,
        "leaf_index": body.leaf_index,
    }


@router.get("/tx/{tx_signature}")
async def verify_transaction(tx_signature: str):
    """TX signature로 온체인 기록 검증"""
    from services.blockchain.solana_client import get_rpc_client
    import os

    try:
        rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com")
        from solana.rpc.async_api import AsyncClient
        async with AsyncClient(rpc_url) as client:
            from solders.signature import Signature  # type: ignore
            resp = await client.get_transaction(
                Signature.from_string(tx_signature),
                max_supported_transaction_version=0,
            )
            if resp.value:
                return {
                    "verified": True,
                    "tx_signature": tx_signature,
                    "slot": resp.value.slot,
                    "block_time": resp.value.block_time,
                    "explorer_url": f"https://explorer.solana.com/tx/{tx_signature}?cluster=devnet",
                }
            return {"verified": False, "tx_signature": tx_signature}
    except Exception as e:
        return {"verified": False, "error": str(e)}


@router.get("/strategy/{strategy_id}/tx-history")
async def get_strategy_tx_history(strategy_id: str, limit: int = 20):
    """
    전략의 TX 히스토리 — 하이브리드 조회.

    1단계: Supabase DB에서 즉시 조회 (~50ms)
    2단계: DB 결과가 없으면 Solana RPC 폴백 (~200ms)
    """
    # 1단계: DB 캐시에서 조회 (즉시)
    try:
        from services.supabase_client import get_trade_tx_records
        db_records = await get_trade_tx_records(strategy_id, limit)
        if db_records:
            return {
                "strategy_id": strategy_id,
                "transactions": [
                    {
                        "tx_signature": r.get("tx_signature", ""),
                        "block_time": None,
                        "slot": 0,
                        "explorer_url": r.get("explorer_url", ""),
                        "merkle_root": r.get("merkle_root", ""),
                        "trades_count": r.get("trades_count", 0),
                        "created_at": r.get("created_at", ""),
                    }
                    for r in db_records
                ],
                "count": len(db_records),
                "source": "database",
            }
    except Exception as e:
        logger.warning(f"DB TX 조회 실패, 온체인 폴백: {e}")

    # 2단계: Solana RPC 폴백
    import os
    from services.blockchain.onchain_client import load_server_keypair, SOLANA_AVAILABLE

    if not SOLANA_AVAILABLE:
        return {"strategy_id": strategy_id, "transactions": []}

    keypair = load_server_keypair()
    if not keypair:
        return {"strategy_id": strategy_id, "transactions": []}

    rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com")
    network = os.getenv("SOLANA_NETWORK", "devnet")

    try:
        from solana.rpc.async_api import AsyncClient

        async with AsyncClient(rpc_url) as client:
            sigs_resp = await client.get_signatures_for_address(keypair.pubkey(), limit=100)
            if not sigs_resp.value:
                return {"strategy_id": strategy_id, "transactions": []}

            matched_txs = []
            strategy_prefix = strategy_id[:16]
            cluster = f"?cluster={network}" if network != "mainnet-beta" else ""

            for sig_info in sigs_resp.value:
                if len(matched_txs) >= limit:
                    break
                memo_str = str(sig_info.memo) if sig_info.memo else ""
                if strategy_prefix in memo_str:
                    matched_txs.append({
                        "tx_signature": str(sig_info.signature),
                        "block_time": sig_info.block_time,
                        "slot": sig_info.slot,
                        "explorer_url": f"https://explorer.solana.com/tx/{sig_info.signature}{cluster}",
                    })

            return {
                "strategy_id": strategy_id,
                "transactions": matched_txs,
                "count": len(matched_txs),
                "source": "solana_onchain",
            }

    except Exception as e:
        logger.error(f"온체인 TX 히스토리 조회 실패: {e}")
        return {"strategy_id": strategy_id, "transactions": [], "error": str(e)}


# === Phase 4: 성과 검증 온체인화 ===

class UpdatePerformanceRequest(BaseModel):
    strategy_pda: str
    trade_pnl_scaled: int  # 1e8 스케일
    holding_seconds: int = 0
    is_live: bool = False
    sharpe_ratio_scaled: int = 0
    profit_factor_scaled: int = 0


@router.post("/performance/update")
async def update_performance_endpoint(
    body: UpdatePerformanceRequest,
    user_id: str | None = Depends(get_current_user_id),
):
    """온체인 성과 업데이트 (Anchor instruction)"""
    from services.blockchain.anchor_client import update_performance_onchain
    from services.blockchain.borsh_utils import UpdatePerformanceArgs

    args = UpdatePerformanceArgs(
        trade_pnl_scaled=body.trade_pnl_scaled,
        holding_seconds=body.holding_seconds,
        is_live=body.is_live,
        sharpe_ratio_scaled=body.sharpe_ratio_scaled,
        profit_factor_scaled=body.profit_factor_scaled,
    )
    result = await update_performance_onchain(body.strategy_pda, args)
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@router.post("/performance/verify/{strategy_pda}")
async def verify_track_record_endpoint(strategy_pda: str):
    """트랙 레코드 검증 (퍼미션리스, 3회 검증 시 is_verified=true)"""
    from services.blockchain.anchor_client import verify_track_record_onchain

    result = await verify_track_record_onchain(strategy_pda)
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    return result


# === Phase 5-3: 마켓플레이스 구매/대여 ===

class PurchaseRequest(BaseModel):
    strategy_pda: str
    strategy_owner: str
    buyer_pubkey: Optional[str] = None


class RentRequest(BaseModel):
    strategy_pda: str
    days: int = 30
    renter_pubkey: Optional[str] = None


@router.post("/marketplace/purchase")
async def purchase_strategy_endpoint(
    body: PurchaseRequest,
    user_id: str | None = Depends(get_current_user_id),
):
    """전략 영구 구매 (SOL 95% owner + 5% treasury)"""
    from services.blockchain.marketplace_client import purchase_strategy

    result = await purchase_strategy(
        strategy_pda_str=body.strategy_pda,
        strategy_owner_str=body.strategy_owner,
        buyer_pubkey_str=body.buyer_pubkey,
    )
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@router.post("/marketplace/rent")
async def rent_strategy_endpoint(
    body: RentRequest,
    user_id: str | None = Depends(get_current_user_id),
):
    """전략 기간 대여 (SOL → Escrow, 일일 정산)"""
    from services.blockchain.marketplace_client import rent_strategy

    result = await rent_strategy(
        strategy_pda_str=body.strategy_pda,
        days=body.days,
        renter_pubkey_str=body.renter_pubkey,
    )
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    return result
