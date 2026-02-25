from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class EntryCondition(BaseModel):
    indicator: str
    operator: str
    value: float
    unit: str = "percent"
    description: str = ""


class Entry(BaseModel):
    conditions: list[EntryCondition]
    logic: str = "AND"


class PartialExit(BaseModel):
    enabled: bool = False
    at_percent: float = 0
    sell_ratio: float = 0.5


class TakeProfit(BaseModel):
    type: str = "percent"
    value: float
    partial: Optional[PartialExit] = None


class StopLoss(BaseModel):
    type: str = "percent"
    value: float


class Exit(BaseModel):
    take_profit: TakeProfit
    stop_loss: StopLoss


class Position(BaseModel):
    size_type: str = "fixed_usd"
    size_value: float = 100
    max_positions: int = 3


class Filters(BaseModel):
    min_liquidity_usd: float = 50000
    min_market_cap_usd: float = 1000000
    exclude_tokens: list[str] = []
    token_whitelist: list[str] = []


class ParsedStrategy(BaseModel):
    name: str
    version: int = 1
    entry: Entry
    exit: Exit
    position: Position
    filters: Filters = Field(default_factory=Filters)
    timeframe: str = "1h"
    target_pair: str = "SOL/USDC"


class StrategyCreate(BaseModel):
    raw_input: str
    input_type: str = "text"  # text | image | paste


class StrategyResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    raw_input: str
    input_type: str
    parsed_strategy: dict
    status: str
    created_at: datetime
    updated_at: datetime


class StrategySave(BaseModel):
    name: str
    raw_input: str = ""
    input_type: str = "text"
    parsed_strategy: dict


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parsed_strategy: Optional[dict] = None
