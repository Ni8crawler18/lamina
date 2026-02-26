"""OFAC screening request/response models."""

from pydantic import BaseModel
from typing import Optional


class ScreeningRequest(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None


class MatchDetails(BaseModel):
    entry_id: Optional[int] = None
    name: Optional[str] = None
    sdn_type: Optional[str] = None
    program: Optional[str] = None


class ScreeningResponse(BaseModel):
    is_match: bool
    score: float = 0
    match_type: Optional[str] = None
    details: Optional[MatchDetails] = None
    screened_at: str


class OFACStatusResponse(BaseModel):
    loaded: bool
    entry_count: int = 0
    address_count: int = 0
    loaded_at: Optional[str] = None
