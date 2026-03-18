"""
Strategy signal evaluator.

Evaluates entry conditions from parsed strategy JSON against OHLCV bars.
Supports all indicators: RSI, MACD, EMA cross, Bollinger, Stochastic RSI, ATR, volume.
"""

from typing import List, Optional, Dict, Any

from .data_loader import OhlcvBar
from .indicators_base import RSI, EMA
from .indicators_advanced import MACD, BollingerBands, ATR, StochasticRSI


def evaluate_entry_signal(
    strategy: Dict[str, Any],
    bars: List[OhlcvBar],
) -> Optional[str]:
    """
    Evaluate strategy entry conditions against price bars.

    Args:
        strategy: Parsed strategy JSON with entry.conditions
        bars: Historical bars up to current point

    Returns:
        "long", "short", or None
    """
    entry = strategy.get("entry", {})
    conditions = entry.get("conditions", [])
    logic = entry.get("logic", "AND")

    if not conditions or len(bars) < 2:
        return None

    results = []
    for cond in conditions:
        result = _evaluate_condition(cond, bars)
        results.append(result)

    if not results:
        return None

    if logic == "AND":
        passed = all(r is not None for r in results)
    else:  # OR
        passed = any(r is not None for r in results)

    if not passed:
        return None

    # 방향 결정: 조건이 매수 성격이면 long, 매도 성격이면 short
    direction = strategy.get("direction", "long")
    if direction == "both":
        return _infer_direction(conditions, bars)
    return direction


def _evaluate_condition(cond: Dict[str, Any], bars: List[OhlcvBar]) -> Optional[bool]:
    """Evaluate single entry condition."""
    indicator = cond.get("indicator", "")
    operator = cond.get("operator", "<=")
    value = cond.get("value", 0)
    params = cond.get("params", {})

    current_value = _calculate_indicator(indicator, params, bars)
    if current_value is None:
        return None

    return _compare(current_value, operator, value)


def _calculate_indicator(
    indicator: str, params: Dict[str, Any], bars: List[OhlcvBar]
) -> Optional[float]:
    """Calculate indicator value from bars."""
    closes = [b.close for b in bars]

    if indicator == "rsi":
        period = params.get("period", 14)
        if len(closes) < period + 1:
            return None
        rsi = RSI(period)
        for c in closes:
            rsi.update(c)
        return rsi.value

    elif indicator in ("ma_cross", "ema_cross"):
        short_p = params.get("short_period", 7)
        long_p = params.get("long_period", 25)
        if len(closes) < long_p:
            return None
        short_ema = EMA(short_p)
        long_ema = EMA(long_p)
        for c in closes:
            short_ema.update(c)
            long_ema.update(c)
        return short_ema.value - long_ema.value  # positive = golden cross

    elif indicator == "macd":
        fp = params.get("fast_period", 12)
        sp = params.get("slow_period", 26)
        sig = params.get("signal_period", 9)
        if len(closes) < sp:
            return None
        macd = MACD(fp, sp, sig)
        for c in closes:
            macd.update(c)
        return macd.histogram

    elif indicator in ("bollinger_lower", "bollinger_upper"):
        period = params.get("period", 20)
        if len(closes) < period:
            return None
        bb = BollingerBands(period, params.get("std_dev", 2.0))
        for c in closes:
            bb.update(c)
        if indicator == "bollinger_lower":
            return closes[-1] - bb.lower  # negative = below lower band
        return closes[-1] - bb.upper

    elif indicator == "stoch_rsi":
        rp = params.get("rsi_period", 14)
        sp = params.get("stoch_period", 14)
        if len(closes) < rp + sp:
            return None
        srsi = StochasticRSI(rp, sp)
        for c in closes:
            srsi.update(c)
        return srsi.k_value

    elif indicator == "atr":
        period = params.get("period", 14)
        if len(bars) < period:
            return None
        atr = ATR(period)
        for b in bars:
            atr.update(b.high, b.low, b.close)
        return (atr.value / closes[-1]) * 100  # ATR as % of price

    elif indicator == "volume_change":
        if len(bars) < 2:
            return None
        prev_vol = bars[-2].volume
        return ((bars[-1].volume - prev_vol) / prev_vol * 100) if prev_vol > 0 else 0

    elif indicator == "price_change":
        if len(closes) < 2:
            return None
        return ((closes[-1] - closes[-2]) / closes[-2]) * 100

    return None


def _compare(actual: float, operator: str, expected: float) -> Optional[bool]:
    ops = {
        "<=": actual <= expected,
        ">=": actual >= expected,
        "<": actual < expected,
        ">": actual > expected,
        "==": abs(actual - expected) < 0.001,
    }
    return ops.get(operator)


def _infer_direction(conditions: list, bars: List[OhlcvBar]) -> str:
    """Infer long/short direction from indicator values."""
    # 기본: 가격이 상승 추세면 long, 하락이면 short
    if len(bars) >= 20:
        ema20 = EMA(20)
        for b in bars:
            ema20.update(b.close)
        return "long" if bars[-1].close > ema20.value else "short"
    return "long"
