"""Asset-type handler tests: real_estate and carbon_credits registration and cadence."""

from app.handlers import CarbonCreditHandler, RealEstateHandler, get_handler
from app.services.issuance_service import _coupon_interval_days


def test_get_handler_returns_real_estate_handler():
    h = get_handler("real_estate")
    assert isinstance(h, RealEstateHandler)
    assert h.periods_per_year == 12


def test_get_handler_returns_carbon_credit_handler():
    h = get_handler("carbon_credits")
    assert isinstance(h, CarbonCreditHandler)
    assert h.period_payout_units(1_000_000, 2, 0.05) == 0


def test_coupon_interval_matches_handler_cadence():
    assert _coupon_interval_days("bond") == 182  # semi-annual
    assert _coupon_interval_days("equity") == 91  # quarterly
    assert _coupon_interval_days("real_estate") == 30  # monthly
    assert _coupon_interval_days("carbon_credits") == 365  # no periodic payout
