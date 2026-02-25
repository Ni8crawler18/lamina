"""Foreign exchange rate data for cross-border asset support."""

import logging

import aiohttp

logger = logging.getLogger(__name__)

FX_API_URL = "https://open.er-api.com/v6/latest/USD"


async def get_fx_rates(base: str = "USD") -> dict:
    """Fetch current FX rates against USD."""
    try:
        url = f"https://open.er-api.com/v6/latest/{base}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "base": base,
                        "rates": data.get("rates", {}),
                        "time_last_update_utc": data.get("time_last_update_utc"),
                        "source": "exchangerate-api",
                    }
    except Exception as e:
        logger.error(f"Failed to fetch FX rates: {e}")

    # Fallback defaults
    return {
        "base": "USD",
        "rates": {"EUR": 0.92, "GBP": 0.79, "SGD": 1.34, "JPY": 150.0, "CHF": 0.88},
        "source": "fallback",
    }


async def convert_currency(amount: float, from_currency: str, to_currency: str) -> float:
    """Convert amount between currencies."""
    if from_currency == to_currency:
        return amount

    rates_data = await get_fx_rates(from_currency)
    rates = rates_data.get("rates", {})

    if to_currency in rates:
        return amount * rates[to_currency]

    logger.warning(f"Rate not found for {from_currency}->{to_currency}, returning original")
    return amount
