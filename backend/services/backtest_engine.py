import json
import re
from datetime import date
from typing import Optional

import numpy as np
import pandas as pd
import vectorbt as vbt

from services.birdeye import fetch_ohlcv
from services.supabase_client import get_strategy_by_id, save_backtest_result

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
    df = await fetch_ohlcv(token_pair, timeframe)

    # 날짜 필터
    if start_date:
        df = df[df.index >= pd.Timestamp(start_date)]
    if end_date:
        df = df[df.index <= pd.Timestamp(end_date)]

    if len(df) < 10:
        raise ValueError("Insufficient data for backtest")

    # 진입/퇴장 시그널 생성
    entries, exits = _generate_signals(df, parsed)

    # vectorbt 포트폴리오 시뮬레이션
    init_cash = 1000.0
    fees = 0.003  # 0.3% 수수료

    pf = vbt.Portfolio.from_signals(
        close=df["Close"],
        entries=entries,
        exits=exits,
        init_cash=init_cash,
        fees=fees,
        freq=timeframe,
    )

    # vectorbt 지표 추출
    result = _extract_results(pf, df, init_cash)

    # DB 저장
    result_data = {
        "token_pair": token_pair,
        "timeframe": timeframe,
        "metrics": result["metrics"],
        "equity_curve": result["equity_curve"],
    }
    if strategy_id and _UUID_RE.match(strategy_id):
        result_data["strategy_id"] = strategy_id
    saved = await save_backtest_result(result_data)

    return {
        "id": saved["id"],
        "metrics": result["metrics"],
        "equity_curve": result["equity_curve"],
        "trade_log": result["trade_log"][:20],
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
    }

    return {
        "metrics": metrics,
        "equity_curve": sampled_equity,
        "trade_log": trade_log,
    }


def _generate_signals(df: pd.DataFrame, strategy: dict) -> tuple:
    """전략 조건 기반 진입/퇴장 시그널 생성"""
    entries = pd.Series(False, index=df.index)
    exits = pd.Series(False, index=df.index)

    conditions = strategy.get("entry", {}).get("conditions", [])
    tp = strategy.get("exit", {}).get("take_profit", {}).get("value", 20)
    sl = strategy.get("exit", {}).get("stop_loss", {}).get("value", -10)

    for cond in conditions:
        indicator = cond.get("indicator", "")
        operator = cond.get("operator", ">=")
        value = cond.get("value", 0)

        if "volume" in indicator.lower():
            vol_change = df["Volume"].pct_change() * 100
            if operator == ">=":
                entries = entries | (vol_change >= value)
            elif operator == ">":
                entries = entries | (vol_change > value)

        elif "rsi" in indicator.lower():
            # RSI 계산 (vectorbt 내장)
            rsi = vbt.RSI.run(df["Close"], window=14).rsi
            if operator == "<=":
                entries = entries | (rsi <= value)
            elif operator == ">=":
                entries = entries | (rsi >= value)

        elif "ma_cross" in indicator.lower() or "cross" in indicator.lower():
            # 이동평균 크로스 (vectorbt 내장)
            ma_short = vbt.MA.run(df["Close"], window=7).ma
            ma_long = vbt.MA.run(df["Close"], window=25).ma
            cross = ma_short > ma_long
            entries = entries | (cross & ~cross.shift(1).fillna(False))

        elif "price" in indicator.lower():
            price_change = df["Close"].pct_change() * 100
            if operator == ">=":
                entries = entries | (price_change >= value)
            elif operator == "<=":
                entries = entries | (price_change <= value)

    # 진입이 없으면 기본 시그널 (이동평균 크로스)
    if not entries.any():
        ma_short = vbt.MA.run(df["Close"], window=7).ma
        ma_long = vbt.MA.run(df["Close"], window=25).ma
        cross = ma_short > ma_long
        entries = cross & ~cross.shift(1).fillna(False)

    # 익절/손절 기반 퇴장
    entry_price = None
    for i in range(len(df)):
        if entries.iloc[i] and entry_price is None:
            entry_price = df["Close"].iloc[i]
        elif entry_price is not None:
            ret = ((df["Close"].iloc[i] / entry_price) - 1) * 100
            if ret >= abs(tp) or ret <= sl:
                exits.iloc[i] = True
                entry_price = None

    return entries, exits
