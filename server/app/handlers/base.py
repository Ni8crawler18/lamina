"""Asset-type handlers — per-type behavior (payout cadence, redemption).

Strategy pattern: payout/lifecycle services ask `get_handler(asset_type)` for the
right rules instead of branching on type inline. Add a new asset type = add a file.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

USDC_DECIMALS = 6


class AssetTypeHandler(ABC):
    asset_type: str
    periods_per_year: int

    @abstractmethod
    def period_payout_units(self, balance: int, token_decimals: int, annual_rate_pct: float) -> int:
        """USDC micro-units owed to a holder for one payout period.

        Face value of a holding = balance / 10^token_decimals (1 token unit = $1 face).
        """


class _RateHandler(AssetTypeHandler):
    """Shared: payout = face_value * (annual_rate% / periods_per_year), in USDC units."""

    def period_payout_units(self, balance: int, token_decimals: int, annual_rate_pct: float) -> int:
        face_value = balance / (10 ** token_decimals)
        per_period_usd = face_value * (annual_rate_pct / 100) / self.periods_per_year
        return int(round(per_period_usd * (10 ** USDC_DECIMALS)))
