"""Asset request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AssetCreate(BaseModel):
    chain: str = Field(description="Chain slug the asset is issued on, e.g. 'robinhood-testnet'")
    name: str
    symbol: str
    asset_type: str = "bond"
    total_supply: int
    decimals: int = 2
    coupon_rate: float = 0.0
    maturity_date: str | None = None
    jurisdiction: str = "US"
    investor_type: str = "accredited"


class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chain: str
    name: str
    symbol: str
    token_id: str | None
    topic_id: str | None
    asset_type: str
    total_supply: int
    decimals: int
    coupon_rate: float
    maturity_date: str | None
    nav: float
    status: str
    jurisdiction: str
    investor_type: str
    created_at: datetime
