"""Issuance service — tokenize an asset on a chosen chain.

Deploys a compliant token via the chain adapter, persists it, schedules its
lifecycle events, whitelists the treasury, and writes the audit trail.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

from app.chains.registry import get_registry
from app.constants.jurisdictions import ASSET_TYPES
from app.handlers import get_handler
from app.models.orm import Asset
from app.repositories.assets import AssetRepository
from app.repositories.events import EventRepository
from app.repositories.holders import HolderRepository
from app.services.audit_service import AuditService
from app.utils.aio import run_chain

logger = logging.getLogger(__name__)


def _coupon_interval_days(asset_type: str) -> int:
    """Scheduling cadence derived from the asset-type handler's periods_per_year,
    instead of one hardcoded interval for every type."""
    periods = get_handler(asset_type).periods_per_year
    return 365 // periods if periods else 365


class IssuanceService:
    def __init__(self, session):
        self.session = session
        self.assets = AssetRepository(session)
        self.holders = HolderRepository(session)
        self.events = EventRepository(session)
        self.audit = AuditService(session)

    async def issue_asset(
        self, *, chain: str, name: str, symbol: str, total_supply: int,
        decimals: int = 2, coupon_rate: float = 0.0, maturity_date: str | None = None,
        jurisdiction: str = "US", investor_type: str = "accredited", asset_type: str = "bond",
        owner: str | None = None, issuer_name: str | None = None, metadata: dict | None = None,
    ) -> Asset:
        adapter = get_registry().adapter(chain)  # raises if chain unknown/disabled

        type_rules = ASSET_TYPES.get(asset_type, {})
        # coupon_rate is the shared periodic-payout rate field: a bond's coupon and an
        # equity/fund/real_estate's dividend are the same underlying mechanism.
        pays_periodically = type_rules.get("has_coupon", True) or type_rules.get("has_dividends", False)
        if not pays_periodically and coupon_rate:
            raise ValueError(f"asset_type '{asset_type}' does not support a coupon_rate")
        if not type_rules.get("has_maturity", True) and maturity_date:
            raise ValueError(f"asset_type '{asset_type}' does not support a maturity_date")
        missing = [k for k in type_rules.get("required_metadata", []) if not (metadata or {}).get(k)]
        if missing:
            raise ValueError(f"asset_type '{asset_type}' requires metadata field(s): {', '.join(missing)}")

        # Canonical coupon_rate is a fraction (0.04 == 4%). The UI form already
        # divides by 100; normalise other callers (AI agent / API) that pass a
        # whole-percent value so a 4% coupon never persists as 4.0 (→ 400%).
        if coupon_rate and coupon_rate > 1:
            coupon_rate = coupon_rate / 100

        # 1. Deploy token + audit topic on-chain
        dep = await run_chain(
            adapter.deploy_asset_token, name, symbol, decimals, total_supply, asset_type, jurisdiction
        )

        # 2. Persist
        nav = total_supply / (10 ** decimals) if decimals > 0 else float(total_supply)
        asset = await self.assets.create(
            chain=chain, owner=owner, issuer_name=issuer_name, name=name, symbol=symbol,
            token_id=dep.token_ref, topic_id=dep.audit_topic_ref,
            asset_type=asset_type, total_supply=total_supply, decimals=decimals,
            coupon_rate=coupon_rate, maturity_date=maturity_date, nav=nav,
            status="active", jurisdiction=jurisdiction, investor_type=investor_type,
            metadata_json=json.dumps(metadata) if metadata else None,
        )

        # 3. Audit (on-chain + DB)
        await self.audit.record(
            adapter, asset.topic_id, asset.id, "lifecycle", "asset_issued",
            {"name": name, "symbol": symbol, "token_ref": dep.token_ref,
             "total_supply": total_supply, "coupon_rate": coupon_rate,
             "maturity_date": maturity_date, "jurisdiction": jurisdiction,
             "investor_type": investor_type, "asset_type": asset_type, "chain": chain},
        )
        await self.audit.record(
            adapter, asset.topic_id, asset.id, "compliance", "configure_compliance",
            {"jurisdiction": jurisdiction, "investor_type": investor_type},
        )

        # 4. Schedule lifecycle events
        await self._schedule_coupons(asset.id, asset_type, coupon_rate, maturity_date)
        if maturity_date:
            await self.events.create(
                asset_id=asset.id, event_type="maturity",
                scheduled_at=datetime.fromisoformat(maturity_date),
            )

        # 5. Whitelist the treasury (operator holds the full supply at issuance)
        await self.holders.create(
            account_id=adapter.operator_ref(), asset_id=asset.id, name="Treasury",
            balance=total_supply, kyc_status="approved", jurisdiction=jurisdiction,
            investor_type="treasury", whitelisted=True, token_associated=True, kyc_granted=True,
            ofac_status="exempt",
        )
        return asset

    async def purchase(self, asset_id: int, buyer: str, amount: int) -> dict:
        """Primary-market purchase: treasury → investor, compliance-validated."""
        from app.services.compliance_service import ComplianceService

        asset = await self.assets.get(asset_id)
        if not asset:
            raise ValueError("Asset not found")
        adapter = get_registry().adapter(asset.chain)
        treasury = adapter.operator_ref()

        compliance = ComplianceService(self.session)
        ok, reason = await compliance.validate_transfer(asset_id, treasury, buyer, amount)
        if not ok:
            raise PermissionError(reason)

        tx = await run_chain(adapter.transfer_token, asset.token_id, buyer, amount)
        await self.holders.adjust_balance(buyer, asset_id, amount)
        await self.holders.adjust_balance(treasury, asset_id, -amount)
        await self.audit.record(
            adapter, asset.topic_id, asset.id, "compliance", "purchase",
            {"buyer": buyer, "amount": amount, "tx": tx},
        )
        return {"asset_id": asset_id, "chain": asset.chain, "buyer": buyer,
                "amount": amount, "tx": tx, "status": "completed"}

    async def _schedule_coupons(
        self, asset_id: int, asset_type: str, coupon_rate: float, maturity_date: str | None
    ) -> None:
        if coupon_rate <= 0:
            return
        interval_days = _coupon_interval_days(asset_type)
        now = datetime.utcnow()
        end = datetime.fromisoformat(maturity_date) if maturity_date else now + timedelta(days=365 * 5)
        nxt = now + timedelta(days=interval_days)
        while nxt < end:
            await self.events.create(
                asset_id=asset_id, event_type="coupon_payment", scheduled_at=nxt
            )
            nxt += timedelta(days=interval_days)
