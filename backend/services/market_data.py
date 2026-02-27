"""Binance 시장 데이터를 AI 코칭 프롬프트용으로 요약"""
import logging
import re
from typing import Optional

import pandas as pd

from services.binance import fetch_ohlcv

logger = logging.getLogger(__name__)

# 토큰 페어 감지용 패턴
_PAIR_PATTERN = re.compile(
    r"(BTC|ETH|SOL|RAY|JUP|BONK|WIF)[\s/]*(USDT|USDC)?",
    re.IGNORECASE,
)

# 타임프레임 감지
_TF_PATTERN = re.compile(
    r"(\d+)\s*(시간봉|시간|분봉|분|일봉|일|h|m|d)",
    re.IGNORECASE,
)

_TF_MAP = {
    "시간봉": "h", "시간": "h", "h": "h",
    "분봉": "m", "분": "m", "m": "m",
    "일봉": "d", "일": "d", "d": "d",
}

# 기간 감지 패턴들
_DAYS_PATTERNS = [
    # "최근 7일", "7일간", "7일 데이터"
    (re.compile(r"(\d+)\s*일(?:간|치| 데이터| 동안)?", re.IGNORECASE), lambda m: int(m.group(1))),
    # "최근 3주", "2주간"
    (re.compile(r"(\d+)\s*주(?:간|치| 데이터| 동안)?", re.IGNORECASE), lambda m: int(m.group(1)) * 7),
    # "최근 3개월", "2개월간", "6개월"
    (re.compile(r"(\d+)\s*개?월(?:간|치| 데이터| 동안)?", re.IGNORECASE), lambda m: int(m.group(1)) * 30),
    # "최근 1년", "2년간"
    (re.compile(r"(\d+)\s*년(?:간|치| 데이터| 동안)?", re.IGNORECASE), lambda m: int(m.group(1)) * 365),
    # "200 candles", "100캔들", "500봉"
    (re.compile(r"(\d+)\s*(?:캔들|candles?|봉 데이터)", re.IGNORECASE), lambda m: -int(m.group(1))),  # 음수 = 캔들 수
    # "3 months", "6 months"
    (re.compile(r"(\d+)\s*months?", re.IGNORECASE), lambda m: int(m.group(1)) * 30),
    # "1 year", "2 years"
    (re.compile(r"(\d+)\s*years?", re.IGNORECASE), lambda m: int(m.group(1)) * 365),
    # "90 days", "30 days"
    (re.compile(r"(\d+)\s*days?", re.IGNORECASE), lambda m: int(m.group(1))),
]


def _detect_period(text: str) -> tuple[int, bool]:
    """텍스트에서 데이터 기간 감지. (값, is_candles) 반환. 기본 30일."""
    for pattern, converter in _DAYS_PATTERNS:
        m = pattern.search(text)
        if m:
            val = converter(m)
            if val < 0:
                # 캔들 수 지정
                return abs(val), True
            # 일수 (최소 1일, 최대 365일)
            return max(1, min(val, 365)), False
    return 30, False


def _detect_pair(text: str) -> Optional[str]:
    """텍스트에서 토큰 페어 추출"""
    m = _PAIR_PATTERN.search(text)
    if not m:
        return None
    token = m.group(1).upper()
    quote = (m.group(2) or "USDT").upper()
    return f"{token}/{quote}"


def _detect_timeframe(text: str) -> str:
    """텍스트에서 타임프레임 추출 (기본 1h)"""
    m = _TF_PATTERN.search(text)
    if not m:
        return "1h"
    num = m.group(1)
    unit = _TF_MAP.get(m.group(2).lower(), "h")
    return f"{num}{unit}"


def _calc_rsi(series: pd.Series, period: int = 14) -> float:
    """RSI 계산"""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    return round(rsi.iloc[-1], 1) if not rsi.empty else 50.0


def _calc_ema(series: pd.Series, period: int) -> float:
    """EMA 최신값"""
    return round(series.ewm(span=period, adjust=False).mean().iloc[-1], 4)


async def fetch_market_summary(text: str, strategy: Optional[dict] = None) -> str:
    """사용자 메시지/전략에서 토큰+타임프레임을 감지하고 시장 데이터 요약 반환"""
    # 전략 JSON에서 페어/타임프레임 추출 우선
    pair = None
    tf = "1h"

    if strategy:
        pair = strategy.get("target_pair")
        tf = strategy.get("timeframe", "1h")

    # 텍스트에서도 감지 (전략 없을 때 폴백)
    if not pair:
        pair = _detect_pair(text)
    detected_tf = _detect_timeframe(text)
    if detected_tf != "1h":
        tf = detected_tf

    if not pair:
        return ""

    # 사용자가 명시한 데이터 기간 감지
    period_val, is_candles = _detect_period(text)

    try:
        if is_candles:
            # 캔들 수 기반: 타임프레임에 따라 일수 환산 (넉넉하게)
            tf_hours = {"1m": 1/60, "5m": 5/60, "15m": 0.25, "30m": 0.5,
                        "1h": 1, "4h": 4, "1d": 24}
            hours_per_candle = tf_hours.get(tf, 1)
            estimated_days = max(1, int(period_val * hours_per_candle / 24) + 2)
            df = await fetch_ohlcv(pair, timeframe=tf, days=estimated_days)
            # 요청한 캔들 수만큼만 잘라서 사용
            if len(df) > period_val:
                df = df.iloc[-period_val:]
        else:
            df = await fetch_ohlcv(pair, timeframe=tf, days=period_val)

        if df.empty or len(df) < 2:
            return ""

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]

        # 기본 가격 정보
        current_price = close.iloc[-1]
        price_24h_ago = close.iloc[-24] if len(close) > 24 else close.iloc[0]
        change_24h = round((current_price - price_24h_ago) / price_24h_ago * 100, 2)

        high_period = high.max()
        low_period = low.min()

        # 기간 표시 문자열
        if is_candles:
            period_label = f"{period_val}캔들"
        elif period_val >= 365:
            period_label = f"{period_val // 365}년"
        elif period_val >= 30:
            period_label = f"{period_val // 30}개월"
        elif period_val >= 7:
            period_label = f"{period_val // 7}주"
        else:
            period_label = f"{period_val}일"

        # 기술적 지표 (충분한 데이터가 있을 때만)
        rsi_str = ""
        if len(close) >= 14:
            rsi_14 = _calc_rsi(close, 14)
            rsi_str = f"RSI(14): {rsi_14} {'(과매수 주의)' if rsi_14 > 70 else '(과매도 영역)' if rsi_14 < 30 else ''}"

        macd_str = ""
        if len(close) >= 26:
            ema_12 = _calc_ema(close, 12)
            ema_26 = _calc_ema(close, 26)
            macd_val = round(ema_12 - ema_26, 4)
            macd_str = f"MACD: {macd_val:+.4f} (EMA12: {ema_12:.4f}, EMA26: {ema_26:.4f})"

        bb_str = ""
        if len(close) >= 20:
            sma_20 = close.rolling(20).mean().iloc[-1]
            std_20 = close.rolling(20).std().iloc[-1]
            bb_upper = round(sma_20 + 2 * std_20, 4)
            bb_lower = round(sma_20 - 2 * std_20, 4)
            bb_str = f"볼린저밴드: 하단 ${bb_lower:,.4f} / 상단 ${bb_upper:,.4f}"

        vol_str = ""
        if len(volume) >= 20:
            avg_vol = volume.rolling(20).mean().iloc[-1]
            latest_vol = volume.iloc[-1]
            vol_ratio = round(latest_vol / avg_vol * 100, 1) if avg_vol > 0 else 100.0
            vol_str = f"거래량: 20봉 평균 대비 {vol_ratio}%{'(거래량 급증!)' if vol_ratio > 150 else ''}"

        lines = [
            f"[실시간 시장 데이터 - {pair} {tf}봉 기준 (최근 {period_label})]",
            f"현재가: ${current_price:,.4f} ({'+' if change_24h >= 0 else ''}{change_24h}% 24h)",
            f"기간 범위: ${low_period:,.4f} ~ ${high_period:,.4f}",
        ]
        for s in [rsi_str, macd_str, bb_str, vol_str]:
            if s:
                lines.append(s)
        lines.append(f"데이터: 총 {len(df)}캔들 ({period_label})")

        return "\n".join(lines)

    except Exception as e:
        logger.warning(f"시장 데이터 조회 실패 ({pair}): {e}")
        return ""
