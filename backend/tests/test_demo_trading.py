"""
Comprehensive pytest test suite for DemoEngine (services/demo_trading.py).

Coverage:
  - BUY_LONG / SELL_SHORT entry slippage and commission
  - SELL_LONG (TP) / BUY_SHORT (SL) exit signal_type and PnL
  - Trailing stop trigger and callback logic
  - Partial exit: quantity reduction, balance update, partial_exited flag
  - Reversal: BUY_LONG → SELL_SHORT closes old position, opens new one
  - Liquidation: forced close at calculated liquidation price
  - Fee calculation (qty * entry * 0.0004 + qty * exit * 0.0004)
  - PnL percentage formula: raw_pnl_pct - 0.08%  (BinanceTrader convention)
  - Edge cases: zero balance, duplicate signals, no-op when session stopped
"""

from __future__ import annotations

import pytest

from services.demo_trading import (
    DemoEngine,
    DemoSession,
    DemoTrade,
    SignalType,
    _COMMISSION,
    _SLIPPAGE,
    _apply_slippage,
)

# ---------------------------------------------------------------------------
# Constants (mirrors the module-level values)
# ---------------------------------------------------------------------------

_FEE_RATE = _COMMISSION          # 0.0004
_SLIP_RATE = _SLIPPAGE           # 0.0001
_FEE_PCT_BOTH = _FEE_RATE * 2 * 100   # 0.08 (양방향 수수료 %)


# ---------------------------------------------------------------------------
# Shared factory helper
# ---------------------------------------------------------------------------

def _make_engine(
    leverage: int = 10,
    balance: float = 1000.0,
    tp_pct: float = 7.5,
    sl_pct: float = -2.5,
    trailing_enabled: bool = False,
    trailing_trigger: float = 0.9,
    trailing_callback: float = 0.2,
    partial_enabled: bool = False,
    partial_at_pct: float = 1.2,
    partial_ratio: float = 0.5,
    direction: str = "both",
    risk_ratio: float = 1.0,
) -> DemoEngine:
    """Create a self-contained DemoEngine with sensible defaults."""
    strategy = {
        "exit": {
            "stop_loss": {"value": sl_pct},
            "take_profit": {"value": tp_pct},
            "trailing_stop": {
                "enabled": trailing_enabled,
                "trigger_pct": trailing_trigger,
                "callback_pct": trailing_callback,
            },
            "partial_exit": {
                "enabled": partial_enabled,
                "at_pct": partial_at_pct,
                "ratio": partial_ratio,
            },
        },
        "direction": direction,
        "position": {"risk_ratio": risk_ratio},
    }
    session = DemoSession(
        session_id="test",
        leverage=leverage,
        initial_balance=balance,
    )
    return DemoEngine(session, strategy)


def _ts(offset: int = 0) -> int:
    """Return a stable millisecond timestamp for deterministic test output."""
    return 1_700_000_000_000 + offset


# ---------------------------------------------------------------------------
# 1. BUY_LONG entry: slippage and commission
# ---------------------------------------------------------------------------

class TestBuyLongEntry:
    """BUY_LONG 진입 슬리피지·수수료 검증."""

    def test_entry_price_is_above_market_price(self) -> None:
        """롱 진입 시 슬리피지로 시장가보다 높은 체결가."""
        engine = _make_engine(leverage=10, balance=1000.0)
        market_price = 50_000.0

        engine.signal(SignalType.BUY_LONG)
        engine.on_price_update(market_price, _ts())

        pos = engine.session.position
        assert pos is not None
        expected_entry = market_price * (1 + _SLIP_RATE)
        assert pos.entry_price == pytest.approx(expected_entry)
        assert pos.entry_price > market_price

    def test_commission_deducted_from_balance_on_entry(self) -> None:
        """진입 수수료만큼 잔고가 감소해야 한다."""
        engine = _make_engine(leverage=10, balance=1000.0)
        market_price = 50_000.0
        initial_balance = engine.session.current_balance

        engine.signal(SignalType.BUY_LONG)
        engine.on_price_update(market_price, _ts())

        pos = engine.session.position
        assert pos is not None
        entry_fee = pos.quantity * pos.entry_price * _FEE_RATE
        assert engine.session.current_balance == pytest.approx(
            initial_balance - entry_fee, rel=1e-6
        )

    def test_position_side_is_long(self) -> None:
        """BUY_LONG 신호 후 포지션 사이드는 'long'이어야 한다."""
        engine = _make_engine()
        engine.signal(SignalType.BUY_LONG)
        engine.on_price_update(50_000.0, _ts())

        assert engine.session.position is not None
        assert engine.session.position.side == "long"

    def test_sl_and_tp_prices_calculated_correctly_for_long(self) -> None:
        """롱 포지션의 SL은 진입가 아래, TP는 진입가 위여야 한다."""
        engine = _make_engine(leverage=10, sl_pct=-2.5, tp_pct=7.5)
        engine.signal(SignalType.BUY_LONG)
        engine.on_price_update(50_000.0, _ts())

        pos = engine.session.position
        assert pos is not None
        assert pos.sl_price is not None
        assert pos.tp_price is not None
        assert pos.sl_price < pos.entry_price
        assert pos.tp_price > pos.entry_price

        # SL ratio: abs(-2.5) / (100 * 10) = 0.0025
        sl_ratio = 2.5 / (100 * 10)
        assert pos.sl_price == pytest.approx(pos.entry_price * (1 - sl_ratio))
        # TP ratio: 7.5 / (100 * 10) = 0.0075
        tp_ratio = 7.5 / (100 * 10)
        assert pos.tp_price == pytest.approx(pos.entry_price * (1 + tp_ratio))


# ---------------------------------------------------------------------------
# 2. SELL_SHORT entry: slippage and side
# ---------------------------------------------------------------------------

class TestSellShortEntry:
    """SELL_SHORT 진입 슬리피지·사이드 검증."""

    def test_entry_price_is_below_market_price(self) -> None:
        """숏 진입 시 슬리피지로 시장가보다 낮은 체결가."""
        engine = _make_engine(leverage=10, balance=1000.0)
        market_price = 50_000.0

        engine.signal(SignalType.SELL_SHORT)
        engine.on_price_update(market_price, _ts())

        pos = engine.session.position
        assert pos is not None
        expected_entry = market_price * (1 - _SLIP_RATE)
        assert pos.entry_price == pytest.approx(expected_entry)
        assert pos.entry_price < market_price

    def test_position_side_is_short(self) -> None:
        """SELL_SHORT 신호 후 포지션 사이드는 'short'이어야 한다."""
        engine = _make_engine()
        engine.signal(SignalType.SELL_SHORT)
        engine.on_price_update(50_000.0, _ts())

        assert engine.session.position is not None
        assert engine.session.position.side == "short"

    def test_sl_above_entry_for_short(self) -> None:
        """숏 포지션의 SL은 진입가 위여야 한다."""
        engine = _make_engine(leverage=10, sl_pct=-2.5, tp_pct=7.5)
        engine.signal(SignalType.SELL_SHORT)
        engine.on_price_update(50_000.0, _ts())

        pos = engine.session.position
        assert pos is not None
        assert pos.sl_price is not None
        assert pos.sl_price > pos.entry_price

    def test_tp_below_entry_for_short(self) -> None:
        """숏 포지션의 TP는 진입가 아래여야 한다."""
        engine = _make_engine(leverage=10, sl_pct=-2.5, tp_pct=7.5)
        engine.signal(SignalType.SELL_SHORT)
        engine.on_price_update(50_000.0, _ts())

        pos = engine.session.position
        assert pos is not None
        assert pos.tp_price is not None
        assert pos.tp_price < pos.entry_price


# ---------------------------------------------------------------------------
# 3. SELL_LONG exit (TP): signal_type, PnL formula
# ---------------------------------------------------------------------------

class TestSellLongExitTP:
    """TP 청산: signal_type, PnL 계산 검증."""

    def _open_long(self, engine: DemoEngine, price: float) -> None:
        engine.signal(SignalType.BUY_LONG)
        engine.on_price_update(price, _ts(0))

    def test_tp_trigger_produces_sell_long_signal_type(self) -> None:
        """TP 도달 시 DemoTrade.signal_type == 'SELL_LONG'."""
        engine = _make_engine(leverage=10, tp_pct=7.5)
        self._open_long(engine, 50_000.0)

        pos = engine.session.position
        assert pos is not None
        tp_price = pos.tp_price
        assert tp_price is not None

        trade = engine.on_price_update(tp_price + 1.0, _ts(1))

        assert trade is not None
        assert trade.signal_type == SignalType.SELL_LONG.value
        assert trade.exit_reason == "tp"

    def test_tp_pnl_positive_for_long(self) -> None:
        """롱 TP 청산 시 PnL은 양수여야 한다."""
        engine = _make_engine(leverage=10, tp_pct=7.5)
        self._open_long(engine, 50_000.0)

        pos = engine.session.position
        assert pos is not None
        trade = engine.on_price_update(pos.tp_price + 1.0, _ts(1))  # type: ignore[operator]

        assert trade is not None
        assert trade.pnl > 0
        assert trade.pnl_pct > 0

    def test_pnl_pct_formula_binancetrader(self) -> None:
        """PnL% = raw_pnl% - 0.08% (양방향 수수료 공제)."""
        engine = _make_engine(leverage=10, tp_pct=7.5)
        self._open_long(engine, 50_000.0)

        pos = engine.session.position
        assert pos is not None
        entry_price = pos.entry_price
        # 직접 TP 가격으로 청산 (reason="tp"이면 슬리피지 없음)
        tp_price = pos.tp_price
        assert tp_price is not None

        trade = engine.on_price_update(tp_price + 1.0, _ts(1))
        assert trade is not None

        raw_pnl_pct = (tp_price - entry_price) / entry_price * 10 * 100
        expected_pnl_pct = raw_pnl_pct - _FEE_PCT_BOTH
        assert trade.pnl_pct == pytest.approx(expected_pnl_pct, rel=1e-4)

    def test_balance_increases_on_tp(self) -> None:
        """TP 청산 후 잔고가 증가해야 한다."""
        engine = _make_engine(leverage=10, balance=1000.0, tp_pct=7.5)
        balance_after_entry: float
        self._open_long(engine, 50_000.0)
        balance_after_entry = engine.session.current_balance

        pos = engine.session.position
        assert pos is not None
        engine.on_price_update(pos.tp_price + 1.0, _ts(1))  # type: ignore[operator]

        assert engine.session.current_balance > balance_after_entry


# ---------------------------------------------------------------------------
# 4. BUY_SHORT exit (SL): negative PnL, signal_type
# ---------------------------------------------------------------------------

class TestBuyShortExitSL:
    """SL 청산: 음수 PnL, signal_type 검증."""

    def _open_short(self, engine: DemoEngine, price: float) -> None:
        engine.signal(SignalType.SELL_SHORT)
        engine.on_price_update(price, _ts(0))

    def test_sl_trigger_produces_buy_short_signal_type(self) -> None:
        """숏 SL 도달 시 DemoTrade.signal_type == 'BUY_SHORT'."""
        engine = _make_engine(leverage=10, sl_pct=-2.5)
        self._open_short(engine, 50_000.0)

        pos = engine.session.position
        assert pos is not None
        sl_price = pos.sl_price
        assert sl_price is not None

        trade = engine.on_price_update(sl_price + 1.0, _ts(1))

        assert trade is not None
        assert trade.signal_type == SignalType.BUY_SHORT.value
        assert trade.exit_reason == "sl"

    def test_sl_pnl_negative_for_short(self) -> None:
        """숏 SL 청산 시 PnL은 음수여야 한다."""
        engine = _make_engine(leverage=10, sl_pct=-2.5, tp_pct=99.0)
        self._open_short(engine, 50_000.0)

        pos = engine.session.position
        assert pos is not None
        # 가격이 SL 이상으로 상승 → 숏 SL 발동
        trade = engine.on_price_update(pos.sl_price + 1.0, _ts(1))  # type: ignore[operator]

        assert trade is not None
        assert trade.pnl < 0
        assert trade.pnl_pct < 0

    def test_long_sl_produces_sell_long_signal_type(self) -> None:
        """롱 SL 청산 시 signal_type == 'SELL_LONG'."""
        engine = _make_engine(leverage=10, sl_pct=-2.5, tp_pct=99.0)
        engine.signal(SignalType.BUY_LONG)
        engine.on_price_update(50_000.0, _ts(0))

        pos = engine.session.position
        assert pos is not None
        trade = engine.on_price_update(pos.sl_price - 1.0, _ts(1))  # type: ignore[operator]

        assert trade is not None
        assert trade.signal_type == SignalType.SELL_LONG.value
        assert trade.exit_reason == "sl"
        assert trade.pnl < 0


# ---------------------------------------------------------------------------
# 5. Trailing stop: trigger and callback
# ---------------------------------------------------------------------------

class TestTrailingStop:
    """트레일링 스탑 검증."""

    def test_trailing_stop_does_not_fire_before_trigger(self) -> None:
        """트레일링 트리거 미달 시 청산되지 않아야 한다."""
        # trigger_pct=0.9, callback_pct=0.2, leverage=10
        # effective_trigger_pct = 0.9 * 10 = 9.0%
        engine = _make_engine(
            leverage=10,
            sl_pct=0.0,
            tp_pct=0.0,
            trailing_enabled=True,
            trailing_trigger=0.9,
            trailing_callback=0.2,
        )
        engine.signal(SignalType.BUY_LONG)
        engine.on_price_update(50_000.0, _ts(0))

        # 수익률 8% (트리거 9% 미달)
        price_8pct = 50_000.0 * (1 + 0.08 / 10)
        trade = engine.on_price_update(price_8pct, _ts(1))
        assert trade is None
        assert engine.session.position is not None

    def test_trailing_stop_fires_after_trigger_and_callback(self) -> None:
        """트리거 도달 후 콜백% 하락 시 청산되어야 한다."""
        # trigger_pct=0.9, callback_pct=0.2, leverage=10
        # effective_trigger = 9.0%, effective_callback = 2.0%
        engine = _make_engine(
            leverage=10,
            sl_pct=0.0,
            tp_pct=0.0,
            trailing_enabled=True,
            trailing_trigger=0.9,
            trailing_callback=0.2,
        )
        engine.signal(SignalType.BUY_LONG)
        engine.on_price_update(50_000.0, _ts(0))

        pos = engine.session.position
        assert pos is not None
        entry = pos.entry_price

        # 트리거 충족: 10%/10(leverage) = 1% 상승
        peak_price = entry * (1 + 0.10 / 10)
        engine.on_price_update(peak_price, _ts(1))

        # peak PnL% = 10%, callback% = 2% → 현재 PnL이 8% 이하이면 청산
        # 현재가 = entry * (1 + 0.08/10)
        retraced_price = entry * (1 + 0.08 / 10)
        trade = engine.on_price_update(retraced_price, _ts(2))

        assert trade is not None
        assert trade.exit_reason == "trailing"

    def test_trailing_stop_exit_reason_is_trailing(self) -> None:
        """트레일링 스탑 청산 시 exit_reason == 'trailing'."""
        engine = _make_engine(
            leverage=10,
            sl_pct=0.0,
            tp_pct=0.0,
            trailing_enabled=True,
            trailing_trigger=0.5,
            trailing_callback=0.1,
        )
        engine.signal(SignalType.BUY_LONG)
        engine.on_price_update(50_000.0, _ts(0))

        pos = engine.session.position
        assert pos is not None
        entry = pos.entry_price

        # 강하게 상승
        high_price = entry * (1 + 0.07 / 10)
        engine.on_price_update(high_price, _ts(1))

        # 콜백 하락
        low_price = entry * (1 + 0.05 / 10)
        trade = engine.on_price_update(low_price, _ts(2))

        assert trade is not None
        assert trade.exit_reason == "trailing"


# ---------------------------------------------------------------------------
# 6. Partial exit
# ---------------------------------------------------------------------------

class TestPartialExit:
    """분할 익절 검증."""

    def _open_long_partial(self) -> DemoEngine:
        """분할 익절 활성화 엔진 + 롱 진입."""
        engine = _make_engine(
            leverage=10,
            balance=1000.0,
            tp_pct=99.0,   # 전체 TP는 매우 멀게
            sl_pct=-50.0,  # SL도 멀게
            partial_enabled=True,
            partial_at_pct=1.2,
            partial_ratio=0.5,
        )
        engine.signal(SignalType.BUY_LONG)
        engine.on_price_update(50_000.0, _ts(0))
        return engine

    def test_partial_exit_sets_partial_exited_flag(self) -> None:
        """분할 익절 후 position.partial_exited == True."""
        engine = self._open_long_partial()
        pos = engine.session.position
        assert pos is not None
        entry = pos.entry_price

        # partial_at_pct=1.2, leverage=10 → unrealized_pnl_pct >= 12%
        # price change = 12% / 10 / 100 * entry
        trigger_price = entry * (1 + 12.0 / (10 * 100))
        engine.on_price_update(trigger_price + 1.0, _ts(1))

        assert engine.session.position is not None
        assert engine.session.position.partial_exited is True

    def test_partial_exit_reduces_quantity(self) -> None:
        """분할 익절 후 포지션 수량이 절반으로 줄어야 한다."""
        engine = self._open_long_partial()
        pos = engine.session.position
        assert pos is not None
        original_qty = pos.quantity
        entry = pos.entry_price

        trigger_price = entry * (1 + 12.0 / (10 * 100))
        engine.on_price_update(trigger_price + 1.0, _ts(1))

        remaining_pos = engine.session.position
        assert remaining_pos is not None
        assert remaining_pos.quantity == pytest.approx(original_qty * 0.5, rel=1e-6)

    def test_partial_exit_trade_recorded(self) -> None:
        """분할 익절 시 거래 기록이 생성되어야 한다."""
        engine = self._open_long_partial()
        pos = engine.session.position
        assert pos is not None
        entry = pos.entry_price

        trigger_price = entry * (1 + 12.0 / (10 * 100))
        engine.on_price_update(trigger_price + 1.0, _ts(1))

        # partial exit는 DemoTrade를 on_price_update 반환값이 아닌 trades 리스트에 추가
        assert len(engine.session.trades) == 1
        partial_trade = engine.session.trades[0]
        assert partial_trade.exit_reason == "partial"

    def test_partial_exit_balance_increases(self) -> None:
        """분할 익절 후 잔고가 증가해야 한다 (수익 구간이므로)."""
        engine = self._open_long_partial()
        pos = engine.session.position
        assert pos is not None
        balance_after_entry = engine.session.current_balance
        entry = pos.entry_price

        trigger_price = entry * (1 + 12.0 / (10 * 100))
        engine.on_price_update(trigger_price + 1.0, _ts(1))

        assert engine.session.current_balance > balance_after_entry

    def test_partial_exit_does_not_fire_twice(self) -> None:
        """분할 익절은 한 번만 실행되어야 한다."""
        engine = self._open_long_partial()
        pos = engine.session.position
        assert pos is not None
        entry = pos.entry_price

        trigger_price = entry * (1 + 12.0 / (10 * 100))
        engine.on_price_update(trigger_price + 1.0, _ts(1))
        engine.on_price_update(trigger_price + 2.0, _ts(2))  # 두 번째 틱

        # 거래가 분할 1회만 기록되어야 함
        partial_trades = [t for t in engine.session.trades if t.exit_reason == "partial"]
        assert len(partial_trades) == 1


# ---------------------------------------------------------------------------
# 7. Reversal: BUY_LONG → SELL_SHORT
# ---------------------------------------------------------------------------

class TestReversal:
    """반전 신호 검증."""

    def test_reversal_closes_long_and_opens_short(self) -> None:
        """BUY_LONG 후 SELL_SHORT 신호 시 롱 청산 + 숏 진입."""
        engine = _make_engine(leverage=10, balance=1000.0, sl_pct=-50.0, tp_pct=99.0)

        # 롱 진입
        engine.signal(SignalType.BUY_LONG)
        engine.on_price_update(50_000.0, _ts(0))
        assert engine.session.position is not None
        assert engine.session.position.side == "long"

        # 반전 신호
        engine.signal(SignalType.SELL_SHORT)
        trade = engine.on_price_update(50_500.0, _ts(1))

        # 기존 롱 포지션이 청산되어 trade 반환
        assert trade is not None
        assert trade.exit_reason == "reversal"
        assert trade.signal_type == SignalType.SELL_LONG.value

        # 새 숏 포지션 생성
        assert engine.session.position is not None
        assert engine.session.position.side == "short"

    def test_reversal_trade_count(self) -> None:
        """반전 후 거래 기록이 1건(이전 포지션 청산)이어야 한다."""
        engine = _make_engine(leverage=10, balance=1000.0, sl_pct=-50.0, tp_pct=99.0)
        engine.signal(SignalType.BUY_LONG)
        engine.on_price_update(50_000.0, _ts(0))

        engine.signal(SignalType.SELL_SHORT)
        engine.on_price_update(50_500.0, _ts(1))

        assert len(engine.session.trades) == 1


# ---------------------------------------------------------------------------
# 8. Liquidation
# ---------------------------------------------------------------------------

class TestLiquidation:
    """강제 청산 검증."""

    def test_liquidation_price_formula_long(self) -> None:
        """롱 포지션 강제 청산 가격: entry * (1 - 1/leverage + commission)."""
        engine = _make_engine(leverage=10, balance=1000.0, sl_pct=0.0, tp_pct=0.0)
        entry_market = 50_000.0
        engine.signal(SignalType.BUY_LONG)
        engine.on_price_update(entry_market, _ts(0))

        pos = engine.session.position
        assert pos is not None
        expected_liq = pos.entry_price * (1 - 1.0 / 10 + _FEE_RATE)

        # 청산 가격 이하로 하락
        trade = engine.on_price_update(expected_liq - 1.0, _ts(1))

        assert trade is not None
        assert trade.exit_reason == "liquidation"

    def test_liquidation_price_formula_short(self) -> None:
        """숏 포지션 강제 청산 가격: entry * (1 + 1/leverage - commission)."""
        engine = _make_engine(leverage=10, balance=1000.0, sl_pct=0.0, tp_pct=0.0)
        engine.signal(SignalType.SELL_SHORT)
        engine.on_price_update(50_000.0, _ts(0))

        pos = engine.session.position
        assert pos is not None
        expected_liq = pos.entry_price * (1 + 1.0 / 10 - _FEE_RATE)

        trade = engine.on_price_update(expected_liq + 1.0, _ts(1))

        assert trade is not None
        assert trade.exit_reason == "liquidation"

    def test_liquidation_stops_session_when_balance_zeroed(self) -> None:
        """잔고가 0 이하로 떨어지면 세션이 'stopped' 상태가 된다."""
        # 레버리지를 매우 높게 설정하여 큰 손실 유발
        engine = _make_engine(leverage=100, balance=100.0, sl_pct=0.0, tp_pct=0.0)
        engine.signal(SignalType.BUY_LONG)
        engine.on_price_update(50_000.0, _ts(0))

        pos = engine.session.position
        assert pos is not None
        liq = pos.entry_price * (1 - 1.0 / 100 + _FEE_RATE)
        engine.on_price_update(liq - 1.0, _ts(1))

        assert engine.session.current_balance == 0.0
        assert engine.session.status == "stopped"


# ---------------------------------------------------------------------------
# 9. Fee calculation
# ---------------------------------------------------------------------------

class TestFeeCalculation:
    """수수료 계산 검증: fee = qty * entry * 0.0004 + qty * exit * 0.0004."""

    def test_fee_formula_on_full_close(self) -> None:
        """전량 청산 시 fee = qty * entry_price * 0.0004 + qty * exit_price * 0.0004."""
        engine = _make_engine(leverage=10, balance=1000.0, sl_pct=0.0, tp_pct=7.5)
        engine.signal(SignalType.BUY_LONG)
        engine.on_price_update(50_000.0, _ts(0))

        pos = engine.session.position
        assert pos is not None
        qty = pos.quantity
        entry_price = pos.entry_price
        tp_price = pos.tp_price
        assert tp_price is not None

        trade = engine.on_price_update(tp_price + 1.0, _ts(1))
        assert trade is not None

        expected_fee = qty * entry_price * _FEE_RATE + qty * tp_price * _FEE_RATE
        assert trade.fee == pytest.approx(expected_fee, rel=1e-4)

    def test_entry_fee_not_double_charged(self) -> None:
        """진입 시 차감된 수수료가 청산 fee 계산과 별개로 처리되는지 확인."""
        engine = _make_engine(leverage=10, balance=1000.0, sl_pct=0.0, tp_pct=7.5)
        balance_before_entry = engine.session.current_balance
        market_price = 50_000.0

        engine.signal(SignalType.BUY_LONG)
        engine.on_price_update(market_price, _ts(0))

        pos = engine.session.position
        assert pos is not None
        # 진입 수수료만큼 차감 검증
        entry_fee = pos.quantity * pos.entry_price * _FEE_RATE
        assert engine.session.current_balance == pytest.approx(
            balance_before_entry - entry_fee, rel=1e-6
        )


# ---------------------------------------------------------------------------
# 10. PnL percentage formula
# ---------------------------------------------------------------------------

class TestPnlPercentage:
    """PnL% = raw_pnl% - 0.08% (BinanceTrader 방식) 검증."""

    def test_pnl_pct_equals_raw_minus_fee_pct_long_tp(self) -> None:
        """롱 TP: pnl_pct = (exit-entry)/entry * lev * 100 - 0.08."""
        engine = _make_engine(leverage=10, balance=1000.0, sl_pct=0.0, tp_pct=7.5)
        engine.signal(SignalType.BUY_LONG)
        engine.on_price_update(50_000.0, _ts(0))

        pos = engine.session.position
        assert pos is not None
        entry = pos.entry_price
        tp = pos.tp_price
        assert tp is not None

        trade = engine.on_price_update(tp + 1.0, _ts(1))
        assert trade is not None

        raw_pct = (tp - entry) / entry * 10 * 100
        expected = raw_pct - _FEE_PCT_BOTH
        assert trade.pnl_pct == pytest.approx(expected, rel=1e-4)

    def test_pnl_pct_equals_raw_minus_fee_pct_short_sl(self) -> None:
        """숏 SL: pnl_pct = (entry-exit)/entry * lev * 100 - 0.08."""
        engine = _make_engine(leverage=10, balance=1000.0, sl_pct=-2.5, tp_pct=99.0)
        engine.signal(SignalType.SELL_SHORT)
        engine.on_price_update(50_000.0, _ts(0))

        pos = engine.session.position
        assert pos is not None
        entry = pos.entry_price
        sl = pos.sl_price
        assert sl is not None

        trade = engine.on_price_update(sl + 1.0, _ts(1))
        assert trade is not None

        # SL reason → exit_price == sl_price (no slippage)
        raw_pct = (entry - sl) / entry * 10 * 100
        expected = raw_pct - _FEE_PCT_BOTH
        assert trade.pnl_pct == pytest.approx(expected, rel=1e-4)

    def test_pnl_amount_consistent_with_pnl_pct(self) -> None:
        """pnl (금액) = margin * pnl_pct / 100."""
        engine = _make_engine(leverage=10, balance=1000.0, sl_pct=0.0, tp_pct=7.5)
        engine.signal(SignalType.BUY_LONG)
        engine.on_price_update(50_000.0, _ts(0))

        pos = engine.session.position
        assert pos is not None
        margin = pos.margin
        tp = pos.tp_price
        assert tp is not None

        trade = engine.on_price_update(tp + 1.0, _ts(1))
        assert trade is not None

        expected_pnl = margin * trade.pnl_pct / 100
        assert trade.pnl == pytest.approx(expected_pnl, rel=1e-4)


# ---------------------------------------------------------------------------
# 11. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """엣지 케이스 및 방어 로직 검증."""

    def test_no_position_opened_when_balance_is_zero(self) -> None:
        """잔고가 0일 때 진입 신호를 받아도 포지션이 생성되지 않아야 한다."""
        engine = _make_engine(balance=0.0)
        engine.signal(SignalType.BUY_LONG)
        engine.on_price_update(50_000.0, _ts(0))
        assert engine.session.position is None

    def test_stopped_session_ignores_price_updates(self) -> None:
        """세션이 'stopped'이면 가격 업데이트를 무시해야 한다."""
        engine = _make_engine(leverage=10, balance=1000.0, sl_pct=0.0, tp_pct=0.0)
        engine.session.status = "stopped"

        engine.signal(SignalType.BUY_LONG)
        result = engine.on_price_update(50_000.0, _ts(0))

        assert result is None
        assert engine.session.position is None

    def test_invalid_signal_is_ignored(self) -> None:
        """유효하지 않은 신호는 무시되어야 한다."""
        engine = _make_engine()
        engine.signal("INVALID_SIGNAL")
        engine.on_price_update(50_000.0, _ts(0))
        assert engine.session.position is None

    def test_duplicate_buy_long_signal_does_not_open_second_position(self) -> None:
        """포지션이 열린 상태에서 BUY_LONG 신호를 받아도 추가 진입 없음."""
        engine = _make_engine(sl_pct=-50.0, tp_pct=99.0)
        engine.signal(SignalType.BUY_LONG)
        engine.on_price_update(50_000.0, _ts(0))

        qty_after_first = engine.session.position.quantity  # type: ignore[union-attr]

        engine.signal(SignalType.BUY_LONG)
        engine.on_price_update(50_000.0, _ts(1))

        # 수량이 변하지 않아야 함 (새 포지션 미생성)
        assert engine.session.position is not None
        assert engine.session.position.quantity == pytest.approx(qty_after_first)

    def test_get_status_returns_none_position_when_no_position(self) -> None:
        """포지션 없을 때 get_status()의 'position' 키는 None이어야 한다."""
        engine = _make_engine()
        status = engine.get_status(current_price=50_000.0)
        assert status["position"] is None

    def test_get_status_reflects_open_position(self) -> None:
        """포지션 열린 후 get_status()에 올바른 side가 반영되어야 한다."""
        engine = _make_engine(sl_pct=-50.0, tp_pct=99.0)
        engine.signal(SignalType.BUY_LONG)
        engine.on_price_update(50_000.0, _ts(0))

        status = engine.get_status(current_price=50_000.0)
        assert status["position"] is not None
        assert status["position"]["side"] == "long"

    def test_apply_slippage_helper_long_entry(self) -> None:
        """_apply_slippage: 롱 진입 → price * (1 + slippage)."""
        result = _apply_slippage(50_000.0, "long", is_entry=True)
        assert result == pytest.approx(50_000.0 * (1 + _SLIP_RATE))

    def test_apply_slippage_helper_short_entry(self) -> None:
        """_apply_slippage: 숏 진입 → price * (1 - slippage)."""
        result = _apply_slippage(50_000.0, "short", is_entry=True)
        assert result == pytest.approx(50_000.0 * (1 - _SLIP_RATE))

    def test_apply_slippage_helper_long_exit(self) -> None:
        """_apply_slippage: 롱 청산 → price * (1 - slippage)."""
        result = _apply_slippage(50_000.0, "long", is_entry=False)
        assert result == pytest.approx(50_000.0 * (1 - _SLIP_RATE))

    def test_apply_slippage_helper_short_exit(self) -> None:
        """_apply_slippage: 숏 청산 → price * (1 + slippage)."""
        result = _apply_slippage(50_000.0, "short", is_entry=False)
        assert result == pytest.approx(50_000.0 * (1 + _SLIP_RATE))


# ---------------------------------------------------------------------------
# 12. Quantity and leverage consistency
# ---------------------------------------------------------------------------

class TestQuantityAndLeverage:
    """수량 / 레버리지 일관성 검증."""

    def test_quantity_formula(self) -> None:
        """qty = (balance * risk_ratio / entry_price) * leverage."""
        leverage = 10
        balance = 1000.0
        market_price = 50_000.0
        engine = _make_engine(leverage=leverage, balance=balance, risk_ratio=1.0)

        engine.signal(SignalType.BUY_LONG)
        engine.on_price_update(market_price, _ts(0))

        pos = engine.session.position
        assert pos is not None
        entry = pos.entry_price  # 슬리피지 포함 가격
        expected_qty = (balance / entry) * leverage
        assert pos.quantity == pytest.approx(expected_qty, rel=1e-6)

    def test_leverage_stored_on_position(self) -> None:
        """포지션에 세션 레버리지가 그대로 저장되어야 한다."""
        engine = _make_engine(leverage=20)
        engine.signal(SignalType.BUY_LONG)
        engine.on_price_update(50_000.0, _ts(0))

        assert engine.session.position is not None
        assert engine.session.position.leverage == 20
