"""Scheduled event data models."""

from pydantic import BaseModel
from typing import Optional


class EventCreate(BaseModel):
    asset_id: int
    event_type: str  # coupon_payment, nav_update, maturity, report
    scheduled_at: str


class EventResponse(BaseModel):
    id: int
    asset_id: int
    event_type: str
    scheduled_at: str
    executed_at: Optional[str] = None
    status: str
    tx_hash: Optional[str] = None
    details: Optional[str] = None


class UpcomingEventResponse(EventResponse):
    asset_name: str
    asset_symbol: str
