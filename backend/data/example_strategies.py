# 예시 전략 데이터 (Supabase 미연결 시 폴백용)
from datetime import datetime, timezone

EXAMPLE_STRATEGIES = [
    {
        "id": "example-rsi-reversal",
        "name": "RSI 평균회귀 전략",
        "raw_input": "RSI가 30 이하로 떨어지면 매수, 15% 익절, 8% 손절",
        "input_type": "text",
        "status": "tested",
        "created_at": datetime(2026, 2, 20, tzinfo=timezone.utc).isoformat(),
        "updated_at": datetime(2026, 2, 20, tzinfo=timezone.utc).isoformat(),
        "parsed_strategy": {
            "name": "RSI 평균회귀 전략",
            "version": 1,
            "entry": {
                "conditions": [
                    {
                        "indicator": "RSI",
                        "operator": "<=",
                        "value": 30,
                        "unit": "index",
                        "description": "RSI가 30 이하 (과매도 구간)",
                    }
                ],
                "logic": "AND",
            },
            "exit": {
                "take_profit": {"type": "percent", "value": 5},
                "stop_loss": {"type": "percent", "value": -5},
            },
            "position": {
                "size_type": "percent",
                "size_value": 30,
                "max_positions": 3,
            },
            "filters": {
                "min_liquidity_usd": 50000,
                "min_market_cap_usd": 1000000,
                "exclude_tokens": [],
                "token_whitelist": ["SOL"],
            },
            "timeframe": "1h",
            "target_pair": "SOL/USDC",
        },
    },
    {
        "id": "example-golden-cross",
        "name": "골든크로스 추세추종",
        "raw_input": "7일 이동평균이 25일 이동평균을 상향 돌파하면 매수, 20% 익절, 10% 손절",
        "input_type": "text",
        "status": "tested",
        "created_at": datetime(2026, 2, 18, tzinfo=timezone.utc).isoformat(),
        "updated_at": datetime(2026, 2, 18, tzinfo=timezone.utc).isoformat(),
        "parsed_strategy": {
            "name": "골든크로스 추세추종",
            "version": 1,
            "entry": {
                "conditions": [
                    {
                        "indicator": "MA_cross",
                        "operator": "cross_above",
                        "value": 0,
                        "unit": "MA7 > MA25",
                        "description": "7일 이평선이 25일 이평선을 상향 돌파",
                    }
                ],
                "logic": "AND",
            },
            "exit": {
                "take_profit": {"type": "percent", "value": 5},
                "stop_loss": {"type": "percent", "value": -5},
            },
            "position": {
                "size_type": "percent",
                "size_value": 25,
                "max_positions": 2,
            },
            "filters": {
                "min_liquidity_usd": 100000,
                "min_market_cap_usd": 5000000,
                "exclude_tokens": [],
                "token_whitelist": ["SOL"],
            },
            "timeframe": "4h",
            "target_pair": "SOL/USDC",
        },
    },
    {
        "id": "example-volume-breakout",
        "name": "거래량 폭증 돌파 전략",
        "raw_input": "거래량이 평균 대비 200% 이상 증가하면 매수, 20% 익절, 10% 손절",
        "input_type": "text",
        "status": "draft",
        "created_at": datetime(2026, 2, 15, tzinfo=timezone.utc).isoformat(),
        "updated_at": datetime(2026, 2, 15, tzinfo=timezone.utc).isoformat(),
        "parsed_strategy": {
            "name": "거래량 폭증 돌파 전략",
            "version": 1,
            "entry": {
                "conditions": [
                    {
                        "indicator": "volume_change",
                        "operator": ">=",
                        "value": 200,
                        "unit": "percent",
                        "description": "거래량이 이전 대비 200% 이상 증가",
                    }
                ],
                "logic": "AND",
            },
            "exit": {
                "take_profit": {"type": "percent", "value": 5},
                "stop_loss": {"type": "percent", "value": -5},
            },
            "position": {
                "size_type": "percent",
                "size_value": 20,
                "max_positions": 2,
            },
            "filters": {
                "min_liquidity_usd": 50000,
                "min_market_cap_usd": 1000000,
                "exclude_tokens": [],
                "token_whitelist": ["SOL"],
            },
            "timeframe": "1h",
            "target_pair": "SOL/USDC",
        },
    },
    # ── 검증된 투자 전략 (2025 리서치 기반) ──
    {
        "id": "example-macd-rsi-confluence",
        "name": "MACD + RSI 복합 시그널 전략",
        "raw_input": "MACD 히스토그램이 양전환하고 RSI가 40~60 사이에 있을 때 매수, 25% 익절, 10% 손절",
        "input_type": "text",
        "status": "tested",
        "created_at": datetime(2026, 2, 25, tzinfo=timezone.utc).isoformat(),
        "updated_at": datetime(2026, 2, 25, tzinfo=timezone.utc).isoformat(),
        "parsed_strategy": {
            "name": "MACD + RSI 복합 시그널 전략",
            "version": 1,
            "entry": {
                "conditions": [
                    {
                        "indicator": "MACD_histogram",
                        "operator": "cross_above",
                        "value": 0,
                        "unit": "index",
                        "description": "MACD 히스토그램이 0선 위로 양전환 (12,26,9)",
                    },
                    {
                        "indicator": "RSI",
                        "operator": "between",
                        "value": 50,
                        "unit": "range:40-60",
                        "description": "RSI(14)가 40~60 구간 (중립 → 상승 전환 구간)",
                    },
                ],
                "logic": "AND",
            },
            "exit": {
                "take_profit": {"type": "percent", "value": 5},
                "stop_loss": {"type": "percent", "value": -5},
            },
            "position": {
                "size_type": "percent",
                "size_value": 25,
                "max_positions": 3,
            },
            "filters": {
                "min_liquidity_usd": 100000,
                "min_market_cap_usd": 5000000,
                "exclude_tokens": [],
                "token_whitelist": ["SOL", "ETH"],
            },
            "timeframe": "4h",
            "target_pair": "SOL/USDC",
        },
    },
    {
        "id": "example-bb-stochrsi-reversion",
        "name": "볼린저밴드 + StochRSI 평균회귀",
        "raw_input": "가격이 볼린저밴드 하단 터치하고 StochRSI가 20 이하면 매수, 15% 익절, 7% 손절",
        "input_type": "text",
        "status": "tested",
        "created_at": datetime(2026, 2, 25, tzinfo=timezone.utc).isoformat(),
        "updated_at": datetime(2026, 2, 25, tzinfo=timezone.utc).isoformat(),
        "parsed_strategy": {
            "name": "볼린저밴드 + StochRSI 평균회귀",
            "version": 1,
            "entry": {
                "conditions": [
                    {
                        "indicator": "BB_lower",
                        "operator": "<=",
                        "value": 0,
                        "unit": "BB(20,2)",
                        "description": "가격이 볼린저밴드 하단(20일, 2σ) 터치 또는 이탈",
                    },
                    {
                        "indicator": "StochRSI",
                        "operator": "<=",
                        "value": 20,
                        "unit": "index",
                        "description": "StochRSI(14,14,3,3)가 20 이하 (극과매도)",
                    },
                ],
                "logic": "AND",
            },
            "exit": {
                "take_profit": {
                    "type": "percent",
                    "value": 5,
                    "partial": {
                        "enabled": True,
                        "at_percent": 2.5,
                        "sell_ratio": 0.5,
                    },
                },
                "stop_loss": {"type": "percent", "value": -5},
            },
            "position": {
                "size_type": "percent",
                "size_value": 20,
                "max_positions": 3,
            },
            "filters": {
                "min_liquidity_usd": 50000,
                "min_market_cap_usd": 2000000,
                "exclude_tokens": [],
                "token_whitelist": ["SOL"],
            },
            "timeframe": "1h",
            "target_pair": "SOL/USDC",
        },
    },
    {
        "id": "example-vwap-weekly-swing",
        "name": "VWAP 주간 스윙 로테이션",
        "raw_input": "주간 종가가 VWAP 위로 돌파하면 월요일 매수, 일요일 매도 또는 29% 익절/10% 손절",
        "input_type": "text",
        "status": "verified",
        "created_at": datetime(2026, 2, 25, tzinfo=timezone.utc).isoformat(),
        "updated_at": datetime(2026, 2, 25, tzinfo=timezone.utc).isoformat(),
        "parsed_strategy": {
            "name": "VWAP 주간 스윙 로테이션",
            "version": 1,
            "entry": {
                "conditions": [
                    {
                        "indicator": "VWAP",
                        "operator": "cross_above",
                        "value": 0,
                        "unit": "weekly",
                        "description": "주간 종가가 VWAP 위로 돌파 시 월요일 진입",
                    },
                ],
                "logic": "AND",
            },
            "exit": {
                "take_profit": {"type": "percent", "value": 5},
                "stop_loss": {"type": "percent", "value": -5},
            },
            "position": {
                "size_type": "percent",
                "size_value": 30,
                "max_positions": 2,
            },
            "filters": {
                "min_liquidity_usd": 200000,
                "min_market_cap_usd": 10000000,
                "exclude_tokens": [],
                "token_whitelist": ["SOL", "ETH", "BTC"],
            },
            "timeframe": "1w",
            "target_pair": "SOL/USDC",
        },
    },
    {
        "id": "example-ema-crossover-atr",
        "name": "EMA 9/21 크로스오버 + ATR 필터",
        "raw_input": "EMA 9가 EMA 21을 상향 돌파하고 ATR이 평균 이상이면 매수, 20% 익절, 8% 손절",
        "input_type": "text",
        "status": "tested",
        "created_at": datetime(2026, 2, 25, tzinfo=timezone.utc).isoformat(),
        "updated_at": datetime(2026, 2, 25, tzinfo=timezone.utc).isoformat(),
        "parsed_strategy": {
            "name": "EMA 9/21 크로스오버 + ATR 필터",
            "version": 1,
            "entry": {
                "conditions": [
                    {
                        "indicator": "EMA_cross",
                        "operator": "cross_above",
                        "value": 0,
                        "unit": "EMA9 > EMA21",
                        "description": "EMA 9가 EMA 21을 상향 돌파 (단기 모멘텀 전환)",
                    },
                    {
                        "indicator": "ATR",
                        "operator": ">=",
                        "value": 1.0,
                        "unit": "ATR_ratio",
                        "description": "ATR(14)이 20일 평균 ATR 이상 (변동성 충분)",
                    },
                ],
                "logic": "AND",
            },
            "exit": {
                "take_profit": {"type": "percent", "value": 5},
                "stop_loss": {"type": "percent", "value": -5},
            },
            "position": {
                "size_type": "percent",
                "size_value": 25,
                "max_positions": 2,
            },
            "filters": {
                "min_liquidity_usd": 100000,
                "min_market_cap_usd": 5000000,
                "exclude_tokens": [],
                "token_whitelist": ["SOL", "ETH"],
            },
            "timeframe": "4h",
            "target_pair": "SOL/USDC",
        },
    },
    {
        "id": "example-qrsi-momentum",
        "name": "Q-RSI 모멘텀 퀀트 전략",
        "raw_input": "RSI(2)가 15 이하로 극과매도 진입, RSI(30)이 50 이상인 상승 추세에서만, 85 이상에서 매도",
        "input_type": "text",
        "status": "verified",
        "created_at": datetime(2026, 2, 25, tzinfo=timezone.utc).isoformat(),
        "updated_at": datetime(2026, 2, 25, tzinfo=timezone.utc).isoformat(),
        "parsed_strategy": {
            "name": "Q-RSI 모멘텀 퀀트 전략",
            "version": 1,
            "entry": {
                "conditions": [
                    {
                        "indicator": "RSI",
                        "operator": "<=",
                        "value": 15,
                        "unit": "RSI(2)",
                        "description": "RSI(2)가 15 이하 (단기 극과매도 시그널)",
                    },
                    {
                        "indicator": "RSI",
                        "operator": ">=",
                        "value": 50,
                        "unit": "RSI(30)",
                        "description": "RSI(30)이 50 이상 (장기 상승 추세 필터)",
                    },
                ],
                "logic": "AND",
            },
            "exit": {
                "take_profit": {"type": "percent", "value": 5},
                "stop_loss": {"type": "percent", "value": -5},
            },
            "position": {
                "size_type": "percent",
                "size_value": 20,
                "max_positions": 4,
            },
            "filters": {
                "min_liquidity_usd": 100000,
                "min_market_cap_usd": 5000000,
                "exclude_tokens": [],
                "token_whitelist": ["SOL", "ETH", "BTC"],
            },
            "timeframe": "1d",
            "target_pair": "SOL/USDC",
        },
    },
]


def get_example_strategies() -> list:
    return EXAMPLE_STRATEGIES


def get_example_strategy_by_id(strategy_id: str) -> dict | None:
    for s in EXAMPLE_STRATEGIES:
        if s["id"] == strategy_id:
            return s
    return None
