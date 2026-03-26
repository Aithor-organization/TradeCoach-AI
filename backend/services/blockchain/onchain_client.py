"""
온체인 클라이언트 — Solana Devnet TX 구성 및 전송.

2단계 접근:
  Tier 1: Memo Program으로 trade log 해시 기록 (즉시 사용)
  Tier 2: StrategyVault record_signal instruction (프로그램 배포 후)
"""

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Optional

try:
    from solana.rpc.async_api import AsyncClient
    from solana.rpc.commitment import Confirmed
    from solders.keypair import Keypair  # type: ignore
    from solders.pubkey import Pubkey  # type: ignore
    from solders.system_program import ID as SYSTEM_PROGRAM_ID  # type: ignore
    from solders.transaction import Transaction  # type: ignore
    from solders.message import Message  # type: ignore
    from solders.instruction import Instruction, AccountMeta  # type: ignore
    from solders.hash import Hash  # type: ignore
    SOLANA_AVAILABLE = True
except ImportError:
    SOLANA_AVAILABLE = False

logger = logging.getLogger(__name__)

# Solana Memo Program ID
MEMO_PROGRAM_ID = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr") if SOLANA_AVAILABLE else None

_server_keypair: Optional[Keypair] = None


def load_server_keypair() -> Optional[Keypair]:
    """서버 키페어 로드 (환경변수 우선, 파일 폴백)"""
    global _server_keypair
    if _server_keypair:
        return _server_keypair

    if not SOLANA_AVAILABLE:
        logger.warning("solana/solders 패키지 미설치 — 온체인 기록 비활성화")
        return None

    # 1순위: 환경변수 SOLANA_KEYPAIR_JSON (Railway 등 클라우드 배포용)
    keypair_json = os.getenv("SOLANA_KEYPAIR_JSON")
    if keypair_json:
        try:
            secret = json.loads(keypair_json)
            _server_keypair = Keypair.from_bytes(bytes(secret))
            logger.info(f"서버 키페어 로드 (환경변수): {_server_keypair.pubkey()}")
            return _server_keypair
        except Exception as e:
            logger.error(f"환경변수 키페어 파싱 실패: {e}")

    # 2순위: 파일 경로 (로컬 개발용)
    keypair_path = os.getenv("SOLANA_KEYPAIR_PATH", "~/.config/solana/id.json")
    expanded = Path(keypair_path).expanduser()

    if not expanded.exists():
        logger.warning(f"키페어 미설정 (환경변수 SOLANA_KEYPAIR_JSON 또는 파일 {expanded})")
        return None

    try:
        with open(expanded) as f:
            secret = json.load(f)
        _server_keypair = Keypair.from_bytes(bytes(secret))
        logger.info(f"서버 키페어 로드 (파일): {_server_keypair.pubkey()}")
        return _server_keypair
    except Exception as e:
        logger.error(f"키페어 로드 실패: {e}")
        return None


def hash_trade_log(trades: list[dict]) -> str:
    """거래 로그의 SHA256 해시 생성"""
    canonical = json.dumps(trades, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


async def record_trades_onchain(
    trades: list[dict],
    session_id: str,
    strategy_id: str = "",
) -> dict:
    """
    Tier 1: Memo Program으로 trade log 해시를 온체인에 기록.

    각 거래의 SHA256 해시를 Memo instruction 데이터로 포함하여
    Solana Devnet에 전송. TX signature로 Solana Explorer에서 확인 가능.

    Returns:
        {
            "tx_signature": "5abc...",
            "trade_hash": "sha256...",
            "trades_count": N,
            "explorer_url": "https://explorer.solana.com/tx/...",
            "network": "devnet"
        }
    """
    if not SOLANA_AVAILABLE:
        return {"error": "solana 패키지 미설치", "tx_signature": None}

    keypair = load_server_keypair()
    if not keypair:
        return {"error": "서버 키페어 없음", "tx_signature": None}

    # Merkle Tree 기반 거래 증명 생성
    from .merkle_tree import build_trade_merkle
    merkle_data = build_trade_merkle(trades)
    trade_hash = hash_trade_log(trades)

    # Memo 데이터: Merkle root + 메타데이터 (개별 proof는 DB에 저장)
    memo_data = json.dumps({
        "app": "TradeCoach-AI",
        "v": 2,
        "type": "merkle_root",
        "session": session_id[:16],
        "strategy": strategy_id[:16] if strategy_id else "",
        "root": merkle_data["root"][:32],
        "hash": trade_hash[:32],
        "n": len(trades),
    }, separators=(",", ":"))

    rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com")

    try:
        async with AsyncClient(rpc_url) as client:
            # 최근 블록해시 가져오기
            resp = await client.get_latest_blockhash()
            blockhash = resp.value.blockhash

            # Memo instruction 구성
            memo_ix = Instruction(
                program_id=MEMO_PROGRAM_ID,
                accounts=[AccountMeta(keypair.pubkey(), is_signer=True, is_writable=True)],
                data=memo_data.encode("utf-8"),
            )

            # 트랜잭션 구성 및 서명
            msg = Message.new_with_blockhash(
                [memo_ix],
                keypair.pubkey(),
                blockhash,
            )
            tx = Transaction.new_unsigned(msg)
            tx.sign([keypair], blockhash)

            # 전송
            result = await client.send_transaction(tx)
            tx_sig = str(result.value)

            network = os.getenv("SOLANA_NETWORK", "devnet")
            cluster_param = f"?cluster={network}" if network != "mainnet-beta" else ""
            explorer_url = f"https://explorer.solana.com/tx/{tx_sig}{cluster_param}"

            logger.info(f"온체인 기록 완료: {tx_sig}, trades={len(trades)}, hash={trade_hash[:16]}...")

            return {
                "tx_signature": tx_sig,
                "trade_hash": trade_hash,
                "merkle_root": merkle_data["root"],
                "merkle_proofs": merkle_data["proofs"],
                "trades_count": len(trades),
                "explorer_url": explorer_url,
                "network": network,
            }

    except Exception as e:
        logger.error(f"온체인 기록 실패: {e}")
        return {
            "error": str(e),
            "tx_signature": None,
            "trade_hash": trade_hash,
        }


async def get_server_balance() -> Optional[float]:
    """서버 키페어의 SOL 잔고 조회"""
    if not SOLANA_AVAILABLE:
        return None

    keypair = load_server_keypair()
    if not keypair:
        return None

    rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com")
    try:
        async with AsyncClient(rpc_url) as client:
            resp = await client.get_balance(keypair.pubkey())
            return resp.value / 1_000_000_000
    except Exception as e:
        logger.error(f"잔고 조회 실패: {e}")
        return None
