from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import date, datetime
import re


class BacktestRequest(BaseModel):
    strategy_id: str = "local"
    token_pair: str = Field(default="SOL/USDC", max_length=20)
    timeframe: str = Field(default="1h", max_length=10)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    parsed_strategy: Optional[dict] = None
    language: str = Field(default="ko", max_length=5)
    market_type: str = "spot"  # "spot" 또는 "futures"

    @field_validator("token_pair")
    @classmethod
    def validate_token_pair(cls, v: str) -> str:
        # "SOL/USDC" 또는 "BTCUSDT" 형식 허용
        if not re.match(r"^[A-Za-z0-9/]{1,20}$", v):
            raise ValueError("token_pair은 영문/숫자/슬래시만 허용 (최대 20자)")
        return v

    @field_validator("market_type")
    @classmethod
    def validate_market_type(cls, v: str) -> str:
        if v not in ("spot", "futures"):
            raise ValueError("market_type은 'spot' 또는 'futures'만 허용")
        return v


class BacktestMetrics(BaseModel):
    total_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    # 선물 확장 메트릭
    cagr: Optional[float] = None
    profit_factor: Optional[float] = None
    calmar_ratio: Optional[float] = None
    avg_win: Optional[float] = None
    avg_loss: Optional[float] = None
    max_consecutive_losses: Optional[int] = None
    long_trades: Optional[int] = None
    short_trades: Optional[int] = None
    long_win_rate: Optional[float] = None
    short_win_rate: Optional[float] = None


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
