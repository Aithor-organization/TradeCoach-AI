from pydantic import BaseModel, Field, field_validator
from typing import Optional
import re


class OptimizeRequest(BaseModel):
    strategy_id: str = "local"
    parsed_strategy: Optional[dict] = None
    param_ranges: dict = {}
    objective: str = "sharpe"
    max_combinations: int = Field(default=80, ge=1, le=10000)
    search_method: str = Field(default="random", pattern=r"^(grid|random)$")
    symbol: str = Field(default="BTCUSDT", max_length=20)
    interval: str = Field(default="1h", max_length=10)
    days: int = Field(default=180, ge=1, le=3650)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        if not re.match(r"^[A-Za-z0-9]{1,20}$", v):
            raise ValueError("symbol은 영문/숫자만 허용 (최대 20자)")
        return v.upper()


class WalkForwardRequest(BaseModel):
    strategy_id: str = "local"
    parsed_strategy: Optional[dict] = None
    param_ranges: Optional[dict] = None
    in_sample_days: int = Field(default=180, ge=1, le=3650)
    out_sample_days: int = Field(default=60, ge=1, le=1825)
    windows: int = Field(default=3, ge=1, le=50)
    objective: str = "sharpe"
    symbol: str = Field(default="BTCUSDT", max_length=20)
    interval: str = Field(default="1h", max_length=10)
    days: int = Field(default=365, ge=1, le=3650)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        if not re.match(r"^[A-Za-z0-9]{1,20}$", v):
            raise ValueError("symbol은 영문/숫자만 허용 (최대 20자)")
        return v.upper()
