"""US Treasury yield curve data from public APIs."""

import logging
from datetime import date

import aiohttp

logger = logging.getLogger(__name__)

# Treasury.gov XML feed for daily yields
TREASURY_XML_URL = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/all/{year}?type=daily_treasury_yield_curve&field_tdr_date_value={year}&page&_format=csv"

# Fallback: use a simple JSON API
TREASURY_API_URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/avg_interest_rates"


async def get_treasury_yields() -> dict:
    """Fetch current US Treasury yield curve."""
    try:
        params = {
            "sort": "-record_date",
            "page[size]": 10,
            "filter": "security_type_desc:eq:Treasury Bonds",
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(TREASURY_API_URL, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    records = data.get("data", [])
                    if records:
                        latest = records[0]
                        return {
                            "date": latest.get("record_date"),
                            "avg_interest_rate": float(latest.get("avg_interest_rate_amt", 0)),
                            "source": "treasury.gov",
                        }
    except Exception as e:
        logger.error(f"Failed to fetch treasury yields: {e}")

    # Fallback: reasonable default for demo
    return {
        "date": date.today().isoformat(),
        "1m": 5.25,
        "3m": 5.20,
        "6m": 5.10,
        "1y": 4.85,
        "2y": 4.60,
        "5y": 4.25,
        "10y": 4.40,
        "30y": 4.55,
        "source": "fallback",
    }


async def get_yield_for_duration(years: int) -> float:
    """Get yield rate for a specific bond duration."""
    yields = await get_treasury_yields()
    duration_map = {1: "1y", 2: "2y", 5: "5y", 10: "10y", 30: "30y"}
    key = duration_map.get(years, "5y")

    if key in yields:
        return float(yields[key])

    # If using real API data, use avg_interest_rate
    return float(yields.get("avg_interest_rate", 4.25))
