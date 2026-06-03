"""Asset-type handler registry."""

from __future__ import annotations

from app.handlers.base import AssetTypeHandler, _RateHandler


class BondHandler(_RateHandler):
    asset_type = "bond"
    periods_per_year = 2  # semi-annual coupons


class EquityHandler(_RateHandler):
    asset_type = "equity"
    periods_per_year = 4  # quarterly dividends


class FundHandler(_RateHandler):
    asset_type = "fund"
    periods_per_year = 4  # quarterly distributions


_HANDLERS: dict[str, AssetTypeHandler] = {
    h.asset_type: h for h in (BondHandler(), EquityHandler(), FundHandler())
}

_DEFAULT = BondHandler()


def get_handler(asset_type: str) -> AssetTypeHandler:
    return _HANDLERS.get(asset_type, _DEFAULT)
