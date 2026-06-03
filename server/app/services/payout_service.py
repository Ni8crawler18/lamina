"""Payout service — coupon/dividend distribution in USDC.

Amount per holder comes from the asset-type handler (bond=semi-annual, etc.);
settlement goes through the chain adapter's pay_stable (USDC).
"""

from __future__ import annotations

import logging

from app.chains.registry import get_registry
from app.handlers import get_handler
from app.repositories.assets import AssetRepository
from app.repositories.events import EventRepository
from app.repositories.holders import HolderRepository
from app.services.audit_service import AuditService
from app.utils.aio import run_chain

logger = logging.getLogger(__name__)


class PayoutError(Exception):
    pass


class PayoutService:
    def __init__(self, session):
        self.session = session
        self.assets = AssetRepository(session)
        self.holders = HolderRepository(session)
        self.events = EventRepository(session)
        self.audit = AuditService(session)

    async def distribute_coupon(self, asset_id: int) -> dict:
        asset = await self.assets.get(asset_id)
        if not asset:
            raise PayoutError("Asset not found")
        if asset.status != "active":
            raise PayoutError(f"Asset is {asset.status}, cannot distribute coupon")
        if asset.coupon_rate <= 0:
            raise PayoutError("Asset has no coupon rate")

        adapter = get_registry().adapter(asset.chain)
        handler = get_handler(asset.asset_type)
        holders = await self.holders.holders_with_balance(asset_id, exclude=adapter.operator_ref())
        if not holders:
            return {"asset_id": asset_id, "message": "No eligible holders", "payments": []}

        payments = []
        for h in holders:
            units = handler.period_payout_units(h.balance, asset.decimals, asset.coupon_rate)
            if units <= 0:
                continue
            try:
                tx = await run_chain(adapter.pay_stable, h.account_id, units)
                payments.append({"account_id": h.account_id, "balance": h.balance,
                                 "coupon_usdc": round(units / 1e6, 6), "tx": tx, "status": "paid"})
            except Exception as e:
                logger.error("coupon payment failed for %s: %s", h.account_id, e)
                payments.append({"account_id": h.account_id, "coupon_usdc": round(units / 1e6, 6),
                                 "error": str(e), "status": "failed"})

        evt = await self.events.next_pending(asset_id, "coupon_payment")
        if evt:
            await self.events.mark_completed(evt.id)

        total = round(sum(p.get("coupon_usdc", 0) for p in payments if p["status"] == "paid"), 6)
        await self.audit.record(
            adapter, asset.topic_id, asset.id, "lifecycle", "coupon_distributed",
            {"coupon_rate": asset.coupon_rate, "num_holders": len(payments), "total_usdc": total},
        )
        return {
            "asset_id": asset_id, "chain": asset.chain, "coupon_rate": asset.coupon_rate,
            "periods_per_year": handler.periods_per_year, "payments": payments,
            "total_distributed_usdc": total,
        }
