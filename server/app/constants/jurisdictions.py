"""Jurisdiction & asset-type rules, loaded from config/*.json once at import.

These are business rules (Reg D/S, MiFID II, FCA, MAS; asset-type metadata), not
secrets — they live in backend/config/ and are read-only at runtime.
"""

import json
from pathlib import Path

_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"

JURISDICTIONS: dict = json.loads((_CONFIG_DIR / "jurisdictions.json").read_text())
ASSET_TYPES: dict = json.loads((_CONFIG_DIR / "asset_types.json").read_text())

# OFAC-sanctioned countries — never whitelistable.
BLOCKED_COUNTRIES = {"IR", "KP", "CU", "SY"}

# Jurisdictions treated as "US person" for Reg S cross-border restrictions.
US_JURISDICTIONS = {"US"}


def rules_for(jurisdiction: str) -> dict:
    return JURISDICTIONS.get(jurisdiction, JURISDICTIONS.get("US", {}))
