"""Chain schema (for the chain picker)."""

from __future__ import annotations

from pydantic import BaseModel


class ChainOut(BaseModel):
    slug: str
    name: str
    family: str
    chain_id: int
    native_symbol: str
    explorer_url: str
    enabled: bool
