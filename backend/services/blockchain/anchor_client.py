"""
Anchor 클라이언트 — StrategyVault 프로그램 instruction 직접 호출.

Tier 2 구현: IDL 기반 Borsh 직렬화로 Anchor instruction을 구성하여
온체인에 구조화된 데이터를 저장.
"""

import logging
import struct
from typing import Optional

from .onchain_client import load_server_keypair, SOLANA_AVAILABLE
from .borsh_utils import (
    RegisterStrategyArgs,
    UpdatePerformanceArgs,
    build_initialize_platform_data,
    build_register_strategy_data,
    build_update_performance_data,
    build_verify_track_record_data,
    get_platform_pda,
    get_strategy_pda,
    get_performance_pda,
)

if SOLANA_AVAILABLE:
    from solana.rpc.async_api import AsyncClient
    from solders.pubkey import Pubkey  # type: ignore
    from solders.system_program import ID as SYSTEM_PROGRAM_ID  # type: ignore
    from solders.transaction import Transaction  # type: ignore
    from solders.message import Message  # type: ignore
    from solders.instruction import Instruction, AccountMeta  # type: ignore

logger = logging.getLogger(__name__)

# Anchor account discriminator 크기
ACCOUNT_DISCRIMINATOR_SIZE = 8


def _get_config():
    """설정에서 Program ID 로드"""
    from config import get_settings
    s = get_settings()
    return {
        "strategy_registry": s.program_strategy_registry,
        "performance_verifier": s.program_performance_verifier,
        "strategy_marketplace": s.program_strategy_marketplace,
        "rpc_url": s.solana_rpc_url,
        "network": s.solana_network,
    }


def _explorer_url(tx_sig: str, network: str) -> str:
    cluster = f"?cluster={network}" if network != "mainnet-beta" else ""
    return f"https://explorer.solana.com/tx/{tx_sig}{cluster}"


async def _send_tx(
    instructions: list,
    keypair,
    rpc_url: str,
) -> str:
    """TX 구성 → 서명 → 전송. 성공 시 signature 반환."""
    async with AsyncClient(rpc_url) as client:
        resp = await client.get_latest_blockhash()
        blockhash = resp.value.blockhash

        msg = Message.new_with_blockhash(instructions, keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([keypair], blockhash)

        result = await client.send_transaction(tx)
        return str(result.value)


# ─── Platform 계정 조회 ───

async def get_platform_info(program_id: str) -> Optional[dict]:
    """
    Platform PDA 계정 데이터를 조회하여 strategy_count 등을 반환.
    계정이 없으면 None (초기화 필요).
    """
    if not SOLANA_AVAILABLE:
        return None

    cfg = _get_config()
    pda_str, bump = get_platform_pda(program_id)
    pda = Pubkey.from_string(pda_str)

    try:
        async with AsyncClient(cfg["rpc_url"]) as client:
            resp = await client.get_account_info(pda)
            if not resp.value or not resp.value.data:
                return None

            data = bytes(resp.value.data)
            # Platform 계정 구조 (8 disc + 32 authority + 8 count + 2 fee + 32 treasury + 1 paused + 1 bump)
            if len(data) < ACCOUNT_DISCRIMINATOR_SIZE + 76:
                logger.warning(f"Platform 계정 데이터 크기 불일치: {len(data)}")
                return None

            offset = ACCOUNT_DISCRIMINATOR_SIZE
            authority = Pubkey.from_bytes(data[offset:offset + 32])
            offset += 32
            strategy_count = struct.unpack_from("<Q", data, offset)[0]
            offset += 8
            fee_bps = struct.unpack_from("<H", data, offset)[0]
            offset += 2
            treasury = Pubkey.from_bytes(data[offset:offset + 32])
            offset += 32
            is_paused = bool(data[offset])

            return {
                "pda": pda_str,
                "authority": str(authority),
                "strategy_count": strategy_count,
                "fee_bps": fee_bps,
                "treasury": str(treasury),
                "is_paused": is_paused,
            }
    except Exception as e:
        logger.error(f"Platform 계정 조회 실패: {e}")
        return None


# ─── initialize_platform ───

async def initialize_platform(fee_bps: int = 500) -> dict:
    """
    Platform PDA 초기화. 1회만 실행 (이미 존재하면 스킵).

    Args:
        fee_bps: 플랫폼 수수료 (basis points, 500 = 5%)

    Returns:
        {tx_signature, platform_pda, explorer_url, ...} or {skipped: True}
    """
    if not SOLANA_AVAILABLE:
        return {"error": "solana 미설치"}

    keypair = load_server_keypair()
    if not keypair:
        return {"error": "서버 키페어 없음"}

    cfg = _get_config()
    program_id = cfg["strategy_registry"]

    # 이미 초기화되었는지 확인
    existing = await get_platform_info(program_id)
    if existing:
        logger.info(f"Platform 이미 초기화됨: {existing['pda']}")
        return {"skipped": True, "platform": existing}

    pda_str, _ = get_platform_pda(program_id)
    pda = Pubkey.from_string(pda_str)
    pid = Pubkey.from_string(program_id)

    # treasury = 서버 키페어 (개발용)
    treasury = keypair.pubkey()

    ix = Instruction(
        program_id=pid,
        accounts=[
            AccountMeta(pda, is_signer=False, is_writable=True),
            AccountMeta(keypair.pubkey(), is_signer=True, is_writable=True),
            AccountMeta(treasury, is_signer=False, is_writable=False),
            AccountMeta(SYSTEM_PROGRAM_ID, is_signer=False, is_writable=False),
        ],
        data=build_initialize_platform_data(fee_bps),
    )

    try:
        tx_sig = await _send_tx([ix], keypair, cfg["rpc_url"])
        logger.info(f"Platform 초기화 완료: {tx_sig}")
        return {
            "tx_signature": tx_sig,
            "platform_pda": pda_str,
            "fee_bps": fee_bps,
            "explorer_url": _explorer_url(tx_sig, cfg["network"]),
            "network": cfg["network"],
        }
    except Exception as e:
        logger.error(f"Platform 초기화 실패: {e}")
        return {"error": str(e)}


# ─── register_strategy (Anchor) ───

async def register_strategy_anchor(args: RegisterStrategyArgs) -> dict:
    """
    Anchor register_strategy instruction으로 전략을 온체인에 등록.

    Platform의 strategy_count를 읽어 Strategy PDA를 생성하고,
    Borsh 직렬화된 args로 instruction을 구성.
    """
    if not SOLANA_AVAILABLE:
        return {"error": "solana 미설치"}

    keypair = load_server_keypair()
    if not keypair:
        return {"error": "서버 키페어 없음"}

    cfg = _get_config()
    program_id = cfg["strategy_registry"]

    # Platform 계정에서 현재 strategy_count 조회
    platform_info = await get_platform_info(program_id)
    if not platform_info:
        return {"error": "Platform 미초기화. initialize_platform을 먼저 실행하세요."}

    if platform_info.get("is_paused"):
        return {"error": "Platform이 일시 정지 상태입니다."}

    strategy_count = platform_info["strategy_count"]
    platform_pda_str = platform_info["pda"]
    platform_pda = Pubkey.from_string(platform_pda_str)

    strategy_pda_str, _ = get_strategy_pda(strategy_count, program_id)
    strategy_pda = Pubkey.from_string(strategy_pda_str)
    pid = Pubkey.from_string(program_id)

    ix = Instruction(
        program_id=pid,
        accounts=[
            AccountMeta(platform_pda, is_signer=False, is_writable=True),
            AccountMeta(strategy_pda, is_signer=False, is_writable=True),
            AccountMeta(keypair.pubkey(), is_signer=True, is_writable=True),
            AccountMeta(SYSTEM_PROGRAM_ID, is_signer=False, is_writable=False),
        ],
        data=build_register_strategy_data(args),
    )

    try:
        tx_sig = await _send_tx([ix], keypair, cfg["rpc_url"])
        logger.info(f"전략 Anchor 등록 완료: id={strategy_count}, tx={tx_sig}")
        return {
            "tx_signature": tx_sig,
            "strategy_id_onchain": strategy_count,
            "strategy_pda": strategy_pda_str,
            "platform_pda": platform_pda_str,
            "explorer_url": _explorer_url(tx_sig, cfg["network"]),
            "network": cfg["network"],
            "tier": 2,
        }
    except Exception as e:
        logger.error(f"전략 Anchor 등록 실패: {e}")
        return {"error": str(e)}


# ─── Phase 4: update_performance ───

async def update_performance_onchain(
    strategy_pda_str: str,
    args: UpdatePerformanceArgs,
) -> dict:
    """
    Performance Verifier의 update_performance instruction 호출.
    모의투자 Stop 시 거래 결과를 온체인 Performance 계정에 기록.
    """
    if not SOLANA_AVAILABLE:
        return {"error": "solana 미설치"}

    keypair = load_server_keypair()
    if not keypair:
        return {"error": "서버 키페어 없음"}

    cfg = _get_config()
    perf_program_id = cfg.get("performance_verifier", "")
    if not perf_program_id:
        from config import get_settings
        perf_program_id = get_settings().program_performance_verifier

    strategy_pda = Pubkey.from_string(strategy_pda_str)
    perf_pda_str, _ = get_performance_pda(strategy_pda_str, perf_program_id)
    perf_pda = Pubkey.from_string(perf_pda_str)
    pid = Pubkey.from_string(perf_program_id)

    ix = Instruction(
        program_id=pid,
        accounts=[
            AccountMeta(strategy_pda, is_signer=False, is_writable=False),
            AccountMeta(perf_pda, is_signer=False, is_writable=True),
            AccountMeta(keypair.pubkey(), is_signer=True, is_writable=True),
            AccountMeta(SYSTEM_PROGRAM_ID, is_signer=False, is_writable=False),
        ],
        data=build_update_performance_data(args),
    )

    try:
        tx_sig = await _send_tx([ix], keypair, cfg["rpc_url"])
        logger.info(f"성과 업데이트 완료: strategy={strategy_pda_str[:16]}, tx={tx_sig}")
        return {
            "tx_signature": tx_sig,
            "performance_pda": perf_pda_str,
            "explorer_url": _explorer_url(tx_sig, cfg["network"]),
        }
    except Exception as e:
        logger.error(f"성과 업데이트 실패: {e}")
        return {"error": str(e)}


async def verify_track_record_onchain(strategy_pda_str: str) -> dict:
    """verify_track_record instruction 호출 (퍼미션리스)."""
    if not SOLANA_AVAILABLE:
        return {"error": "solana 미설치"}

    keypair = load_server_keypair()
    if not keypair:
        return {"error": "서버 키페어 없음"}

    cfg = _get_config()
    from config import get_settings
    perf_program_id = get_settings().program_performance_verifier

    perf_pda_str, _ = get_performance_pda(strategy_pda_str, perf_program_id)
    perf_pda = Pubkey.from_string(perf_pda_str)
    pid = Pubkey.from_string(perf_program_id)

    ix = Instruction(
        program_id=pid,
        accounts=[
            AccountMeta(perf_pda, is_signer=False, is_writable=True),
            AccountMeta(keypair.pubkey(), is_signer=True, is_writable=False),
        ],
        data=build_verify_track_record_data(),
    )

    try:
        tx_sig = await _send_tx([ix], keypair, cfg["rpc_url"])
        return {
            "tx_signature": tx_sig,
            "explorer_url": _explorer_url(tx_sig, cfg["network"]),
            "verified": True,
        }
    except Exception as e:
        logger.error(f"트랙 레코드 검증 실패: {e}")
        return {"error": str(e)}
