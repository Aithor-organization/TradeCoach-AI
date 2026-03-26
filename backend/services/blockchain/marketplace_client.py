"""
마켓플레이스 클라이언트 — 전략 구매/대여 Anchor instruction.

strategy_marketplace 프로그램의 purchase_strategy, rent_strategy를 호출하여
SOL 결제 + License PDA 생성을 수행.
"""

import logging
from typing import Optional

from .onchain_client import load_server_keypair, SOLANA_AVAILABLE
from .borsh_utils import (
    build_purchase_strategy_data,
    build_rent_strategy_data,
    get_license_pda,
    get_revenue_pda,
    get_escrow_pda,
)

if SOLANA_AVAILABLE:
    from solders.pubkey import Pubkey  # type: ignore
    from solders.system_program import ID as SYSTEM_PROGRAM_ID  # type: ignore
    from solders.instruction import Instruction, AccountMeta  # type: ignore

logger = logging.getLogger(__name__)


def _get_marketplace_config():
    from config import get_settings
    s = get_settings()
    return {
        "marketplace_id": s.program_strategy_marketplace,
        "rpc_url": s.solana_rpc_url,
        "network": s.solana_network,
    }


def _explorer_url(tx_sig: str, network: str) -> str:
    cluster = f"?cluster={network}" if network != "mainnet-beta" else ""
    return f"https://explorer.solana.com/tx/{tx_sig}{cluster}"


async def purchase_strategy(
    strategy_pda_str: str,
    strategy_owner_str: str,
    buyer_pubkey_str: Optional[str] = None,
) -> dict:
    """
    전략 영구 구매. SOL이 95% owner + 5% treasury로 분배되고 License PDA 생성.

    buyer_pubkey_str이 None이면 서버 키페어를 buyer로 사용 (테스트용).
    프로덕션에서는 프론트엔드에서 Phantom 지갑으로 TX를 서명.
    """
    if not SOLANA_AVAILABLE:
        return {"error": "solana 미설치"}

    keypair = load_server_keypair()
    if not keypair:
        return {"error": "서버 키페어 없음"}

    cfg = _get_marketplace_config()
    mp_id = cfg["marketplace_id"]

    buyer = Pubkey.from_string(buyer_pubkey_str) if buyer_pubkey_str else keypair.pubkey()
    strategy_pda = Pubkey.from_string(strategy_pda_str)
    strategy_owner = Pubkey.from_string(strategy_owner_str)

    license_pda_str, _ = get_license_pda(strategy_pda_str, str(buyer), mp_id)
    license_pda = Pubkey.from_string(license_pda_str)
    revenue_pda_str, _ = get_revenue_pda(strategy_pda_str, mp_id)
    revenue_pda = Pubkey.from_string(revenue_pda_str)

    # treasury = 서버 키페어 (개발용)
    treasury = keypair.pubkey()
    pid = Pubkey.from_string(mp_id)

    ix = Instruction(
        program_id=pid,
        accounts=[
            AccountMeta(strategy_pda, is_signer=False, is_writable=False),
            AccountMeta(license_pda, is_signer=False, is_writable=True),
            AccountMeta(revenue_pda, is_signer=False, is_writable=True),
            AccountMeta(strategy_owner, is_signer=False, is_writable=True),
            AccountMeta(treasury, is_signer=False, is_writable=True),
            AccountMeta(buyer, is_signer=True, is_writable=True),
            AccountMeta(SYSTEM_PROGRAM_ID, is_signer=False, is_writable=False),
        ],
        data=build_purchase_strategy_data(),
    )

    try:
        from .anchor_client import _send_tx
        tx_sig = await _send_tx([ix], keypair, cfg["rpc_url"])
        logger.info(f"전략 구매 완료: license={license_pda_str[:16]}, tx={tx_sig}")
        return {
            "tx_signature": tx_sig,
            "license_pda": license_pda_str,
            "license_type": "Permanent",
            "explorer_url": _explorer_url(tx_sig, cfg["network"]),
        }
    except Exception as e:
        logger.error(f"전략 구매 실패: {e}")
        return {"error": str(e)}


async def rent_strategy(
    strategy_pda_str: str,
    days: int = 30,
    renter_pubkey_str: Optional[str] = None,
) -> dict:
    """
    전략 기간 대여. SOL이 Escrow PDA에 보관되고 daily_settle로 일일 정산.

    renter_pubkey_str이 None이면 서버 키페어를 renter로 사용 (테스트용).
    """
    if not SOLANA_AVAILABLE:
        return {"error": "solana 미설치"}
    if days < 1:
        return {"error": "대여 기간은 최소 1일"}

    keypair = load_server_keypair()
    if not keypair:
        return {"error": "서버 키페어 없음"}

    cfg = _get_marketplace_config()
    mp_id = cfg["marketplace_id"]

    renter = Pubkey.from_string(renter_pubkey_str) if renter_pubkey_str else keypair.pubkey()
    strategy_pda = Pubkey.from_string(strategy_pda_str)

    license_pda_str, _ = get_license_pda(strategy_pda_str, str(renter), mp_id)
    license_pda = Pubkey.from_string(license_pda_str)
    revenue_pda_str, _ = get_revenue_pda(strategy_pda_str, mp_id)
    revenue_pda = Pubkey.from_string(revenue_pda_str)
    escrow_pda_str, _ = get_escrow_pda(strategy_pda_str, mp_id)
    escrow_pda = Pubkey.from_string(escrow_pda_str)
    pid = Pubkey.from_string(mp_id)

    ix = Instruction(
        program_id=pid,
        accounts=[
            AccountMeta(strategy_pda, is_signer=False, is_writable=False),
            AccountMeta(license_pda, is_signer=False, is_writable=True),
            AccountMeta(revenue_pda, is_signer=False, is_writable=True),
            AccountMeta(escrow_pda, is_signer=False, is_writable=True),
            AccountMeta(renter, is_signer=True, is_writable=True),
            AccountMeta(SYSTEM_PROGRAM_ID, is_signer=False, is_writable=False),
        ],
        data=build_rent_strategy_data(days),
    )

    try:
        from .anchor_client import _send_tx
        tx_sig = await _send_tx([ix], keypair, cfg["rpc_url"])
        logger.info(f"전략 대여 완료: {days}일, license={license_pda_str[:16]}, tx={tx_sig}")
        return {
            "tx_signature": tx_sig,
            "license_pda": license_pda_str,
            "escrow_pda": escrow_pda_str,
            "license_type": "Subscription",
            "days": days,
            "explorer_url": _explorer_url(tx_sig, cfg["network"]),
        }
    except Exception as e:
        logger.error(f"전략 대여 실패: {e}")
        return {"error": str(e)}
