"""Issuance service — tokenize an asset on a chosen chain.

Deploys a compliant token via the chain adapter, persists it, schedules its
lifecycle events, whitelists the treasury, and writes the audit trail.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from app.chains.registry import get_registry
from app.models.orm import Asset
from app.repositories.assets import AssetRepository
from app.repositories.events import EventRepository
from app.repositories.holders import HolderRepository
from app.services.audit_service import AuditService
from app.utils.aio import run_chain

logger = logging.getLogger(__name__)

_COUPON_INTERVAL_DAYS = 182  # semi-annual


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
        owner: str | None = None,
    ) -> Asset:
        adapter = get_registry().adapter(chain)  # raises if chain unknown/disabled

        # 1. Deploy token + audit topic on-chain
        dep = await run_chain(
            adapter.deploy_asset_token, name, symbol, decimals, total_supply, asset_type, jurisdiction
        )

        # 2. Persist
        nav = total_supply / (10 ** decimals) if decimals > 0 else float(total_supply)
        asset = await self.assets.create(
            chain=chain, owner=owner, name=name, symbol=symbol,
            token_id=dep.token_ref, topic_id=dep.audit_topic_ref,
            asset_type=asset_type, total_supply=total_supply, decimals=decimals,
            coupon_rate=coupon_rate, maturity_date=maturity_date, nav=nav,
            status="active", jurisdiction=jurisdiction, investor_type=investor_type,
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
        await self._schedule_coupons(asset.id, coupon_rate, maturity_date)
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

    async def _schedule_coupons(self, asset_id: int, coupon_rate: float, maturity_date: str | None) -> None:
        if coupon_rate <= 0:
            return
        now = datetime.utcnow()
        end = datetime.fromisoformat(maturity_date) if maturity_date else now + timedelta(days=365 * 5)
        nxt = now + timedelta(days=_COUPON_INTERVAL_DAYS)
        while nxt < end:
            await self.events.create(
                asset_id=asset_id, event_type="coupon_payment", scheduled_at=nxt
            )
            nxt += timedelta(days=_COUPON_INTERVAL_DAYS)
