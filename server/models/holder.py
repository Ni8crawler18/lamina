"""Token holder data models."""

from pydantic import BaseModel
from typing import Optional


class HolderCreate(BaseModel):
    account_id: Optional[str] = None  # If None, a new Hedera account is created
    jurisdiction: str = "US"
    investor_type: str = "accredited"


class HolderResponse(BaseModel):
    id: int
    account_id: str
    asset_id: int
    balance: int
    kyc_status: str
    jurisdiction: str
    investor_type: str
    whitelisted: bool
    token_associated: Optional[bool] = False
    kyc_granted: Optional[bool] = False
    created_at: str


class HolderUpdate(BaseModel):
    balance: Optional[int] = None
    kyc_status: Optional[str] = None
    whitelisted: Optional[bool] = None
