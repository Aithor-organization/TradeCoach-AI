import json
import logging
import re
from datetime import date
from typing import Optional

import numpy as np
import pandas as pd

import sys
try:
    import coverage
    if not hasattr(coverage, 'types'):
        import types as _types
        coverage.types = _types.ModuleType('types')
    # numba coverage_support.py가 참조하는 모든 속성 패치
    if getattr(coverage.types, 'Tracer', None) is None:
        class DummyTracer:
            pass
        coverage.types.Tracer = DummyTracer
    for _attr in ('TTraceData', 'TShouldTraceFn', 'TFileDisposition',
                  'TShouldStartContextFn', 'TWarnFn', 'TTraceFn'):
        if getattr(coverage.types, _attr, None) is None:
            setattr(coverage.types, _attr, None)
except ImportError:
    pass

import vectorbt as vbt

from services.binance import fetch_ohlcv
from services.supabase_client import get_strategy_by_id, save_backtest_result

logger = logging.getLogger(__name__)

_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I,
)


async def execute_backtest(
    strategy_id: str,
    token_pair: str = "SOL/USDC",
    timeframe: str = "1h",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    parsed_strategy: Optional[dict] = None,
    language: str = "ko",
) -> dict:
    """전략 기반 백테스트 실행 (vectorbt)"""
    if parsed_strategy:
        parsed = parsed_strategy
    else:
        strategy = await get_strategy_by_id(strategy_id)
        if not strategy:
            raise ValueError("Strategy not found")
        parsed = strategy["parsed_strategy"]
    if isinstance(parsed, str):
        parsed = json.loads(parsed)

    # OHLCV 데이터 수집
    df = await fetch_ohlcv(
        token_symbol=token_pair,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
    )

    # 날짜 필터
    if start_date:
        df = df[df.index >= pd.Timestamp(start_date)]
    if end_date:
        df = df[df.index <= pd.Timestamp(end_date)]

    if len(df) < 10:
        raise ValueError("Insufficient data for backtest")

    # 실제 데이터 범위 기록 (API가 반환한 날짜)
    actual_start = df.index[0].isoformat()
    actual_end = df.index[-1].isoformat()

    # 진입/퇴장 시그널 생성 (High/Low 기반 봉 중간 청산)
    entries, exits, exit_prices = _generate_signals(df, parsed)

    # 투자금 설정: max_positions는 항상 1로 고정, size_value가 곧 init_cash
    position = parsed.get("position", {})
    size_value = position.get("size_value", 1000)
    init_cash = float(size_value)
    if init_cash <= 0:
        init_cash = 1000.0
    fees = 0.0004  # 0.04% 수수료

    pf = vbt.Portfolio.from_signals(
        close=exit_prices,
        entries=entries,
        exits=exits,
        init_cash=init_cash,
        size=float(size_value),
        size_type="value",
        fees=fees,
        freq=timeframe,
    )

    # vectorbt 지표 추출
    result = _extract_results(pf, df, init_cash)

    # AI 분석 리포트 자동 생성
    ai_summary = None
    try:
        from services.gemini import generate_backtest_summary
        ai_summary = await generate_backtest_summary(parsed, result["metrics"], language=language)
    except Exception as e:
        logger.warning(f"AI 분석 리포트 생성 실패 (계속 진행): {e}")

    # DB 저장
    result_data = {
        "token_pair": token_pair,
        "timeframe": timeframe,
        "metrics": result["metrics"],
        "equity_curve": result["equity_curve"],
        "trade_log": result["trade_log"],
        "ai_summary": ai_summary,
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "parsed_strategy": parsed,
    }
    if strategy_id and _UUID_RE.match(strategy_id):
        result_data["strategy_id"] = strategy_id
    saved = await save_backtest_result(result_data)

    return {
        "id": saved["id"],
        "metrics": result["metrics"],
        "equity_curve": result["equity_curve"],
        "trade_log": result["trade_log"],
        "ai_summary": ai_summary,
        "actual_period": {
            "start": actual_start,
            "end": actual_end,
            "candles": len(df),
        },
    }


def _extract_results(pf, df: pd.DataFrame, init_cash: float) -> dict:
    """vectorbt Portfolio에서 결과 추출"""
    # 자산 곡선
    equity_series = pf.value()
    equity_list = []
    for ts, val in equity_series.items():
        equity_list.append({
            "date": int(ts.timestamp()),
            "value": round(float(val), 2),
        })

    # 샘플링 (최대 200포인트)
    step = max(1, len(equity_list) // 200)
    sampled_equity = equity_list[::step]

    # 지표 계산
    total_return = round(float(pf.total_return() * 100), 2)
    max_dd = round(float(pf.max_drawdown() * 100), 2)

    # Sharpe Ratio
    try:
        sharpe = round(float(pf.sharpe_ratio()), 2)
        if np.isnan(sharpe) or np.isinf(sharpe):
            sharpe = 0.0
    except Exception:
        sharpe = 0.0

    # 거래 기록
    trades_df = pf.trades.records_readable
    total_trades = len(trades_df) if len(trades_df) > 0 else 0
    wins = len(trades_df[trades_df["PnL"] > 0]) if total_trades > 0 else 0
    win_rate = round((wins / total_trades) * 100, 2) if total_trades > 0 else 0.0

    # trade_log 생성 (vectorbt 0.26: Entry/Exit Timestamp 컬럼 사용)
    trade_log = []
    if total_trades > 0:
        for _, row in trades_df.iterrows():
            entry_ts = row["Entry Timestamp"]
            exit_ts = row["Exit Timestamp"]
            trade_log.append({
                "entry_date": int(entry_ts.timestamp()),
                "exit_date": int(exit_ts.timestamp()),
                "pnl": round(float(row["PnL"]), 2),
                "return_pct": round(float(row["Return"] * 100), 2),
            })

    metrics = {
        "total_return": total_return,
        "max_drawdown": max_dd,
        "sharpe_ratio": sharpe,
        "win_rate": win_rate,
        "total_trades": total_trades,
        "init_cash": init_cash,
    }

    return {
        "metrics": metrics,
        "equity_curve": sampled_equity,
        "trade_log": trade_log,
    }


def _apply_operator(series: pd.Series, operator: str, value: float) -> pd.Series:
    """비교 연산자 적용 헬퍼"""
    if operator == "<=":
        return series <= value
    elif operator == "<":
        return series < value
    elif operator == ">=":
        return series >= value
    elif operator == ">":
        return series > value
    elif operator == "==":
        return series == value
    return series >= value


def _generate_signals(df: pd.DataFrame, strategy: dict) -> tuple:
    """전략 조건 기반 진입/퇴장 시그널 생성 (확장 지표 지원)

    Returns: (entries, exits, tp_pct, sl_pct)
      - tp_pct: 익절 비율 (0~1, 예: 0.08 = 8%)
      - sl_pct: 손절 비율 (0~1, 예: 0.05 = 5%)
    """
    entries = pd.Series(False, index=df.index)
    exits = pd.Series(False, index=df.index)

    conditions = strategy.get("entry", {}).get("conditions", [])
    logic = strategy.get("entry", {}).get("logic", "OR").upper()
    tp = strategy.get("exit", {}).get("take_profit", {}).get("value", 20)
    sl = strategy.get("exit", {}).get("stop_loss", {}).get("value", -10)

    condition_signals = []

    for cond in conditions:
        indicator = cond.get("indicator", "").lower()
        operator = cond.get("operator", ">=")
        value = cond.get("value", 0)
        params = cond.get("params", {})
        signal = pd.Series(False, index=df.index)

        # === RSI ===
        if "rsi" in indicator and "stoch" not in indicator:
            period = params.get("period", 14)
            rsi = vbt.RSI.run(df["Close"], window=period).rsi
            signal = _apply_operator(rsi, operator, value)

        # === Stochastic RSI ===
        elif "stoch" in indicator and "rsi" in indicator:
            rsi_period = params.get("rsi_period", 14)
            stoch_period = params.get("stoch_period", 14)
            rsi = vbt.RSI.run(df["Close"], window=rsi_period).rsi
            stoch_rsi = (rsi - rsi.rolling(stoch_period).min()) / \
                        (rsi.rolling(stoch_period).max() - rsi.rolling(stoch_period).min()) * 100
            stoch_rsi = stoch_rsi.fillna(50)
            signal = _apply_operator(stoch_rsi, operator, value)

        # === MA Cross (골든크로스/데드크로스) ===
        elif "ma_cross" in indicator or "golden" in indicator or "dead" in indicator:
            short_period = params.get("short_period", 7)
            long_period = params.get("long_period", 25)
            ma_short = vbt.MA.run(df["Close"], window=short_period).ma
            ma_long = vbt.MA.run(df["Close"], window=long_period).ma
            if "dead" in indicator:
                cross = ma_short < ma_long
            else:
                cross = ma_short > ma_long
            signal = cross & ~cross.shift(1).fillna(False)

        # === EMA Cross ===
        elif "ema_cross" in indicator or "ema" in indicator:
            short_period = params.get("short_period", 12)
            long_period = params.get("long_period", 26)
            ema_short = df["Close"].ewm(span=short_period, adjust=False).mean()
            ema_long = df["Close"].ewm(span=long_period, adjust=False).mean()
            cross = ema_short > ema_long
            signal = cross & ~cross.shift(1).fillna(False)

        # === MACD ===
        elif "macd" in indicator:
            fast = params.get("fast_period", 12)
            slow = params.get("slow_period", 26)
            signal_period = params.get("signal_period", 9)
            ema_fast = df["Close"].ewm(span=fast, adjust=False).mean()
            ema_slow = df["Close"].ewm(span=slow, adjust=False).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
            macd_hist = macd_line - signal_line
            # MACD 히스토그램이 양수로 전환 (매수 신호)
            if "hist" in indicator:
                signal = _apply_operator(macd_hist, operator, value)
            else:
                cross_up = (macd_line > signal_line) & ~(macd_line.shift(1) > signal_line.shift(1))
                signal = cross_up.fillna(False)

        # === Bollinger Bands ===
        elif "bollinger" in indicator or "bb" in indicator:
            period = params.get("period", 20)
            std_dev = params.get("std_dev", 2.0)
            ma = df["Close"].rolling(window=period).mean()
            std = df["Close"].rolling(window=period).std()
            upper = ma + std_dev * std
            lower = ma - std_dev * std
            if "upper" in indicator:
                signal = df["Close"] > upper
            else:
                # 기본: 하단밴드 터치 시 매수 (평균회귀)
                signal = df["Close"] <= lower

        # === ATR (Average True Range) ===
        elif "atr" in indicator:
            period = params.get("period", 14)
            high_low = df["High"] - df["Low"]
            high_close = (df["High"] - df["Close"].shift(1)).abs()
            low_close = (df["Low"] - df["Close"].shift(1)).abs()
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = tr.rolling(window=period).mean()
            atr_pct = (atr / df["Close"]) * 100
            signal = _apply_operator(atr_pct, operator, value)

        # === Volume Change ===
        elif "volume" in indicator:
            vol_change = df["Volume"].pct_change() * 100
            signal = _apply_operator(vol_change, operator, value)

        # === Price Change ===
        elif "price" in indicator:
            price_change = df["Close"].pct_change() * 100
            signal = _apply_operator(price_change, operator, value)

        # === VWAP (Volume Weighted Average Price) ===
        elif "vwap" in indicator:
            vwap = (df["Volume"] * (df["High"] + df["Low"] + df["Close"]) / 3).cumsum() / df["Volume"].cumsum()
            if "above" in indicator or operator in (">=", ">"):
                signal = df["Close"] > vwap
            else:
                signal = df["Close"] < vwap

        condition_signals.append(signal)

    # AND/OR 로직 적용
    if condition_signals:
        if logic == "AND":
            combined = condition_signals[0]
            for s in condition_signals[1:]:
                combined = combined & s
            entries = combined
        else:
            for s in condition_signals:
                entries = entries | s

    # 진입이 없으면 기본 시그널 (이동평균 크로스)
    if not entries.any():
        ma_short = vbt.MA.run(df["Close"], window=7).ma
        ma_long = vbt.MA.run(df["Close"], window=25).ma
        cross = ma_short > ma_long
        entries = cross & ~cross.shift(1).fillna(False)

    # 익절/손절: High/Low 기반 봉 중간 청산 (정확한 SL/TP 가격으로 청산)
    tp_ratio = abs(tp) / 100.0  # 예: 8% → 0.08
    sl_ratio = abs(sl) / 100.0  # 예: -5% → 0.05

    # vectorbt 동기화를 위해 clean 시그널 생성
    # entries 원본은 조건 충족하는 모든 봉에 True → vectorbt가 exit 봉에서
    # 재진입 시 수정된 exit_prices(SL가격)로 entry하는 버그 방지
    clean_entries = pd.Series(False, index=df.index)
    clean_exits = pd.Series(False, index=df.index)
    exit_prices = df["Close"].copy().astype(float)
    entry_price = None

    for i in range(len(df)):
        if entry_price is None and entries.iloc[i]:
            clean_entries.iloc[i] = True
            entry_price = df["Close"].iloc[i]
        elif entry_price is not None:
            sl_price = entry_price * (1 - sl_ratio)
            tp_price = entry_price * (1 + tp_ratio)

            # SL 체크: 봉의 Low가 SL 가격 이하
            if df["Low"].iloc[i] <= sl_price:
                clean_exits.iloc[i] = True
                exit_prices.iloc[i] = sl_price
                entry_price = None
            # TP 체크: 봉의 High가 TP 가격 이상
            elif df["High"].iloc[i] >= tp_price:
                clean_exits.iloc[i] = True
                exit_prices.iloc[i] = tp_price
                entry_price = None

    return clean_entries, clean_exits, exit_prices
