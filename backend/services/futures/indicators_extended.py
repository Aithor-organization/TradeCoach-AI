"""
Extended technical indicators — 25 additional indicators using pure NumPy.

All functions accept OHLCV data as a 2-D NumPy array with columns:
    [open, high, low, close, volume]  (shape: N × 5)

or individual 1-D arrays where documented, and return a 1-D NumPy array
of the same length N.  Warmup values that cannot be computed are filled
with ``np.nan``.

No TA-Lib dependency — uses NumPy and Wilder-smoothing where appropriate.

Indicators implemented
----------------------
Trend
  adx          – Average Directional Index
  di_plus      – Positive Directional Indicator (+DI)
  di_minus     – Negative Directional Indicator (-DI)
  sar          – Parabolic Stop-and-Reverse
  aroon_up     – Aroon Up
  aroon_down   – Aroon Down

Momentum
  cci          – Commodity Channel Index
  mom          – Momentum
  roc          – Rate of Change
  willr        – Williams %R
  mfi          – Money Flow Index
  apo          – Absolute Price Oscillator
  ppo          – Percentage Price Oscillator

Volume
  obv          – On-Balance Volume
  ad           – Accumulation / Distribution
  adosc        – Chaikin A/D Oscillator

Moving Averages
  ema_60       – 60-period EMA
  ema_120      – 120-period EMA
  sma_60       – 60-period SMA

RCoinFutTrader core strategy indicators
  ddif         – DI+ minus DI-  (DDIF = DIF in the original codebase)
  maddif       – Fast EMA of DDIF
  maddif1      – Slow EMA of DDIF
"""

from __future__ import annotations

import numpy as np
from numpy import ndarray

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _true_range(high: ndarray, low: ndarray, close: ndarray) -> ndarray:
    """Vectorised True Range."""
    prev_close = np.empty_like(close)
    prev_close[0] = close[0]
    prev_close[1:] = close[:-1]
    tr = np.maximum(
        high - low,
        np.maximum(np.abs(high - prev_close), np.abs(low - prev_close)),
    )
    return tr


def _wilder_smooth(arr: ndarray, period: int) -> ndarray:
    """Wilder's smoothing (RMA): seed with SMA of first *period* values."""
    n = len(arr)
    out = np.full(n, np.nan)
    if n < period:
        return out
    seed = float(np.mean(arr[:period]))
    out[period - 1] = seed
    alpha = 1.0 / period
    for i in range(period, n):
        out[i] = out[i - 1] * (1.0 - alpha) + arr[i] * alpha
    return out


def _ema(arr: ndarray, period: int) -> ndarray:
    """Standard EMA (seed = first value)."""
    n = len(arr)
    out = np.full(n, np.nan)
    if n == 0:
        return out
    # Find first non-nan
    start = 0
    while start < n and np.isnan(arr[start]):
        start += 1
    if start >= n:
        return out
    out[start] = arr[start]
    k = 2.0 / (period + 1.0)
    for i in range(start + 1, n):
        if np.isnan(arr[i]):
            out[i] = np.nan
        else:
            out[i] = arr[i] * k + out[i - 1] * (1.0 - k)
    return out


def _sma(arr: ndarray, period: int) -> ndarray:
    """Simple Moving Average."""
    n = len(arr)
    out = np.full(n, np.nan)
    for i in range(period - 1, n):
        window = arr[i - period + 1: i + 1]
        if not np.any(np.isnan(window)):
            out[i] = float(np.mean(window))
    return out


def _extract_ohlcv(ohlcv: ndarray):
    """Return (open, high, low, close, volume) arrays from OHLCV matrix."""
    o = ohlcv[:, 0].astype(float)
    h = ohlcv[:, 1].astype(float)
    l = ohlcv[:, 2].astype(float)
    c = ohlcv[:, 3].astype(float)
    v = ohlcv[:, 4].astype(float)
    return o, h, l, c, v


# ---------------------------------------------------------------------------
# Trend indicators
# ---------------------------------------------------------------------------

def adx(ohlcv: ndarray, period: int = 14) -> ndarray:
    """Average Directional Index.

    Args:
        ohlcv: N×5 OHLCV array.
        period: Wilder smoothing period (default 14).

    Returns:
        ADX values, NaN during warmup.
    """
    _, h, l, c, _ = _extract_ohlcv(ohlcv)
    n = len(c)
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)
    tr_arr = np.zeros(n)

    for i in range(1, n):
        up = h[i] - h[i - 1]
        down = l[i - 1] - l[i]
        plus_dm[i] = up if (up > down and up > 0) else 0.0
        minus_dm[i] = down if (down > up and down > 0) else 0.0
        tr_arr[i] = max(
            h[i] - l[i],
            abs(h[i] - c[i - 1]),
            abs(l[i] - c[i - 1]),
        )

    s_plus = _wilder_smooth(plus_dm, period)
    s_minus = _wilder_smooth(minus_dm, period)
    s_tr = _wilder_smooth(tr_arr, period)

    with np.errstate(invalid="ignore", divide="ignore"):
        out_di_plus = np.where(s_tr > 0, s_plus / s_tr * 100.0, 0.0)
        out_di_minus = np.where(s_tr > 0, s_minus / s_tr * 100.0, 0.0)
        di_sum = out_di_plus + out_di_minus
        dx = np.where(di_sum > 0, np.abs(out_di_plus - out_di_minus) / di_sum * 100.0, 0.0)
    adx_out = _wilder_smooth(dx, period)
    # Mask warmup
    adx_out[:period * 2] = np.nan
    return adx_out


def di_plus(ohlcv: ndarray, period: int = 14) -> ndarray:
    """Positive Directional Indicator (+DI)."""
    _, h, l, c, _ = _extract_ohlcv(ohlcv)
    n = len(c)
    plus_dm = np.zeros(n)
    tr_arr = np.zeros(n)
    for i in range(1, n):
        up = h[i] - h[i - 1]
        down = l[i - 1] - l[i]
        plus_dm[i] = up if (up > down and up > 0) else 0.0
        tr_arr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    s_plus = _wilder_smooth(plus_dm, period)
    s_tr = _wilder_smooth(tr_arr, period)
    out = np.where(s_tr > 0, s_plus / s_tr * 100.0, 0.0)
    out[:period] = np.nan
    return out


def di_minus(ohlcv: ndarray, period: int = 14) -> ndarray:
    """Negative Directional Indicator (-DI)."""
    _, h, l, c, _ = _extract_ohlcv(ohlcv)
    n = len(c)
    minus_dm = np.zeros(n)
    tr_arr = np.zeros(n)
    for i in range(1, n):
        up = h[i] - h[i - 1]
        down = l[i - 1] - l[i]
        minus_dm[i] = down if (down > up and down > 0) else 0.0
        tr_arr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    s_minus = _wilder_smooth(minus_dm, period)
    s_tr = _wilder_smooth(tr_arr, period)
    out = np.where(s_tr > 0, s_minus / s_tr * 100.0, 0.0)
    out[:period] = np.nan
    return out


def sar(ohlcv: ndarray, acceleration: float = 0.02, maximum: float = 0.20) -> ndarray:
    """Parabolic Stop-and-Reverse (SAR).

    Args:
        ohlcv: N×5 OHLCV array.
        acceleration: Initial acceleration factor (default 0.02).
        maximum: Maximum acceleration factor (default 0.20).

    Returns:
        SAR values, NaN for first bar.
    """
    _, h, l, _, _ = _extract_ohlcv(ohlcv)
    n = len(h)
    out = np.full(n, np.nan)
    if n < 2:
        return out

    # Initialise
    bull = True  # True = uptrend
    af = acceleration
    ep = h[0]  # extreme point
    sar_val = l[0]

    for i in range(1, n):
        out[i] = sar_val

        if bull:
            if l[i] < sar_val:  # reversal
                bull = False
                sar_val = ep
                ep = l[i]
                af = acceleration
            else:
                if h[i] > ep:
                    ep = h[i]
                    af = min(af + acceleration, maximum)
                sar_val = sar_val + af * (ep - sar_val)
                sar_val = min(sar_val, l[i - 1], l[max(i - 2, 0)])
        else:
            if h[i] > sar_val:  # reversal
                bull = True
                sar_val = ep
                ep = h[i]
                af = acceleration
            else:
                if l[i] < ep:
                    ep = l[i]
                    af = min(af + acceleration, maximum)
                sar_val = sar_val + af * (ep - sar_val)
                sar_val = max(sar_val, h[i - 1], h[max(i - 2, 0)])

    return out


def aroon_up(ohlcv: ndarray, period: int = 25) -> ndarray:
    """Aroon Up: ((period - bars since period-high) / period) * 100."""
    _, h, _, _, _ = _extract_ohlcv(ohlcv)
    n = len(h)
    out = np.full(n, np.nan)
    for i in range(period, n):
        window = h[i - period: i + 1]
        idx_max = int(np.argmax(window))
        out[i] = (idx_max / period) * 100.0
    return out


def aroon_down(ohlcv: ndarray, period: int = 25) -> ndarray:
    """Aroon Down: ((period - bars since period-low) / period) * 100."""
    _, _, l, _, _ = _extract_ohlcv(ohlcv)
    n = len(l)
    out = np.full(n, np.nan)
    for i in range(period, n):
        window = l[i - period: i + 1]
        idx_min = int(np.argmin(window))
        out[i] = (idx_min / period) * 100.0
    return out


# ---------------------------------------------------------------------------
# Momentum indicators
# ---------------------------------------------------------------------------

def cci(ohlcv: ndarray, period: int = 14) -> ndarray:
    """Commodity Channel Index.

    CCI = (Typical Price - SMA(TP, n)) / (0.015 * Mean Deviation)
    Typical Price = (H + L + C) / 3
    """
    _, h, l, c, _ = _extract_ohlcv(ohlcv)
    tp = (h + l + c) / 3.0
    n = len(tp)
    out = np.full(n, np.nan)
    for i in range(period - 1, n):
        window = tp[i - period + 1: i + 1]
        avg = float(np.mean(window))
        mean_dev = float(np.mean(np.abs(window - avg)))
        if mean_dev > 0:
            out[i] = (tp[i] - avg) / (0.015 * mean_dev)
    return out


def mom(ohlcv: ndarray, period: int = 10) -> ndarray:
    """Momentum: Close[i] - Close[i - period]."""
    _, _, _, c, _ = _extract_ohlcv(ohlcv)
    n = len(c)
    out = np.full(n, np.nan)
    out[period:] = c[period:] - c[:-period]
    return out


def roc(ohlcv: ndarray, period: int = 10) -> ndarray:
    """Rate of Change (%): (Close[i] - Close[i-n]) / Close[i-n] * 100."""
    _, _, _, c, _ = _extract_ohlcv(ohlcv)
    n = len(c)
    out = np.full(n, np.nan)
    for i in range(period, n):
        if c[i - period] != 0:
            out[i] = (c[i] - c[i - period]) / c[i - period] * 100.0
    return out


def willr(ohlcv: ndarray, period: int = 14) -> ndarray:
    """Williams %R: ((Highest High - Close) / (Highest High - Lowest Low)) * -100."""
    _, h, l, c, _ = _extract_ohlcv(ohlcv)
    n = len(c)
    out = np.full(n, np.nan)
    for i in range(period - 1, n):
        hh = float(np.max(h[i - period + 1: i + 1]))
        ll = float(np.min(l[i - period + 1: i + 1]))
        denom = hh - ll
        if denom > 0:
            out[i] = ((hh - c[i]) / denom) * -100.0
    return out


def mfi(ohlcv: ndarray, period: int = 14) -> ndarray:
    """Money Flow Index (0-100).

    MFI = 100 - 100 / (1 + Positive MF / Negative MF)
    Typical Price = (H + L + C) / 3
    Raw MF = Typical Price × Volume
    """
    _, h, l, c, v = _extract_ohlcv(ohlcv)
    tp = (h + l + c) / 3.0
    raw_mf = tp * v
    n = len(tp)
    out = np.full(n, np.nan)

    for i in range(period, n):
        pos_mf = 0.0
        neg_mf = 0.0
        for j in range(i - period + 1, i + 1):
            if j == 0:
                continue
            if tp[j] > tp[j - 1]:
                pos_mf += raw_mf[j]
            elif tp[j] < tp[j - 1]:
                neg_mf += raw_mf[j]
        if neg_mf == 0:
            out[i] = 100.0
        else:
            mr = pos_mf / neg_mf
            out[i] = 100.0 - (100.0 / (1.0 + mr))
    return out


def apo(ohlcv: ndarray, fast_period: int = 12, slow_period: int = 26) -> ndarray:
    """Absolute Price Oscillator: EMA(fast) - EMA(slow)."""
    _, _, _, c, _ = _extract_ohlcv(ohlcv)
    fast = _ema(c, fast_period)
    slow = _ema(c, slow_period)
    return fast - slow


def ppo(ohlcv: ndarray, fast_period: int = 12, slow_period: int = 26) -> ndarray:
    """Percentage Price Oscillator: (EMA(fast) - EMA(slow)) / EMA(slow) * 100."""
    _, _, _, c, _ = _extract_ohlcv(ohlcv)
    fast = _ema(c, fast_period)
    slow = _ema(c, slow_period)
    out = np.full(len(c), np.nan)
    mask = slow != 0
    out[mask] = (fast[mask] - slow[mask]) / slow[mask] * 100.0
    return out


# ---------------------------------------------------------------------------
# Volume indicators
# ---------------------------------------------------------------------------

def obv(ohlcv: ndarray) -> ndarray:
    """On-Balance Volume.

    OBV[i] = OBV[i-1] + Volume  if Close > prev Close
    OBV[i] = OBV[i-1] - Volume  if Close < prev Close
    OBV[i] = OBV[i-1]           if Close == prev Close
    """
    _, _, _, c, v = _extract_ohlcv(ohlcv)
    n = len(c)
    out = np.zeros(n)
    out[0] = v[0]
    for i in range(1, n):
        if c[i] > c[i - 1]:
            out[i] = out[i - 1] + v[i]
        elif c[i] < c[i - 1]:
            out[i] = out[i - 1] - v[i]
        else:
            out[i] = out[i - 1]
    return out


def ad(ohlcv: ndarray) -> ndarray:
    """Accumulation / Distribution Line.

    CLV  = ((Close - Low) - (High - Close)) / (High - Low)
    AD[i] = AD[i-1] + CLV * Volume
    """
    _, h, l, c, v = _extract_ohlcv(ohlcv)
    n = len(c)
    out = np.zeros(n)
    hl = h - l
    # Avoid division by zero
    clv = np.where(hl > 0, ((c - l) - (h - c)) / hl, 0.0)
    mfv = clv * v
    out[0] = mfv[0]
    for i in range(1, n):
        out[i] = out[i - 1] + mfv[i]
    return out


def adosc(ohlcv: ndarray, fast_period: int = 3, slow_period: int = 10) -> ndarray:
    """Chaikin A/D Oscillator: EMA(AD, fast) - EMA(AD, slow)."""
    ad_line = ad(ohlcv)
    return _ema(ad_line, fast_period) - _ema(ad_line, slow_period)


# ---------------------------------------------------------------------------
# Moving Averages
# ---------------------------------------------------------------------------

def ema_60(ohlcv: ndarray) -> ndarray:
    """60-period EMA of Close."""
    _, _, _, c, _ = _extract_ohlcv(ohlcv)
    return _ema(c, 60)


def ema_120(ohlcv: ndarray) -> ndarray:
    """120-period EMA of Close."""
    _, _, _, c, _ = _extract_ohlcv(ohlcv)
    return _ema(c, 120)


def sma_60(ohlcv: ndarray) -> ndarray:
    """60-period SMA of Close."""
    _, _, _, c, _ = _extract_ohlcv(ohlcv)
    return _sma(c, 60)


# ---------------------------------------------------------------------------
# RCoinFutTrader core strategy indicators
# ---------------------------------------------------------------------------

def ddif(ohlcv: ndarray, period: int = 14) -> ndarray:
    """DDIF = DI+ - DI-  (raw difference of directional indicators).

    This is the primary signal in the RCoinFutTrader DDIF strategy.
    Positive values indicate a bullish bias; negative a bearish bias.
    """
    dip = di_plus(ohlcv, period)
    dim = di_minus(ohlcv, period)
    return dip - dim


def maddif(ohlcv: ndarray, period: int = 14, ema_period: int = 5) -> ndarray:
    """Fast EMA of DDIF.

    Args:
        ohlcv: N×5 OHLCV array.
        period: ADX/DI period (default 14).
        ema_period: EMA period applied to DDIF (default 5).

    Returns:
        Fast MADDIF values.
    """
    d = ddif(ohlcv, period)
    return _ema(d, ema_period)


def maddif1(ohlcv: ndarray, period: int = 14, ema_period: int = 20) -> ndarray:
    """Slow EMA of DDIF.

    Args:
        ohlcv: N×5 OHLCV array.
        period: ADX/DI period (default 14).
        ema_period: EMA period applied to DDIF (default 20).

    Returns:
        Slow MADDIF1 values.
    """
    d = ddif(ohlcv, period)
    return _ema(d, ema_period)


# ================================================================
# 추가 포팅 지표 (BinanceTrader에서 가져옴)
# ================================================================

def bollinger_middle(closes, period=20):
    """볼린저밴드 중간선 = SMA(period)"""
    import numpy as np
    result = np.full(len(closes), np.nan)
    for i in range(period - 1, len(closes)):
        result[i] = np.mean(closes[i - period + 1:i + 1])
    return result


def stochastic_k(highs, lows, closes, period=14):
    """Stochastic %K = (close - lowest_low) / (highest_high - lowest_low) * 100"""
    import numpy as np
    result = np.full(len(closes), np.nan)
    for i in range(period - 1, len(closes)):
        hh = np.max(highs[i - period + 1:i + 1])
        ll = np.min(lows[i - period + 1:i + 1])
        result[i] = ((closes[i] - ll) / (hh - ll) * 100) if hh != ll else 50.0
    return result


def stochastic_d(highs, lows, closes, k_period=14, d_period=3):
    """Stochastic %D = SMA(%K, d_period)"""
    import numpy as np
    k = stochastic_k(highs, lows, closes, k_period)
    result = np.full(len(closes), np.nan)
    for i in range(len(closes)):
        if i >= k_period + d_period - 2:
            window = k[i - d_period + 1:i + 1]
            if not np.isnan(window).any():
                result[i] = np.mean(window)
    return result


def stochastic_fast_k(highs, lows, closes, period=5):
    """Fast Stochastic %K (짧은 기간)"""
    return stochastic_k(highs, lows, closes, period)


def stochastic_fast_d(highs, lows, closes, k_period=5, d_period=3):
    """Fast Stochastic %D"""
    return stochastic_d(highs, lows, closes, k_period, d_period)


def money_flow_index(highs, lows, closes, volumes, period=14):
    """MFI = 100 - (100 / (1 + money_ratio)), 거래량 가중 RSI"""
    import numpy as np
    n = len(closes)
    result = np.full(n, np.nan)
    tp = (highs + lows + closes) / 3  # typical price
    for i in range(period, n):
        pos_flow = 0.0
        neg_flow = 0.0
        for j in range(i - period + 1, i + 1):
            if j > 0:
                mf = tp[j] * volumes[j]
                if tp[j] > tp[j - 1]:
                    pos_flow += mf
                else:
                    neg_flow += mf
        ratio = pos_flow / neg_flow if neg_flow > 0 else 999.99
        result[i] = 100.0 - (100.0 / (1.0 + ratio))
    return result


def absolute_price_oscillator(closes, fast=12, slow=26):
    """APO = EMA(fast) - EMA(slow)"""
    import numpy as np
    fast_ema = _ema_helper(closes, fast)
    slow_ema = _ema_helper(closes, slow)
    result = np.full(len(closes), np.nan)
    for i in range(slow - 1, len(closes)):
        if not np.isnan(fast_ema[i]) and not np.isnan(slow_ema[i]):
            result[i] = fast_ema[i] - slow_ema[i]
    return result


def percentage_price_oscillator(closes, fast=12, slow=26):
    """PPO = (EMA(fast) - EMA(slow)) / EMA(slow) * 100"""
    import numpy as np
    fast_ema = _ema_helper(closes, fast)
    slow_ema = _ema_helper(closes, slow)
    result = np.full(len(closes), np.nan)
    for i in range(slow - 1, len(closes)):
        if not np.isnan(fast_ema[i]) and not np.isnan(slow_ema[i]) and slow_ema[i] != 0:
            result[i] = (fast_ema[i] - slow_ema[i]) / slow_ema[i] * 100
    return result


def accumulation_distribution(highs, lows, closes, volumes):
    """AD Line = cumsum(((close-low)-(high-close))/(high-low) * volume)"""
    import numpy as np
    n = len(closes)
    result = np.zeros(n)
    for i in range(n):
        hl = highs[i] - lows[i]
        if hl > 0:
            clv = ((closes[i] - lows[i]) - (highs[i] - closes[i])) / hl
            result[i] = result[i - 1] + clv * volumes[i] if i > 0 else clv * volumes[i]
        elif i > 0:
            result[i] = result[i - 1]
    return result


def chaikin_ad_oscillator(highs, lows, closes, volumes, fast=3, slow=10):
    """ADOSC = EMA(AD, fast) - EMA(AD, slow)"""
    import numpy as np
    ad = accumulation_distribution(highs, lows, closes, volumes)
    fast_ema = _ema_helper(ad, fast)
    slow_ema = _ema_helper(ad, slow)
    result = np.full(len(closes), np.nan)
    for i in range(slow - 1, len(closes)):
        if not np.isnan(fast_ema[i]) and not np.isnan(slow_ema[i]):
            result[i] = fast_ema[i] - slow_ema[i]
    return result


def _ema_helper(data, period):
    """EMA 헬퍼 (지표 내부 사용)"""
    import numpy as np
    result = np.full(len(data), np.nan)
    if len(data) < period:
        return result
    k = 2.0 / (period + 1)
    result[period - 1] = np.mean(data[:period])
    for i in range(period, len(data)):
        result[i] = data[i] * k + result[i - 1] * (1 - k)
    return result
