"""
Phase 5: 블록체인 통합 — Solana State Compression + cNFT.

전략을 cNFT로 민팅하고, 매매 신호를 Merkle Tree에 압축 기록.
Helius DAS API로 조회/검증.
"""

from .strategy_nft import (
    mint_strategy_nft,
    confirm_mint,
    burn_strategy_nft,
    verify_strategy,
    get_strategies_by_owner,
)
from .signal_recorder import (
    record_signal,
    flush_signals_to_chain,
    get_signal_history,
    verify_signal,
    get_buffer_status,
)
from .solana_client import (
    get_rpc_client,
    get_balance,
    request_airdrop,
    helius_get_asset,
    helius_get_asset_proof,
)
from .onchain_client import (
    record_trades_onchain,
    get_server_balance,
    hash_trade_log,
)
from .anchor_client import (
    initialize_platform,
    register_strategy_anchor,
    get_platform_info,
)

__all__ = [
    "mint_strategy_nft",
    "confirm_mint",
    "burn_strategy_nft",
    "verify_strategy",
    "get_strategies_by_owner",
    "record_signal",
    "flush_signals_to_chain",
    "get_signal_history",
    "verify_signal",
    "get_buffer_status",
    "get_rpc_client",
    "get_balance",
    "request_airdrop",
    "helius_get_asset",
    "helius_get_asset_proof",
    "record_trades_onchain",
    "get_server_balance",
    "hash_trade_log",
    "initialize_platform",
    "register_strategy_anchor",
    "get_platform_info",
]
