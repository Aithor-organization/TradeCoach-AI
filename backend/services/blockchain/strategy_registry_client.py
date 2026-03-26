"""
전략 온체인 등록 및 성과 관리 — Anchor instruction + Memo 폴백.

Tier 2: Anchor register_strategy instruction으로 온체인 구조화 데이터 저장.
Tier 1 폴백: Anchor 실패 시 Memo TX로 등록 증명 기록.
"""

import hashlib
import json
import logging
import time
from typing import Optional

from .onchain_client import load_server_keypair, record_trades_onchain, SOLANA_AVAILABLE
from .merkle_tree import build_trade_merkle, verify_merkle_proof, compute_leaf

logger = logging.getLogger(__name__)

# 인메모리 성과 저장소 (프로덕션에서는 DB 사용)
_strategy_performances: dict[str, dict] = {}
_strategy_trade_history: dict[str, list[dict]] = {}


async def register_strategy_onchain(
    strategy_id: str,
    strategy_name: str,
    strategy_data: dict,
) -> dict:
    """
    전략을 온체인에 등록 — Anchor 우선, Memo 폴백.

    1. Anchor register_strategy instruction 시도 (구조화된 온체인 데이터)
    2. 실패 시 Memo TX로 등록 증명 기록 (해시만)
    """
    if not SOLANA_AVAILABLE:
        return {"error": "solana 미설치", "tx_signature": None}

    # Tier 2: Anchor instruction 시도
    try:
        anchor_result = await _register_via_anchor(
            strategy_name, strategy_data,
        )
        if anchor_result and not anchor_result.get("error"):
            logger.info(f"Anchor 등록 성공: {anchor_result.get('tx_signature')}")
            anchor_result["strategy_id"] = strategy_id
            anchor_result["registered_at"] = int(time.time())
            return anchor_result
        logger.warning(f"Anchor 등록 실패, Memo 폴백: {anchor_result.get('error')}")
    except Exception as e:
        logger.warning(f"Anchor 호출 예외, Memo 폴백: {e}")

    # Tier 1 폴백: Memo TX
    return await _register_via_memo(strategy_id, strategy_name, strategy_data)


async def _register_via_anchor(
    strategy_name: str,
    strategy_data: dict,
) -> dict:
    """Anchor register_strategy instruction으로 등록"""
    from .anchor_client import register_strategy_anchor
    from .borsh_utils import RegisterStrategyArgs, BacktestSummary

    # strategy_data에서 Anchor args 구성
    backtest = strategy_data.get("backtest", {})
    symbols = strategy_data.get("symbols", ["BTCUSDT"])
    if isinstance(symbols, str):
        symbols = [symbols]

    args = RegisterStrategyArgs(
        name=strategy_name[:64],
        description=strategy_data.get("description", "")[:256],
        metadata_uri=strategy_data.get("metadata_uri", "")[:128],
        market=strategy_data.get("market", "BinanceFutures"),
        time_frame=strategy_data.get("time_frame", "D1"),
        symbols=symbols[:5],
        symbol_count=min(len(symbols), 5),
        backtest=BacktestSummary(
            period_start=backtest.get("period_start", 0),
            period_end=backtest.get("period_end", 0),
            total_trades=backtest.get("total_trades", 0),
            win_rate_bps=backtest.get("win_rate_bps", 0),
            total_return_bps=backtest.get("total_return_bps", 0),
            max_drawdown_bps=backtest.get("max_drawdown_bps", 0),
            sharpe_ratio_scaled=backtest.get("sharpe_ratio_scaled", 0),
            profit_factor_scaled=backtest.get("profit_factor_scaled", 0),
            avg_leverage=backtest.get("avg_leverage", 1),
            max_leverage=backtest.get("max_leverage", 1),
        ),
        price_lamports=strategy_data.get("price_lamports", 100_000_000),
        rent_lamports_per_day=strategy_data.get("rent_lamports_per_day", 10_000_000),
    )

    return await register_strategy_anchor(args)


async def _register_via_memo(
    strategy_id: str,
    strategy_name: str,
    strategy_data: dict,
) -> dict:
    """Tier 1 폴백: Memo TX로 등록 증명 기록"""
    strategy_hash = hashlib.sha256(
        json.dumps(strategy_data, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    memo_data = {
        "app": "TradeCoach-AI",
        "v": 2,
        "type": "strategy_register",
        "id": strategy_id[:16],
        "name": strategy_name[:32],
        "hash": strategy_hash[:32],
        "ts": int(time.time()),
    }

    keypair = load_server_keypair()
    if not keypair:
        return {"error": "서버 키페어 없음", "tx_signature": None}

    import os
    from solana.rpc.async_api import AsyncClient
    from solders.instruction import Instruction, AccountMeta
    from solders.pubkey import Pubkey
    from solders.transaction import Transaction
    from solders.message import Message

    MEMO_PROGRAM_ID = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")
    rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com")

    try:
        async with AsyncClient(rpc_url) as client:
            resp = await client.get_latest_blockhash()
            blockhash = resp.value.blockhash

            memo_bytes = json.dumps(memo_data, separators=(",", ":")).encode("utf-8")
            memo_ix = Instruction(
                program_id=MEMO_PROGRAM_ID,
                accounts=[AccountMeta(keypair.pubkey(), is_signer=True, is_writable=True)],
                data=memo_bytes,
            )

            msg = Message.new_with_blockhash([memo_ix], keypair.pubkey(), blockhash)
            tx = Transaction.new_unsigned(msg)
            tx.sign([keypair], blockhash)

            result = await client.send_transaction(tx)
            tx_sig = str(result.value)

            network = os.getenv("SOLANA_NETWORK", "devnet")
            cluster_param = f"?cluster={network}" if network != "mainnet-beta" else ""

            return {
                "tx_signature": tx_sig,
                "strategy_hash": strategy_hash,
                "explorer_url": f"https://explorer.solana.com/tx/{tx_sig}{cluster_param}",
                "network": network,
                "registered_at": int(time.time()),
                "tier": 1,
            }

    except Exception as e:
        logger.error(f"전략 Memo 등록도 실패: {e}")
        return {"error": str(e), "tx_signature": None}


def update_performance(strategy_id: str, session_result: dict) -> dict:
    """
    모의투자 결과를 성과 데이터에 반영.

    매 Stop마다 호출되어 누적 성과를 계산.
    """
    if strategy_id not in _strategy_performances:
        _strategy_performances[strategy_id] = {
            "total_trades": 0,
            "winning_trades": 0,
            "total_pnl": 0.0,
            "max_drawdown": 0.0,
            "sessions": 0,
            "first_session": int(time.time()),
            "last_session": int(time.time()),
            "tx_signatures": [],
        }

    perf = _strategy_performances[strategy_id]
    trades = session_result.get("trades", [])

    for trade in trades:
        perf["total_trades"] += 1
        pnl = trade.get("pnl", 0)
        perf["total_pnl"] += pnl
        if pnl > 0:
            perf["winning_trades"] += 1
        perf["max_drawdown"] = min(perf["max_drawdown"], pnl)

    perf["sessions"] += 1
    perf["last_session"] = int(time.time())

    if session_result.get("signal_recording", {}).get("tx_signature"):
        perf["tx_signatures"].append(session_result["signal_recording"]["tx_signature"])

    # 파생 지표 계산
    win_rate = (perf["winning_trades"] / perf["total_trades"] * 100) if perf["total_trades"] > 0 else 0

    # 히스토리 저장
    if strategy_id not in _strategy_trade_history:
        _strategy_trade_history[strategy_id] = []
    _strategy_trade_history[strategy_id].extend(trades)

    return {
        "strategy_id": strategy_id,
        "total_trades": perf["total_trades"],
        "winning_trades": perf["winning_trades"],
        "win_rate": round(win_rate, 1),
        "total_pnl": round(perf["total_pnl"], 2),
        "max_drawdown": round(perf["max_drawdown"], 2),
        "sessions": perf["sessions"],
        "tx_count": len(perf["tx_signatures"]),
    }


def get_performance(strategy_id: str) -> Optional[dict]:
    """전략의 누적 성과 조회"""
    perf = _strategy_performances.get(strategy_id)
    if not perf:
        return None

    win_rate = (perf["winning_trades"] / perf["total_trades"] * 100) if perf["total_trades"] > 0 else 0

    return {
        "strategy_id": strategy_id,
        "total_trades": perf["total_trades"],
        "winning_trades": perf["winning_trades"],
        "win_rate": round(win_rate, 1),
        "total_pnl": round(perf["total_pnl"], 2),
        "max_drawdown": round(perf["max_drawdown"], 2),
        "sessions": perf["sessions"],
        "period_days": max(1, (perf["last_session"] - perf["first_session"]) // 86400),
        "tx_signatures": perf["tx_signatures"][-10:],
        "verified": len(perf["tx_signatures"]) > 0,
    }


def get_trade_history(strategy_id: str, limit: int = 50) -> list[dict]:
    """전략의 전체 거래 히스토리"""
    return _strategy_trade_history.get(strategy_id, [])[-limit:]
