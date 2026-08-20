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


class RealEstateHandler(_RateHandler):
    asset_type = "real_estate"
    periods_per_year = 12  # monthly rental distributions


class CarbonCreditHandler(AssetTypeHandler):
    """Carbon credits carry no periodic income — they are held, then retired on use."""

    asset_type = "carbon_credits"
    periods_per_year = 0

    def period_payout_units(self, balance: int, token_decimals: int, annual_rate: float) -> int:
        return 0


_HANDLERS: dict[str, AssetTypeHandler] = {
    h.asset_type: h
    for h in (BondHandler(), EquityHandler(), FundHandler(), RealEstateHandler(), CarbonCreditHandler())
}

_DEFAULT = BondHandler()


def get_handler(asset_type: str) -> AssetTypeHandler:
    return _HANDLERS.get(asset_type, _DEFAULT)
