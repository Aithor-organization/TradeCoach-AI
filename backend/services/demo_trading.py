"""
가상 데모 트레이딩 엔진 (Paper Trading Simulation)

실시간 가격 피드를 받아 가상의 선물 포지션을 시뮬레이션한다.
- 4종 신호: BUY_LONG, SELL_SHORT, SELL_LONG, BUY_SHORT
- 슬리피지 모델링 (BinanceTrader 동일 0.01%)
- 수수료: PnL 비율 포함 방식 (양방향 0.08%)
- 레버리지 반영 손익 계산
- SL/TP/분할익절/트레일링 스탑 자동 관리
- 강제 청산 시뮬레이션
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

# 수수료율: 0.04% taker fee (바이낸스 선물 기준)
_COMMISSION = 0.0004
# 슬리피지: 0.01% (BinanceTrader 동일)
_SLIPPAGE = 0.0001


class SignalType(str, Enum):
    """4종 거래 신호 타입."""
    BUY_LONG = "BUY_LONG"
    SELL_SHORT = "SELL_SHORT"
    SELL_LONG = "SELL_LONG"
    BUY_SHORT = "BUY_SHORT"


class Side(str, Enum):
    LONG = "long"
    SHORT = "short"


# ---------------------------------------------------------------------------
# 데이터 클래스 정의
# ---------------------------------------------------------------------------

@dataclass
class DemoPosition:
    """활성 가상 포지션 상태."""
    side: str                        # "long" | "short"
    entry_price: float
    quantity: float                  # 수량 (코인 단위)
    leverage: int
    margin: float                    # 사용된 마진 (USDT)
    sl_price: Optional[float] = None
    tp_price: Optional[float] = None
    trailing_trigger: Optional[float] = None
    trailing_callback: Optional[float] = None
    highest_since_entry: float = 0.0
    lowest_since_entry: float = 0.0
    partial_exited: bool = False


@dataclass
class DemoTrade:
    """체결된 거래 기록."""
    side: str           # "long" | "short"
    signal_type: str    # "BUY_LONG" | "SELL_SHORT" | "SELL_LONG" | "BUY_SHORT"
    entry_price: float
    exit_price: float
    quantity: float
    leverage: int
    pnl: float          # 실현 손익 (USDT)
    pnl_pct: float      # 실현 손익률 (%)
    fee: float           # 수수료 (USDT)
    exit_reason: str    # "sl" | "tp" | "trailing" | "partial" | "liquidation" | "manual" | "reversal"
    entry_at: str       # ISO8601
    exit_at: str        # ISO8601


@dataclass
class DemoSession:
    """데모 트레이딩 세션 전체 상태."""
    session_id: str
    symbol: str = "BTCUSDT"
    leverage: int = 10
    initial_balance: float = 1000.0
    current_balance: float = field(default=0.0)
    position: Optional[DemoPosition] = None
    trades: list[DemoTrade] = field(default_factory=list)
    status: str = "active"           # "active" | "stopped"

    def __post_init__(self) -> None:
        if self.current_balance == 0.0:
            self.current_balance = self.initial_balance


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

def _iso(timestamp_ms: int) -> str:
    """밀리초 유닉스 타임스탬프 → ISO8601 문자열."""
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).isoformat()


def _apply_slippage(price: float, side: str, is_entry: bool) -> float:
    """슬리피지 적용: 항상 불리한 방향으로."""
    if is_entry:
        # 진입: 매수는 비싸게, 매도는 싸게
        return price * (1 + _SLIPPAGE) if side == "long" else price * (1 - _SLIPPAGE)
    else:
        # 청산: 매수 청산은 싸게, 매도 청산은 비싸게
        return price * (1 - _SLIPPAGE) if side == "long" else price * (1 + _SLIPPAGE)


# ---------------------------------------------------------------------------
# 데모 트레이딩 엔진
# ---------------------------------------------------------------------------

class DemoEngine:
    """실시간 가격 피드 기반 가상 선물 트레이딩 엔진."""

    def __init__(self, session: DemoSession, strategy_config: dict) -> None:
        self.session = session
        self.config = strategy_config
        self.last_price: float = 0.0

        # 전략에서 위험 관리 파라미터 추출
        risk = strategy_config.get("risk", {})
        exit_cfg = strategy_config.get("exit", {})
        tp_cfg = exit_cfg.get("take_profit", {})
        sl_cfg = exit_cfg.get("stop_loss", {})
        pe_cfg = risk.get("partial_exit", exit_cfg.get("partial_exit", {}))
        ts_cfg = risk.get("trailing_stop", exit_cfg.get("trailing_stop", {}))
        pos_cfg = strategy_config.get("position", {})

        self._tp_pct: float = float(tp_cfg.get("value", 1.5))
        self._sl_pct: float = float(sl_cfg.get("value", -0.4))
        self._partial_enabled: bool = bool(pe_cfg.get("enabled", False))
        self._partial_at_pct: float = float(pe_cfg.get("at_pct", pe_cfg.get("at_percent", 1.2)))
        self._partial_ratio: float = float(pe_cfg.get("ratio", pe_cfg.get("sell_ratio", 0.5)))
        self._trailing_enabled: bool = bool(ts_cfg.get("enabled", False))
        self._trailing_trigger: float = float(ts_cfg.get("trigger_pct", 0.9))
        self._trailing_callback: float = float(ts_cfg.get("callback_pct", 0.2))
        self._risk_ratio: float = float(pos_cfg.get("risk_ratio", 1.0))
        self._direction: str = strategy_config.get("direction", "both")
        # 4종 신호 대기열
        self._pending_signal: Optional[str] = None  # SignalType value

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------

    def signal(self, signal_type: str) -> None:
        """외부에서 4종 신호 주입."""
        valid = {s.value for s in SignalType}
        if signal_type in valid:
            self._pending_signal = signal_type

    def on_price_update(self, price: float, timestamp_ms: int) -> Optional[DemoTrade]:
        """새 가격 틱 처리. SL/TP/청산 신호 등 자동 처리."""
        if self.session.status != "active":
            return None
        self.last_price = price

        pos = self.session.position

        if pos is not None:
            pos.highest_since_entry = max(pos.highest_since_entry, price)
            pos.lowest_since_entry = min(pos.lowest_since_entry, price)

            # 1. 강제 청산
            liq = self._calc_liquidation_price()
            if (pos.side == "long" and price <= liq) or \
               (pos.side == "short" and price >= liq):
                return self._close_position(liq, "liquidation", timestamp_ms)

            # 2. 손절 (SL)
            if pos.sl_price is not None:
                if (pos.side == "long" and price <= pos.sl_price) or \
                   (pos.side == "short" and price >= pos.sl_price):
                    return self._close_position(pos.sl_price, "sl", timestamp_ms)

            # 3. 익절 (TP)
            if pos.tp_price is not None:
                if (pos.side == "long" and price >= pos.tp_price) or \
                   (pos.side == "short" and price <= pos.tp_price):
                    return self._close_position(pos.tp_price, "tp", timestamp_ms)

            # 4. 트레일링 스탑
            if self._trailing_enabled and self._check_trailing(price):
                return self._close_position(price, "trailing", timestamp_ms)

            # 5. 분할 익절
            if self._partial_enabled and not pos.partial_exited:
                upnl_pct = self._unrealized_pnl_pct(price)
                if upnl_pct >= self._partial_at_pct * pos.leverage:
                    self._execute_partial_exit(price, timestamp_ms)

            # 6. 청산 신호 처리 (SELL_LONG / BUY_SHORT)
            if self._pending_signal:
                sig = self._pending_signal
                if (pos.side == "long" and sig == SignalType.SELL_LONG.value) or \
                   (pos.side == "short" and sig == SignalType.BUY_SHORT.value):
                    self._pending_signal = None
                    return self._close_position(price, "signal", timestamp_ms)
                # 반전 신호: 기존 포지션 청산 후 반대 방향 진입
                if (pos.side == "long" and sig == SignalType.SELL_SHORT.value) or \
                   (pos.side == "short" and sig == SignalType.BUY_LONG.value):
                    self._pending_signal = None
                    trade = self._close_position(price, "reversal", timestamp_ms)
                    new_side = "short" if sig == SignalType.SELL_SHORT.value else "long"
                    self._open_position(new_side, price, timestamp_ms)
                    return trade

            return None

        # 포지션 없음: 진입 신호 처리 (BUY_LONG / SELL_SHORT)
        if self._pending_signal:
            sig = self._pending_signal
            self._pending_signal = None
            if sig == SignalType.BUY_LONG.value:
                self._open_position("long", price, timestamp_ms)
            elif sig == SignalType.SELL_SHORT.value:
                self._open_position("short", price, timestamp_ms)
        return None

    def _open_position(self, side: str, price: float, timestamp_ms: int) -> None:
        """신규 포지션 진입 (슬리피지 + 수수료 적용)."""
        if self.session.current_balance <= 0:
            return

        # 슬리피지 적용
        entry_price = _apply_slippage(price, side, is_entry=True)

        # 수량 계산: (잔고 × 위험비율 / 진입가) × 레버리지
        usable = self.session.current_balance * self._risk_ratio
        qty = (usable / entry_price) * self.session.leverage
        margin = usable  # 사용 마진

        # 진입 수수료: 체결금액 기준 (BinanceTrader 방식)
        entry_fee = qty * entry_price * _COMMISSION
        self.session.current_balance -= entry_fee

        # SL/TP 절대가격 계산
        sl_abs: Optional[float] = None
        tp_abs: Optional[float] = None
        if self._sl_pct != 0:
            ratio = abs(self._sl_pct) / (100 * self.session.leverage)
            sl_abs = entry_price * (1 - ratio) if side == "long" else entry_price * (1 + ratio)
        if self._tp_pct != 0:
            ratio = abs(self._tp_pct) / (100 * self.session.leverage)
            tp_abs = entry_price * (1 + ratio) if side == "long" else entry_price * (1 - ratio)

        self.session.position = DemoPosition(
            side=side,
            entry_price=entry_price,
            quantity=qty,
            leverage=self.session.leverage,
            margin=margin,
            sl_price=sl_abs,
            tp_price=tp_abs,
            trailing_trigger=self._trailing_trigger if self._trailing_enabled else None,
            trailing_callback=self._trailing_callback if self._trailing_enabled else None,
            highest_since_entry=entry_price,
            lowest_since_entry=entry_price,
        )

    def _close_position(
        self, price: float, reason: str, timestamp_ms: int
    ) -> Optional[DemoTrade]:
        """포지션 전량 청산 (BinanceTrader PnL 방식)."""
        pos = self.session.position
        if pos is None:
            return None

        # 슬리피지 적용 (SL/TP는 정확한 가격이므로 reason에 따라 분기)
        if reason in ("sl", "tp", "liquidation"):
            exit_price = price  # SL/TP 가격은 이미 설정된 절대가
        else:
            exit_price = _apply_slippage(price, pos.side, is_entry=False)

        # PnL 계산: BinanceTrader 방식 (수수료를 비율에 포함)
        fee_pct = _COMMISSION * 2 * 100  # 양방향 0.08%
        if pos.side == "long":
            raw_pnl_pct = (exit_price - pos.entry_price) / pos.entry_price * pos.leverage * 100
        else:
            raw_pnl_pct = (pos.entry_price - exit_price) / pos.entry_price * pos.leverage * 100
        pnl_pct = raw_pnl_pct - fee_pct
        pnl_amount = pos.margin * pnl_pct / 100

        # 실제 수수료 금액
        fee_amount = pos.quantity * pos.entry_price * _COMMISSION + pos.quantity * exit_price * _COMMISSION

        self.session.current_balance += pnl_amount

        if self.session.current_balance <= 0:
            self.session.current_balance = 0.0
            self.session.status = "stopped"

        # 청산 signal_type 결정
        if pos.side == "long":
            signal_type = SignalType.SELL_LONG.value
        else:
            signal_type = SignalType.BUY_SHORT.value

        trade = DemoTrade(
            side=pos.side,
            signal_type=signal_type,
            entry_price=pos.entry_price,
            exit_price=exit_price,
            quantity=pos.quantity,
            leverage=pos.leverage,
            pnl=round(pnl_amount, 4),
            pnl_pct=round(pnl_pct, 4),
            fee=round(fee_amount, 4),
            exit_reason=reason,
            entry_at=_iso(timestamp_ms - 1),
            exit_at=_iso(timestamp_ms),
        )
        self.session.trades.append(trade)
        self.session.position = None
        return trade

    def get_status(self, current_price: Optional[float] = None) -> dict:
        """현재 세션 상태 스냅샷."""
        pos = self.session.position
        unrealized = 0.0
        liq_price: Optional[float] = None

        if pos is not None:
            price = current_price or self.last_price or pos.entry_price
            unrealized = self._calc_unrealized_pnl(price)
            liq_price = self._calc_liquidation_price()

        return {
            "session_id": self.session.session_id,
            "symbol": self.session.symbol,
            "leverage": self.session.leverage,
            "initial_balance": self.session.initial_balance,
            "current_balance": round(self.session.current_balance, 4),
            "unrealized_pnl": round(unrealized, 4),
            "current_price": self.last_price,
            "total_trades": len(self.session.trades),
            "status": self.session.status,
            "position": {
                "side": pos.side,
                "entry_price": pos.entry_price,
                "quantity": round(pos.quantity, 6),
                "margin": round(pos.margin, 4),
                "sl_price": pos.sl_price,
                "tp_price": pos.tp_price,
                "liquidation_price": liq_price,
                "highest_since_entry": pos.highest_since_entry,
                "lowest_since_entry": pos.lowest_since_entry,
            } if pos else None,
        }

    # ------------------------------------------------------------------
    # 내부 헬퍼
    # ------------------------------------------------------------------

    def _calc_liquidation_price(self) -> float:
        pos = self.session.position
        if pos is None:
            return 0.0
        margin_ratio = 1.0 / pos.leverage
        if pos.side == "long":
            return pos.entry_price * (1 - margin_ratio + _COMMISSION)
        return pos.entry_price * (1 + margin_ratio - _COMMISSION)

    def _calc_unrealized_pnl(self, current_price: float) -> float:
        pos = self.session.position
        if pos is None:
            return 0.0
        if pos.side == "long":
            return pos.quantity * (current_price - pos.entry_price)
        return pos.quantity * (pos.entry_price - current_price)

    def _unrealized_pnl_pct(self, current_price: float) -> float:
        """미실현 PnL% (레버리지 포함)."""
        pos = self.session.position
        if pos is None:
            return 0.0
        if pos.side == "long":
            return (current_price - pos.entry_price) / pos.entry_price * 100 * pos.leverage
        return (pos.entry_price - current_price) / pos.entry_price * 100 * pos.leverage

    def _check_trailing(self, price: float) -> bool:
        pos = self.session.position
        if pos is None or pos.trailing_trigger is None or pos.trailing_callback is None:
            return False
        trigger_pct = pos.trailing_trigger * pos.leverage
        callback_pct = pos.trailing_callback * pos.leverage
        if pos.side == "long":
            peak_pnl = (pos.highest_since_entry - pos.entry_price) / pos.entry_price * 100 * pos.leverage
            if peak_pnl >= trigger_pct:
                current_pnl = (price - pos.entry_price) / pos.entry_price * 100 * pos.leverage
                return (peak_pnl - current_pnl) >= callback_pct
        else:
            peak_pnl = (pos.entry_price - pos.lowest_since_entry) / pos.entry_price * 100 * pos.leverage
            if peak_pnl >= trigger_pct:
                current_pnl = (pos.entry_price - price) / pos.entry_price * 100 * pos.leverage
                return (peak_pnl - current_pnl) >= callback_pct
        return False

    def _execute_partial_exit(self, price: float, timestamp_ms: int) -> None:
        """분할 익절: 수량 일부 청산."""
        pos = self.session.position
        if pos is None:
            return

        exit_qty = pos.quantity * self._partial_ratio
        exit_price = _apply_slippage(price, pos.side, is_entry=False)

        # PnL 계산 (BinanceTrader 방식)
        fee_pct = _COMMISSION * 2 * 100
        if pos.side == "long":
            raw_pnl_pct = (exit_price - pos.entry_price) / pos.entry_price * pos.leverage * 100
        else:
            raw_pnl_pct = (pos.entry_price - exit_price) / pos.entry_price * pos.leverage * 100
        pnl_pct = raw_pnl_pct - fee_pct
        partial_margin = pos.margin * self._partial_ratio
        partial_pnl = partial_margin * pnl_pct / 100
        fee_amount = exit_qty * pos.entry_price * _COMMISSION + exit_qty * exit_price * _COMMISSION

        self.session.current_balance += partial_pnl
        pos.quantity -= exit_qty
        pos.margin -= partial_margin
        pos.partial_exited = True

        signal_type = SignalType.SELL_LONG.value if pos.side == "long" else SignalType.BUY_SHORT.value
        trade = DemoTrade(
            side=pos.side,
            signal_type=signal_type,
            entry_price=pos.entry_price,
            exit_price=exit_price,
            quantity=exit_qty,
            leverage=pos.leverage,
            pnl=round(partial_pnl, 4),
            pnl_pct=round(pnl_pct, 4),
            fee=round(fee_amount, 4),
            exit_reason="partial",
            entry_at=_iso(timestamp_ms - 1),
            exit_at=_iso(timestamp_ms),
        )
        self.session.trades.append(trade)
