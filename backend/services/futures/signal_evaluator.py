"""
Strategy signal evaluator.

Evaluates entry conditions from parsed strategy JSON against OHLCV bars.
Supports ALL indicators defined in strategy_parser.py:
  - Trend: rsi, ema_cross, ma_cross, macd, macd_hist, adx, di_plus, di_minus,
           sar, aroon_up, aroon_down, ema_N, sma_N
  - Momentum: cci, mom, roc, willr, mfi, apo, ppo, stoch_rsi
  - Volatility: bollinger_lower, bollinger_upper, bollinger_middle, atr
  - Volume: volume_change, price_change, vwap, obv, ad, adosc
  - DDIF: ddif, maddif
"""

from typing import List, Optional, Dict, Any

from .data_loader import OhlcvBar
from .indicators_base import RSI, EMA, SMA
from .indicators_advanced import MACD, BollingerBands, ATR, StochasticRSI


def evaluate_entry_signal(
    strategy: Dict[str, Any],
    bars: List[OhlcvBar],
) -> Optional[str]:
    """
    Evaluate strategy entry conditions against price bars.

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
        passed = all(r is True for r in results)
    else:  # OR
        passed = any(r is True for r in results)

    direction = strategy.get("direction", "both")

    if direction == "both":
        # 양방향 모드: 조건 충족 → long, 조건 반전 → short
        if passed:
            return "long"
        # 조건 반전 체크 — 모든 조건의 operator를 뒤집어서 평가
        reversed_results = []
        for cond in conditions:
            result = _evaluate_condition_reversed(cond, bars)
            reversed_results.append(result)
        if logic == "AND":
            reversed_passed = all(r is True for r in reversed_results)
        else:
            reversed_passed = any(r is True for r in reversed_results)
        if reversed_passed:
            return "short"
        return None
    else:
        # 단방향 모드: 조건 충족 시에만 해당 방향
        if not passed:
            return None
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
    """Calculate indicator value from bars. Supports all strategy_parser indicators."""
    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    volumes = [b.volume for b in bars]
    n = len(bars)

    # ── RSI ──
    if indicator == "rsi":
        period = params.get("period", 14)
        if n < period + 1:
            return None
        rsi = RSI(period)
        for c in closes:
            rsi.update(c)
        return rsi.value

    # ── EMA/MA Cross ──
    elif indicator in ("ma_cross", "ema_cross"):
        short_p = params.get("short_period", 7)
        long_p = params.get("long_period", 25)
        if n < long_p:
            return None
        short_ema = EMA(short_p)
        long_ema = EMA(long_p)
        for c in closes:
            short_ema.update(c)
            long_ema.update(c)
        return short_ema.value - long_ema.value  # positive = golden cross

    # ── MACD (histogram) ──
    elif indicator in ("macd", "macd_hist"):
        fp = params.get("fast_period", 12)
        sp = params.get("slow_period", 26)
        sig = params.get("signal_period", 9)
        if n < sp:
            return None
        macd = MACD(fp, sp, sig)
        for c in closes:
            macd.update(c)
        return macd.histogram

    # ── Bollinger Bands ──
    elif indicator in ("bollinger_lower", "bollinger_upper", "bollinger_middle"):
        period = params.get("period", 20)
        if n < period:
            return None
        bb = BollingerBands(period, params.get("std_dev", 2.0))
        for c in closes:
            bb.update(c)
        if indicator == "bollinger_lower":
            return closes[-1] - bb.lower  # negative = below lower band
        elif indicator == "bollinger_middle":
            return closes[-1] - bb.middle
        return closes[-1] - bb.upper

    # ── Stochastic RSI ──
    elif indicator == "stoch_rsi":
        rp = params.get("rsi_period", 14)
        sp = params.get("stoch_period", 14)
        if n < rp + sp:
            return None
        srsi = StochasticRSI(rp, sp)
        for c in closes:
            srsi.update(c)
        return srsi.k_value

    # ── ATR (as % of price) ──
    elif indicator == "atr":
        period = params.get("period", 14)
        if n < period:
            return None
        atr = ATR(period)
        for b in bars:
            atr.update(b.high, b.low, b.close)
        return (atr.value / closes[-1]) * 100

    # ── Volume Change (%) ──
    elif indicator == "volume_change":
        if n < 2:
            return None
        prev_vol = bars[-2].volume
        return ((bars[-1].volume - prev_vol) / prev_vol * 100) if prev_vol > 0 else 0

    # ── Price Change (%) ──
    elif indicator == "price_change":
        if n < 2:
            return None
        return ((closes[-1] - closes[-2]) / closes[-2]) * 100

    # ── ADX (Average Directional Index) ──
    elif indicator == "adx":
        period = params.get("period", 14)
        if n < period * 2:
            return None
        dx_values = _calc_dx_series(highs, lows, closes, period)
        if not dx_values:
            return None
        # ADX = smoothed average of DX
        adx_val = sum(dx_values[-period:]) / min(len(dx_values), period)
        return adx_val

    # ── DI+ / DI- ──
    elif indicator == "di_plus":
        period = params.get("period", 14)
        if n < period + 1:
            return None
        return _calc_di(highs, lows, closes, period, plus=True)

    elif indicator == "di_minus":
        period = params.get("period", 14)
        if n < period + 1:
            return None
        return _calc_di(highs, lows, closes, period, plus=False)

    # ── DDIF (DI+ - DI-) ──
    elif indicator == "ddif":
        period = params.get("period", 14)
        if n < period + 1:
            return None
        di_p = _calc_di(highs, lows, closes, period, plus=True)
        di_m = _calc_di(highs, lows, closes, period, plus=False)
        if di_p is None or di_m is None:
            return None
        return di_p - di_m

    # ── MADDIF (EMA of DDIF) ──
    elif indicator == "maddif":
        period = params.get("period", 14)
        ema_period = params.get("ema_period", 5)
        if n < period + ema_period:
            return None
        ddif_series = _calc_ddif_series(highs, lows, closes, period)
        if len(ddif_series) < ema_period:
            return None
        ema = EMA(ema_period)
        for d in ddif_series:
            ema.update(d)
        return ema.value

    # ── Parabolic SAR ──
    elif indicator == "sar":
        accel = params.get("acceleration", 0.02)
        maximum = params.get("maximum", 0.20)
        if n < 3:
            return None
        sar_val = _calc_sar(highs, lows, closes, accel, maximum)
        # 가격 - SAR: positive = 상승 추세 (SAR이 가격 아래)
        return closes[-1] - sar_val

    # ── Aroon Up / Down ──
    elif indicator == "aroon_up":
        period = params.get("period", 25)
        if n < period + 1:
            return None
        recent_highs = highs[-(period + 1):]
        bars_since_high = period - recent_highs.index(max(recent_highs))
        return (bars_since_high / period) * 100

    elif indicator == "aroon_down":
        period = params.get("period", 25)
        if n < period + 1:
            return None
        recent_lows = lows[-(period + 1):]
        bars_since_low = period - recent_lows.index(min(recent_lows))
        return (bars_since_low / period) * 100

    # ── CCI (Commodity Channel Index) ──
    elif indicator == "cci":
        period = params.get("period", 14)
        if n < period:
            return None
        typical_prices = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
        tp_slice = typical_prices[-period:]
        tp_mean = sum(tp_slice) / period
        mean_dev = sum(abs(tp - tp_mean) for tp in tp_slice) / period
        if mean_dev == 0:
            return 0.0
        return (typical_prices[-1] - tp_mean) / (0.015 * mean_dev)

    # ── Momentum ──
    elif indicator == "mom":
        period = params.get("period", 10)
        if n < period + 1:
            return None
        return closes[-1] - closes[-(period + 1)]

    # ── Rate of Change (%) ──
    elif indicator == "roc":
        period = params.get("period", 10)
        if n < period + 1:
            return None
        prev = closes[-(period + 1)]
        return ((closes[-1] - prev) / prev) * 100 if prev != 0 else 0

    # ── Williams %R ──
    elif indicator == "willr":
        period = params.get("period", 14)
        if n < period:
            return None
        highest = max(highs[-period:])
        lowest = min(lows[-period:])
        rng = highest - lowest
        if rng == 0:
            return -50.0
        return ((highest - closes[-1]) / rng) * -100

    # ── MFI (Money Flow Index) ──
    elif indicator == "mfi":
        period = params.get("period", 14)
        if n < period + 1:
            return None
        tp = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
        pos_flow = 0.0
        neg_flow = 0.0
        for i in range(-period, 0):
            mf = tp[i] * volumes[i]
            if tp[i] > tp[i - 1]:
                pos_flow += mf
            elif tp[i] < tp[i - 1]:
                neg_flow += mf
        if neg_flow == 0:
            return 100.0
        mfr = pos_flow / neg_flow
        return 100 - (100 / (1 + mfr))

    # ── APO (Absolute Price Oscillator) ──
    elif indicator == "apo":
        fp = params.get("fast_period", 12)
        sp = params.get("slow_period", 26)
        if n < sp:
            return None
        fast_ema = EMA(fp)
        slow_ema = EMA(sp)
        for c in closes:
            fast_ema.update(c)
            slow_ema.update(c)
        return fast_ema.value - slow_ema.value

    # ── PPO (Percentage Price Oscillator) ──
    elif indicator == "ppo":
        fp = params.get("fast_period", 12)
        sp = params.get("slow_period", 26)
        if n < sp:
            return None
        fast_ema = EMA(fp)
        slow_ema = EMA(sp)
        for c in closes:
            fast_ema.update(c)
            slow_ema.update(c)
        if slow_ema.value == 0:
            return 0.0
        return ((fast_ema.value - slow_ema.value) / slow_ema.value) * 100

    # ── VWAP (Volume Weighted Average Price) ──
    elif indicator in ("vwap", "vwap_above", "vwap_below"):
        if n < 2 or sum(volumes) == 0:
            return None
        tp_vol_sum = sum((h + l + c) / 3 * v for h, l, c, v in zip(highs, lows, closes, volumes))
        vol_sum = sum(volumes)
        vwap_val = tp_vol_sum / vol_sum
        return closes[-1] - vwap_val  # positive = price above VWAP

    # ── OBV (On-Balance Volume) ──
    elif indicator == "obv":
        if n < 2:
            return None
        obv_val = 0.0
        for i in range(1, n):
            if closes[i] > closes[i - 1]:
                obv_val += volumes[i]
            elif closes[i] < closes[i - 1]:
                obv_val -= volumes[i]
        # OBV 자체는 스케일이 커서, 변화율로 반환
        prev_obv = 0.0
        for i in range(1, n - 1):
            if closes[i] > closes[i - 1]:
                prev_obv += volumes[i]
            elif closes[i] < closes[i - 1]:
                prev_obv -= volumes[i]
        if prev_obv == 0:
            return 0.0
        return ((obv_val - prev_obv) / abs(prev_obv)) * 100 if prev_obv != 0 else 0

    # ── AD (Accumulation/Distribution) ──
    elif indicator == "ad":
        if n < 2:
            return None
        ad_val = 0.0
        for i in range(n):
            rng = highs[i] - lows[i]
            if rng > 0:
                clv = ((closes[i] - lows[i]) - (highs[i] - closes[i])) / rng
                ad_val += clv * volumes[i]
        # 변화율 반환
        prev_ad = 0.0
        for i in range(n - 1):
            rng = highs[i] - lows[i]
            if rng > 0:
                clv = ((closes[i] - lows[i]) - (highs[i] - closes[i])) / rng
                prev_ad += clv * volumes[i]
        return ad_val - prev_ad

    # ── ADOSC (Chaikin A/D Oscillator) ──
    elif indicator == "adosc":
        fp = params.get("fast_period", 3)
        sp = params.get("slow_period", 10)
        if n < sp:
            return None
        ad_series = []
        cumulative = 0.0
        for i in range(n):
            rng = highs[i] - lows[i]
            if rng > 0:
                clv = ((closes[i] - lows[i]) - (highs[i] - closes[i])) / rng
                cumulative += clv * volumes[i]
            ad_series.append(cumulative)
        fast_ema = EMA(fp)
        slow_ema = EMA(sp)
        for ad_v in ad_series:
            fast_ema.update(ad_v)
            slow_ema.update(ad_v)
        return fast_ema.value - slow_ema.value

    # ── ema_N 패턴 (ema_60, ema_120 등): close - EMA(N) ──
    elif indicator.startswith("ema_") and indicator[4:].isdigit():
        period = int(indicator[4:])
        if n < period:
            return None
        ema = EMA(period)
        for c in closes:
            ema.update(c)
        return closes[-1] - ema.value  # positive = price above EMA

    # ── sma_N 패턴 (sma_60 등): close - SMA(N) ──
    elif indicator.startswith("sma_") and indicator[4:].isdigit():
        period = int(indicator[4:])
        if n < period:
            return None
        sma_val = sum(closes[-period:]) / period
        return closes[-1] - sma_val  # positive = price above SMA

    return None


# ── Helper: DI+/DI- 계산 ──
def _calc_di(
    highs: list, lows: list, closes: list, period: int, plus: bool
) -> Optional[float]:
    """Calculate +DI or -DI using Wilder smoothing."""
    n = len(closes)
    if n < period + 1:
        return None

    dm_sum = 0.0
    tr_sum = 0.0
    for i in range(1, period + 1):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        if plus:
            dm = up if (up > down and up > 0) else 0
        else:
            dm = down if (down > up and down > 0) else 0
        dm_sum += dm
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        tr_sum += tr

    # Wilder smoothing
    for i in range(period + 1, n):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        if plus:
            dm = up if (up > down and up > 0) else 0
        else:
            dm = down if (down > up and down > 0) else 0
        dm_sum = dm_sum - (dm_sum / period) + dm
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        tr_sum = tr_sum - (tr_sum / period) + tr

    if tr_sum == 0:
        return 0.0
    return (dm_sum / tr_sum) * 100


def _calc_dx_series(
    highs: list, lows: list, closes: list, period: int
) -> list:
    """Calculate DX series for ADX computation."""
    n = len(closes)
    if n < period + 1:
        return []

    dx_values = []
    dm_plus_sum = 0.0
    dm_minus_sum = 0.0
    tr_sum = 0.0

    for i in range(1, period + 1):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        dm_plus = up if (up > down and up > 0) else 0
        dm_minus = down if (down > up and down > 0) else 0
        dm_plus_sum += dm_plus
        dm_minus_sum += dm_minus
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        tr_sum += tr

    if tr_sum > 0:
        di_p = (dm_plus_sum / tr_sum) * 100
        di_m = (dm_minus_sum / tr_sum) * 100
        di_sum = di_p + di_m
        dx_values.append(abs(di_p - di_m) / di_sum * 100 if di_sum > 0 else 0)

    for i in range(period + 1, n):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        dm_plus = up if (up > down and up > 0) else 0
        dm_minus = down if (down > up and down > 0) else 0
        dm_plus_sum = dm_plus_sum - (dm_plus_sum / period) + dm_plus
        dm_minus_sum = dm_minus_sum - (dm_minus_sum / period) + dm_minus
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        tr_sum = tr_sum - (tr_sum / period) + tr
        if tr_sum > 0:
            di_p = (dm_plus_sum / tr_sum) * 100
            di_m = (dm_minus_sum / tr_sum) * 100
            di_sum = di_p + di_m
            dx_values.append(abs(di_p - di_m) / di_sum * 100 if di_sum > 0 else 0)

    return dx_values


def _calc_ddif_series(
    highs: list, lows: list, closes: list, period: int
) -> list:
    """Calculate DDIF (DI+ - DI-) series."""
    n = len(closes)
    if n < period + 1:
        return []

    ddif_values = []
    dm_plus_sum = 0.0
    dm_minus_sum = 0.0
    tr_sum = 0.0

    for i in range(1, period + 1):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        dm_plus = up if (up > down and up > 0) else 0
        dm_minus = down if (down > up and down > 0) else 0
        dm_plus_sum += dm_plus
        dm_minus_sum += dm_minus
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        tr_sum += tr

    if tr_sum > 0:
        di_p = (dm_plus_sum / tr_sum) * 100
        di_m = (dm_minus_sum / tr_sum) * 100
        ddif_values.append(di_p - di_m)

    for i in range(period + 1, n):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        dm_plus = up if (up > down and up > 0) else 0
        dm_minus = down if (down > up and down > 0) else 0
        dm_plus_sum = dm_plus_sum - (dm_plus_sum / period) + dm_plus
        dm_minus_sum = dm_minus_sum - (dm_minus_sum / period) + dm_minus
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        tr_sum = tr_sum - (tr_sum / period) + tr
        if tr_sum > 0:
            di_p = (dm_plus_sum / tr_sum) * 100
            di_m = (dm_minus_sum / tr_sum) * 100
            ddif_values.append(di_p - di_m)

    return ddif_values


def _calc_sar(
    highs: list, lows: list, closes: list,
    accel: float, maximum: float,
) -> float:
    """Calculate Parabolic SAR and return last value."""
    n = len(closes)
    is_long = closes[1] > closes[0]
    sar = lows[0] if is_long else highs[0]
    ep = highs[1] if is_long else lows[1]
    af = accel

    for i in range(2, n):
        sar = sar + af * (ep - sar)

        if is_long:
            sar = min(sar, lows[i - 1], lows[i - 2])
            if highs[i] > ep:
                ep = highs[i]
                af = min(af + accel, maximum)
            if lows[i] < sar:
                is_long = False
                sar = ep
                ep = lows[i]
                af = accel
        else:
            sar = max(sar, highs[i - 1], highs[i - 2])
            if lows[i] < ep:
                ep = lows[i]
                af = min(af + accel, maximum)
            if highs[i] > sar:
                is_long = True
                sar = ep
                ep = highs[i]
                af = accel

    return sar


def _compare(actual: float, operator: str, expected: float) -> Optional[bool]:
    ops = {
        "<=": actual <= expected,
        ">=": actual >= expected,
        "<": actual < expected,
        ">": actual > expected,
        "==": abs(actual - expected) < 0.001,
    }
    return ops.get(operator)


def _evaluate_condition_reversed(cond: Dict[str, Any], bars: List[OhlcvBar]) -> Optional[bool]:
    """Evaluate condition with smart reversal for short signals.

    방향성 지표 (ema_cross, ema_60 등): operator만 반전 (> → <)
    범위 지표 (RSI 0-100, Williams %R -100~0 등): operator + value 미러링
    """
    indicator = cond.get("indicator", "")
    operator = cond.get("operator", "<=")
    value = cond.get("value", 0)
    params = cond.get("params", {})

    reverse_op_map = {">": "<", "<": ">", ">=": "<=", "<=": ">=", "==": "=="}
    reversed_op = reverse_op_map.get(operator, operator)

    # RSI 계열 (0-100 범위): value 미러링 (100 - value)
    _RSI_BOUNDED = {"rsi", "stoch_rsi", "mfi"}
    # Williams %R (-100 ~ 0): value 미러링 (-100 - value)
    _WILLR_BOUNDED = {"willr"}
    # Aroon (0-100): value 미러링 (100 - value)
    _AROON = {"aroon_up", "aroon_down"}

    # 비방향성 필터 (반전 불필요 — 롱/숏 모두 동일 조건 적용)
    _NO_REVERSE = {"adx", "atr", "volume_change"}

    if indicator in _NO_REVERSE:
        # 추세 강도, 변동성, 거래량 필터 — 방향 무관
        reversed_op = operator
        reversed_value = value
    elif indicator in _RSI_BOUNDED:
        reversed_value = 100 - value  # rsi < 70 → rsi > 30
    elif indicator in _WILLR_BOUNDED:
        reversed_value = -100 - value  # willr < -80 → willr > -20
    elif indicator in _AROON:
        reversed_value = 100 - value
        # aroon_up ↔ aroon_down 교체
        if indicator == "aroon_up":
            indicator = "aroon_down"
        elif indicator == "aroon_down":
            indicator = "aroon_up"
    elif indicator == "cci":
        reversed_value = -value  # cci > 100 → cci < -100
    elif indicator in ("bollinger_lower", "bollinger_upper", "bollinger_middle"):
        # 볼린저 하단 터치(매수) ↔ 상단 터치(매도)
        if indicator == "bollinger_lower":
            indicator = "bollinger_upper"
        elif indicator == "bollinger_upper":
            indicator = "bollinger_lower"
        # bollinger_middle은 그대로 operator만 반전
        reversed_value = value
    elif indicator == "sar":
        # SAR: close - SAR → 부호 반전 = operator 반전만 (이미 됨)
        reversed_value = value
    else:
        # 방향성 지표 (ema_cross, macd, ddif, ema_N, sma_N, mom, roc, apo, ppo, obv, ad, adosc, price_change, vwap):
        # operator만 반전, value 유지
        reversed_value = value

    current_value = _calculate_indicator(indicator, params, bars)
    if current_value is None:
        return None

    return _compare(current_value, reversed_op, reversed_value)


def evaluate_exit_signal(
    strategy: Dict[str, Any],
    bars: List[OhlcvBar],
    position_side: str,
) -> Optional[str]:
    """
    Evaluate strategy exit conditions against price bars.

    Args:
        strategy: parsed strategy with optional exit_conditions
        bars: OHLCV price bars
        position_side: "long" or "short"

    Returns:
        "SELL_LONG", "BUY_SHORT", or None
    """
    exit_conds = strategy.get("exit_conditions", strategy.get("exit", {}).get("conditions", []))
    if not exit_conds:
        return None

    # exit_conditions가 dict 형태면 conditions 배열 추출
    if isinstance(exit_conds, dict):
        exit_conds = exit_conds.get("conditions", [])

    if not exit_conds or len(bars) < 2:
        return None

    logic = "AND"
    if isinstance(strategy.get("exit_conditions"), dict):
        logic = strategy["exit_conditions"].get("logic", "AND")

    results = []
    for cond in exit_conds:
        result = _evaluate_condition(cond, bars)
        results.append(result)

    if not results:
        return None

    if logic == "AND":
        passed = all(r is True for r in results)
    else:
        passed = any(r is True for r in results)

    if not passed:
        return None

    if position_side == "long":
        return "SELL_LONG"
    return "BUY_SHORT"
