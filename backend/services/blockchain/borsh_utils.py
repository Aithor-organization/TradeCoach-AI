"""
Borsh 직렬화 유틸리티 — Anchor IDL 기반 instruction 데이터 인코딩.

solders의 Pubkey.find_program_address()를 PDA 계산에 사용하고,
struct 모듈로 Borsh 바이너리 직렬화를 수행.
"""

import struct
from dataclasses import dataclass
from typing import Optional

try:
    from solders.pubkey import Pubkey  # type: ignore
    SOLDERS_AVAILABLE = True
except ImportError:
    SOLDERS_AVAILABLE = False


# ─── Anchor Discriminator (IDL에서 추출) ───

DISCRIMINATORS = {
    # strategy_registry
    "initialize_platform": bytes([119, 201, 101, 45, 75, 122, 89, 3]),
    "register_strategy": bytes([121, 12, 64, 75, 99, 15, 177, 143]),
    "delete_strategy": bytes([170, 252, 31, 143, 231, 7, 212, 159]),
    "toggle_pause": bytes([238, 237, 206, 27, 255, 95, 123, 229]),
    "update_metadata_uri": bytes([27, 40, 178, 7, 93, 135, 196, 102]),
    # performance_verifier
    "update_performance": bytes([11, 251, 66, 148, 20, 86, 149, 20]),
    "verify_track_record": bytes([150, 12, 215, 138, 127, 80, 19, 23]),
    "update_ranking": bytes([129, 41, 207, 232, 254, 219, 175, 196]),
    # strategy_marketplace
    "purchase_strategy": bytes([231, 1, 25, 228, 190, 253, 4, 179]),
    "rent_strategy": bytes([109, 113, 229, 70, 106, 28, 202, 118]),
    "daily_settle": bytes([243, 239, 169, 202, 141, 84, 213, 214]),
    "expire_rental": bytes([157, 4, 166, 64, 175, 60, 122, 46]),
    "claim_revenue": bytes([4, 22, 151, 70, 183, 79, 73, 189]),
}

# ─── Enum 매핑 ───

MARKET_VARIANTS = {
    "BinanceFutures": 0,
    "BinanceSpot": 1,
    "BybitFutures": 2,
}

TIMEFRAME_VARIANTS = {
    "M1": 0, "M5": 1, "M15": 2,
    "H1": 3, "H4": 4, "D1": 5, "W1": 6,
}


# ─── PDA 계산 ───

def get_platform_pda(program_id: str) -> tuple[str, int]:
    """Platform PDA: seeds = [b"platform"]"""
    if not SOLDERS_AVAILABLE:
        raise RuntimeError("solders 미설치")
    pid = Pubkey.from_string(program_id)
    pda, bump = Pubkey.find_program_address([b"platform"], pid)
    return str(pda), bump


def get_strategy_pda(strategy_count: int, program_id: str) -> tuple[str, int]:
    """Strategy PDA: seeds = [b"strategy", strategy_count.to_le_bytes(8)]"""
    if not SOLDERS_AVAILABLE:
        raise RuntimeError("solders 미설치")
    pid = Pubkey.from_string(program_id)
    count_bytes = struct.pack("<Q", strategy_count)  # u64 little-endian
    pda, bump = Pubkey.find_program_address([b"strategy", count_bytes], pid)
    return str(pda), bump


# ─── 고정 크기 바이트 배열 헬퍼 ───

def _pad_bytes(data: bytes, size: int) -> bytes:
    """data를 size 바이트로 패딩 (잘림 + 0-패딩)"""
    return data[:size].ljust(size, b"\x00")


def _str_to_fixed(s: str, size: int) -> bytes:
    """문자열을 UTF-8로 인코딩 후 고정 크기 바이트 배열로 변환"""
    return _pad_bytes(s.encode("utf-8"), size)


def _symbols_to_fixed(symbols: list[str], max_count: int = 5) -> bytes:
    """심볼 리스트를 [[u8; 16]; 5] 고정 배열로 직렬화"""
    result = b""
    for i in range(max_count):
        sym = symbols[i] if i < len(symbols) else ""
        result += _str_to_fixed(sym, 16)
    return result


# ─── BacktestSummary 직렬화 ───

@dataclass
class BacktestSummary:
    period_start: int       # i64
    period_end: int         # i64
    total_trades: int       # u32
    win_rate_bps: int       # u16 (5000 = 50%)
    total_return_bps: int   # i32
    max_drawdown_bps: int   # u16
    sharpe_ratio_scaled: int  # i16 (185 = 1.85)
    profit_factor_scaled: int  # u16 (210 = 2.10)
    avg_leverage: int       # u8
    max_leverage: int       # u8

    def to_borsh(self) -> bytes:
        return struct.pack(
            "<qqIHiHhHBB",
            self.period_start,
            self.period_end,
            self.total_trades,
            self.win_rate_bps,
            self.total_return_bps,
            self.max_drawdown_bps,
            self.sharpe_ratio_scaled,
            self.profit_factor_scaled,
            self.avg_leverage,
            self.max_leverage,
        )


# ─── RegisterStrategyArgs 직렬화 ───

@dataclass
class RegisterStrategyArgs:
    name: str                           # → [u8; 64]
    description: str                    # → [u8; 256]
    metadata_uri: str                   # → [u8; 128]
    market: str                         # → Market enum (1 byte)
    time_frame: str                     # → TimeFrame enum (1 byte)
    symbols: list[str]                  # → [[u8; 16]; 5]
    symbol_count: int                   # → u8
    backtest: BacktestSummary
    price_lamports: int                 # → u64
    rent_lamports_per_day: int          # → u64

    def to_borsh(self) -> bytes:
        data = b""
        data += _str_to_fixed(self.name, 64)
        data += _str_to_fixed(self.description, 256)
        data += _str_to_fixed(self.metadata_uri, 128)
        data += struct.pack("<B", MARKET_VARIANTS.get(self.market, 0))
        data += struct.pack("<B", TIMEFRAME_VARIANTS.get(self.time_frame, 5))
        data += _symbols_to_fixed(self.symbols)
        data += struct.pack("<B", min(self.symbol_count, 5))
        data += self.backtest.to_borsh()
        data += struct.pack("<Q", self.price_lamports)
        data += struct.pack("<Q", self.rent_lamports_per_day)
        return data


# ─── Instruction 데이터 빌더 ───

def build_initialize_platform_data(fee_bps: int) -> bytes:
    """initialize_platform instruction 데이터 (discriminator + args)"""
    return DISCRIMINATORS["initialize_platform"] + struct.pack("<H", fee_bps)


def build_register_strategy_data(args: RegisterStrategyArgs) -> bytes:
    """register_strategy instruction 데이터 (discriminator + args)"""
    return DISCRIMINATORS["register_strategy"] + args.to_borsh()


# ─── Phase 4: Performance Verifier ───

def get_performance_pda(strategy_pubkey: str, program_id: str) -> tuple[str, int]:
    """Performance PDA: seeds = [b"perf", strategy_pubkey]"""
    if not SOLDERS_AVAILABLE:
        raise RuntimeError("solders 미설치")
    pid = Pubkey.from_string(program_id)
    strategy = Pubkey.from_string(strategy_pubkey)
    pda, bump = Pubkey.find_program_address([b"perf", bytes(strategy)], pid)
    return str(pda), bump


@dataclass
class UpdatePerformanceArgs:
    trade_pnl_scaled: int    # i64 (1e8 스케일)
    holding_seconds: int     # u64
    is_live: bool            # bool
    sharpe_ratio_scaled: int  # i16
    profit_factor_scaled: int  # u16

    def to_borsh(self) -> bytes:
        return struct.pack(
            "<qQ?hH",
            self.trade_pnl_scaled,
            self.holding_seconds,
            self.is_live,
            self.sharpe_ratio_scaled,
            self.profit_factor_scaled,
        )


def build_update_performance_data(args: UpdatePerformanceArgs) -> bytes:
    return DISCRIMINATORS["update_performance"] + args.to_borsh()


def build_verify_track_record_data() -> bytes:
    return DISCRIMINATORS["verify_track_record"]


# ─── Phase 5-3: Marketplace PDA ───

def get_license_pda(strategy_pubkey: str, buyer_pubkey: str, program_id: str) -> tuple[str, int]:
    """License PDA: seeds = [b"license", strategy, buyer]"""
    if not SOLDERS_AVAILABLE:
        raise RuntimeError("solders 미설치")
    pid = Pubkey.from_string(program_id)
    strategy = Pubkey.from_string(strategy_pubkey)
    buyer = Pubkey.from_string(buyer_pubkey)
    pda, bump = Pubkey.find_program_address(
        [b"license", bytes(strategy), bytes(buyer)], pid
    )
    return str(pda), bump


def get_revenue_pda(strategy_pubkey: str, program_id: str) -> tuple[str, int]:
    """Revenue PDA: seeds = [b"revenue", strategy]"""
    if not SOLDERS_AVAILABLE:
        raise RuntimeError("solders 미설치")
    pid = Pubkey.from_string(program_id)
    strategy = Pubkey.from_string(strategy_pubkey)
    pda, bump = Pubkey.find_program_address([b"revenue", bytes(strategy)], pid)
    return str(pda), bump


def get_escrow_pda(strategy_pubkey: str, program_id: str) -> tuple[str, int]:
    """Escrow PDA: seeds = [b"escrow", strategy]"""
    if not SOLDERS_AVAILABLE:
        raise RuntimeError("solders 미설치")
    pid = Pubkey.from_string(program_id)
    strategy = Pubkey.from_string(strategy_pubkey)
    pda, bump = Pubkey.find_program_address([b"escrow", bytes(strategy)], pid)
    return str(pda), bump


def build_purchase_strategy_data() -> bytes:
    """purchase_strategy는 args 없음 (가격은 Strategy 계정에서 읽음)"""
    return DISCRIMINATORS["purchase_strategy"]


def build_rent_strategy_data(days: int) -> bytes:
    return DISCRIMINATORS["rent_strategy"] + struct.pack("<I", days)
