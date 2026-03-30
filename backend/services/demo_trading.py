"""
가상 데모 트레이딩 엔진 (Paper Trading Simulation)

실시간 가격 피드를 받아 가상의 선물 포지션을 시뮬레이션한다.
- Long/Short/전환 포지션 관리
- 레버리지 반영 손익 계산
- 시장가/지정가 주문 지원
- SL/TP/분할익절/트레일링 스탑 자동 관리
- 강제 청산 시뮬레이션
- 체결 내역은 메모리에 보관 (DB 저장은 라우터에 위임)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

# 수수료율: 0.04% taker fee (바이낸스 선물 기준)
_COMMISSION = 0.0004


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
    sl_price: Optional[float] = None
    tp_price: Optional[float] = None
    trailing_trigger: Optional[float] = None  # 트레일링 발동 수익률 (%)
    trailing_callback: Optional[float] = None  # 트레일링 콜백 비율 (%)
    highest_since_entry: float = 0.0  # 진입 이후 최고가 (트레일링용)
    lowest_since_entry: float = 0.0   # 진입 이후 최저가 (트레일링용)
    partial_exited: bool = False      # 분할 익절 완료 여부


@dataclass
class DemoTrade:
    """체결된 거래 기록."""
    side: str           # "long" | "short"
    entry_price: float
    exit_price: float
    quantity: float
    leverage: int
    pnl: float          # 실현 손익 (USDT)
    exit_reason: str    # "sl" | "tp" | "trailing" | "partial" | "liquidation" | "manual"
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
        # current_balance 미지정 시 initial_balance 로 초기화
        if self.current_balance == 0.0:
            self.current_balance = self.initial_balance


# ---------------------------------------------------------------------------
# 헬퍼: ISO8601 타임스탬프 변환
# ---------------------------------------------------------------------------

def _iso(timestamp_ms: int) -> str:
    """밀리초 유닉스 타임스탬프 → ISO8601 문자열."""
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# 데모 트레이딩 엔진
# ---------------------------------------------------------------------------

class DemoEngine:
    """
    실시간 가격 피드 기반 가상 선물 트레이딩 엔진.

    사용 흐름:
        session = DemoSession(session_id="abc", leverage=10, initial_balance=1000)
        engine  = DemoEngine(session, strategy_config={...})
        trade   = engine.on_price_update(price=95000.0, timestamp_ms=1_700_000_000_000)
    """

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
        self._sl_pct: float = float(sl_cfg.get("value", -0.4))   # 음수 기대
        self._partial_enabled: bool = bool(pe_cfg.get("enabled", False))
        self._partial_at_pct: float = float(pe_cfg.get("at_pct", pe_cfg.get("at_percent", 1.2)))
        self._partial_ratio: float = float(pe_cfg.get("ratio", pe_cfg.get("sell_ratio", 0.5)))
        self._trailing_enabled: bool = bool(ts_cfg.get("enabled", False))
        self._trailing_trigger: float = float(ts_cfg.get("trigger_pct", 0.9))
        self._trailing_callback: float = float(ts_cfg.get("callback_pct", 0.2))
        # 포지션 진입에 사용할 잔고 비율 (기본 전액)
        self._risk_ratio: float = float(pos_cfg.get("risk_ratio", 1.0))
        # 전략 방향: "long" | "short" | "both"
        self._direction: str = strategy_config.get("direction", "both")
        # 외부에서 직접 진입 신호를 전달하기 위한 플래그
        self._pending_signal: Optional[str] = None  # "long" | "short" | None

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------

    def signal(self, side: str) -> None:
        """외부(라우터/웹소켓)에서 진입 신호 주입."""
        if side in ("long", "short"):
            self._pending_signal = side

    def on_price_update(self, price: float, timestamp_ms: int) -> Optional[DemoTrade]:
        """
        새 가격 틱을 처리한다.

        처리 순서:
            1. 강제 청산 확인
            2. SL/TP 확인
            3. 트레일링 스탑 확인
            4. 분할 익절 확인
            5. 포지션 없으면 진입 신호 처리

        Returns:
            체결된 DemoTrade (청산 발생 시), 없으면 None
        """
        if self.session.status != "active":
            return None
        self.last_price = price

        pos = self.session.position

        if pos is not None:
            # 최고/최저가 갱신
            pos.highest_since_entry = max(pos.highest_since_entry, price)
            pos.lowest_since_entry = min(pos.lowest_since_entry, price)

            # 1. 강제 청산
            liq = self._calc_liquidation_price()
            if (pos.side == "long" and price <= liq) or \
               (pos.side == "short" and price >= liq):
                return self.close_position(liq, "liquidation", timestamp_ms)

            # 2. 손절 (SL)
            if pos.sl_price is not None:
                if (pos.side == "long" and price <= pos.sl_price) or \
                   (pos.side == "short" and price >= pos.sl_price):
                    return self.close_position(pos.sl_price, "sl", timestamp_ms)

            # 3. 익절 (TP)
            if pos.tp_price is not None:
                if (pos.side == "long" and price >= pos.tp_price) or \
                   (pos.side == "short" and price <= pos.tp_price):
                    return self.close_position(pos.tp_price, "tp", timestamp_ms)

            # 4. 트레일링 스탑
            if self._trailing_enabled and self._check_trailing(price):
                return self.close_position(price, "trailing", timestamp_ms)

            # 5. 분할 익절 (partial exit) — 포지션 수량만 줄이고 잔고 반영
            if self._partial_enabled and not pos.partial_exited:
                upnl_pct = self._calc_unrealized_pnl(price) / (
                    self.session.current_balance or 1
                ) * 100
                if upnl_pct >= self._partial_at_pct * pos.leverage:
                    self._execute_partial_exit(price, timestamp_ms)

            return None

        # 포지션 없음: 진입 신호 처리
        if self._pending_signal:
            side = self._pending_signal
            self._pending_signal = None
            self.open_position(side, price, timestamp_ms)
        return None

    def open_position(self, side: str, price: float, timestamp_ms: int) -> None:
        """
        신규 포지션 진입.

        기존 포지션이 있으면 반전(reversal) 진입을 수행한다:
        현재 포지션을 시장가로 청산 후 반대 방향으로 재진입.
        """
        # 기존 포지션 반전
        if self.session.position is not None:
            self.close_position(price, "reversal", timestamp_ms)

        # 수수료 차감
        commission = self.session.current_balance * _COMMISSION
        self.session.current_balance -= commission

        if self.session.current_balance <= 0:
            return

        # 수량 = (잔고 × 위험비율 / 진입가) × 레버리지
        qty = (self.session.current_balance * self._risk_ratio / price) * self.session.leverage

        # SL/TP 절대가격 계산 (백분율 → 절대가)
        sl_abs: Optional[float] = None
        tp_abs: Optional[float] = None
        if self._sl_pct != 0:
            ratio = abs(self._sl_pct) / (100 * self.session.leverage)
            sl_abs = price * (1 - ratio) if side == "long" else price * (1 + ratio)
        if self._tp_pct != 0:
            ratio = abs(self._tp_pct) / (100 * self.session.leverage)
            tp_abs = price * (1 + ratio) if side == "long" else price * (1 - ratio)

        self.session.position = DemoPosition(
            side=side,
            entry_price=price,
            quantity=qty,
            leverage=self.session.leverage,
            sl_price=sl_abs,
            tp_price=tp_abs,
            trailing_trigger=self._trailing_trigger if self._trailing_enabled else None,
            trailing_callback=self._trailing_callback if self._trailing_enabled else None,
            highest_since_entry=price,
            lowest_since_entry=price,
        )

    def close_position(
        self, price: float, reason: str, timestamp_ms: int
    ) -> Optional[DemoTrade]:
        """
        포지션 전량 청산.

        수수료 차감 후 실현 손익을 잔고에 반영하고
        DemoTrade 기록을 세션에 추가한다.
        """
        pos = self.session.position
        if pos is None:
            return None

        commission = abs(pos.quantity * price) * _COMMISSION
        pnl = self._calc_unrealized_pnl(price) - commission
        self.session.current_balance += pnl

        # 잔고가 0 이하면 계정 종료
        if self.session.current_balance <= 0:
            self.session.current_balance = 0.0
            self.session.status = "stopped"

        trade = DemoTrade(
            side=pos.side,
            entry_price=pos.entry_price,
            exit_price=price,
            quantity=pos.quantity,
            leverage=pos.leverage,
            pnl=round(pnl, 4),
            exit_reason=reason,
            entry_at=_iso(timestamp_ms - 1),   # 진입 시각: 편의상 틱-1ms
            exit_at=_iso(timestamp_ms),
        )
        self.session.trades.append(trade)
        self.session.position = None
        return trade

    def get_status(self, current_price: Optional[float] = None) -> dict:
        """현재 세션 상태 스냅샷 반환. current_price로 실시간 PnL 계산."""
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
        """
        강제 청산 가격 계산 (간이 공식).

        Long:  entry * (1 - 1/leverage + commission)
        Short: entry * (1 + 1/leverage - commission)
        """
        pos = self.session.position
        if pos is None:
            return 0.0
        margin_ratio = 1.0 / pos.leverage
        if pos.side == "long":
            return pos.entry_price * (1 - margin_ratio + _COMMISSION)
        return pos.entry_price * (1 + margin_ratio - _COMMISSION)

    def _calc_unrealized_pnl(self, current_price: float) -> float:
        """
        미실현 손익 (USDT 기준).

        Long:  quantity * (current_price - entry_price)
        Short: quantity * (entry_price - current_price)
        """
        pos = self.session.position
        if pos is None:
            return 0.0
        if pos.side == "long":
            return pos.quantity * (current_price - pos.entry_price)
        return pos.quantity * (pos.entry_price - current_price)

    def _check_trailing(self, price: float) -> bool:
        """트레일링 스탑 발동 여부 확인."""
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
        """
        분할 익절: 포지션 수량의 일부를 시장가에 청산하고 잔고에 반영.
        DemoTrade 기록을 남기되 포지션은 유지된다.
        """
        pos = self.session.position
        if pos is None:
            return

        exit_qty = pos.quantity * self._partial_ratio
        commission = abs(exit_qty * price) * _COMMISSION

        if pos.side == "long":
            partial_pnl = exit_qty * (price - pos.entry_price) - commission
        else:
            partial_pnl = exit_qty * (pos.entry_price - price) - commission

        self.session.current_balance += partial_pnl
        pos.quantity -= exit_qty
        pos.partial_exited = True

        # 분할 체결 기록
        trade = DemoTrade(
            side=pos.side,
            entry_price=pos.entry_price,
            exit_price=price,
            quantity=exit_qty,
            leverage=pos.leverage,
            pnl=round(partial_pnl, 4),
            exit_reason="partial",
            entry_at=_iso(timestamp_ms - 1),
            exit_at=_iso(timestamp_ms),
        )
        self.session.trades.append(trade)
