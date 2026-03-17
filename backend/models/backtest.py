from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class BacktestRequest(BaseModel):
    strategy_id: str = "local"
    token_pair: str = "SOL/USDC"
    timeframe: str = "1h"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    parsed_strategy: Optional[dict] = None
    language: str = "ko"


class BacktestMetrics(BaseModel):
    total_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int


class BacktestResponse(BaseModel):
    id: str
    strategy_id: str
    metrics: BacktestMetrics
    token_pair: str
    timeframe: str
    start_date: date
    end_date: date
    equity_curve: list[dict]
    trade_log: list[dict]
    created_at: datetime
