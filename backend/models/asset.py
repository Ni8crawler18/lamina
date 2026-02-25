"""Asset data models (Pydantic schemas for API)."""

from pydantic import BaseModel
from typing import Optional


class AssetCreate(BaseModel):
    name: str
    symbol: str
    asset_type: str = "bond"
    total_supply: int
    decimals: int = 2
    coupon_rate: float = 0.0
    maturity_date: Optional[str] = None
    jurisdiction: str = "US"
    investor_type: str = "accredited"


class AssetResponse(BaseModel):
    id: int
    name: str
    symbol: str
    token_id: Optional[str] = None
    topic_id: Optional[str] = None
    asset_type: str
    total_supply: int
    decimals: int
    coupon_rate: float
    maturity_date: Optional[str] = None
    nav: float
    status: str
    jurisdiction: str
    investor_type: str
    created_at: str


class AssetUpdate(BaseModel):
    nav: Optional[float] = None
    status: Optional[str] = None
