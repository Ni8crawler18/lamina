"""Asset-type valuation sources — how NAV is recomputed on a refresh.

Strategy pattern, mirroring app/handlers/: revalue code asks
`get_valuation_source(asset_type)` for the right pricing logic instead of
branching on type inline. Add a new asset type's valuation = add a class here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.integrations.oracle.treasury_rates import get_yield_for_duration


class ValuationSource(ABC):
    @abstractmethod
    async def revalue(self, asset) -> float:
        """Return the asset's new NAV. `asset` is the ORM Asset row (read-only here)."""


class BondFundValuationSource(ValuationSource):
    """Bond/equity/fund: price off a coupon-rate-vs-treasury-yield factor."""

    async def revalue(self, asset) -> float:
        face_value = asset.total_supply / (10 ** asset.decimals)
        current_yield = await get_yield_for_duration(5)
        if current_yield > 0 and asset.coupon_rate > 0:
            price_factor = min(max(asset.coupon_rate / (current_yield / 100), 0.8), 1.2)
            return round(face_value * price_factor, 2)
        return round(face_value, 2)


class ManualValuationSource(ValuationSource):
    """No live feed yet (real-estate appraisal / carbon-credit market price) — NAV is
    updated manually via LifecycleService.update_nav; a refresh is a no-op that keeps
    the last-set value. Phase-1 stub with a clear seam to plug in a real feed later."""

    async def revalue(self, asset) -> float:
        return asset.nav


_BOND_FUND = BondFundValuationSource()
_MANUAL = ManualValuationSource()

_SOURCES: dict[str, ValuationSource] = {
    "bond": _BOND_FUND,
    "equity": _BOND_FUND,
    "fund": _BOND_FUND,
    "real_estate": _MANUAL,
    "carbon_credits": _MANUAL,
}


def get_valuation_source(asset_type: str) -> ValuationSource:
    return _SOURCES.get(asset_type, _BOND_FUND)
