"""Holder / whitelist / purchase schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WhitelistRequest(BaseModel):
    account_id: str
    name: str | None = None
    jurisdiction: str = "US"
    investor_type: str = "accredited"


class PurchaseRequest(BaseModel):
    account_id: str
    amount: int


class HolderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: str
    asset_id: int
    name: str | None
    balance: int
    kyc_status: str
    jurisdiction: str | None
    investor_type: str | None
    whitelisted: bool
    kyc_granted: bool
    ofac_status: str
    created_at: datetime
