"""Lifecycle service — NAV revaluation and maturity settlement."""

from __future__ import annotations

import logging

from app.chains.registry import get_registry
from app.integrations.oracle.valuation import get_valuation_source
from app.repositories.assets import AssetRepository
from app.repositories.holders import HolderRepository
from app.services.audit_service import AuditService
from app.utils.aio import run_chain

logger = logging.getLogger(__name__)

USDC_DECIMALS = 6


class LifecycleError(Exception):
    pass


class LifecycleService:
    def __init__(self, session):
        self.session = session
        self.assets = AssetRepository(session)
        self.holders = HolderRepository(session)
        self.audit = AuditService(session)

    async def update_nav(self, asset_id: int, new_nav: float) -> dict:
        asset = await self.assets.get(asset_id)
        if not asset:
            raise LifecycleError("Asset not found")
        old_nav = asset.nav
        await self.assets.set_nav(asset_id, new_nav)
        await self.audit.record(
            get_registry().adapter(asset.chain), asset.topic_id, asset.id,
            "lifecycle", "nav_updated", {"old_nav": old_nav, "new_nav": new_nav},
        )
        return {"asset_id": asset_id, "old_nav": old_nav, "new_nav": new_nav}

    async def update_nav_from_oracle(self, asset_id: int) -> dict:
        asset = await self.assets.get(asset_id)
        if not asset:
            raise LifecycleError("Asset not found")
        new_nav = await get_valuation_source(asset.asset_type).revalue(asset)
        return await self.update_nav(asset_id, round(new_nav, 2))

    async def execute_maturity(self, asset_id: int) -> dict:
        asset = await self.assets.get(asset_id)
        if not asset:
            raise LifecycleError("Asset not found")
        if asset.status != "active":
            raise LifecycleError(f"Asset is already {asset.status}")

        adapter = get_registry().adapter(asset.chain)
        operator = adapter.operator_ref()
        holders = await self.holders.holders_with_balance(asset_id, exclude=operator)

        redemptions, total_wiped = [], 0
        for h in holders:
            r = {"account_id": h.account_id, "balance": h.balance}
            if asset.token_id and h.balance > 0:
                try:
                    await run_chain(adapter.force_redeem, asset.token_id, h.account_id, h.balance)
                    r["token_wipe"] = "success"
                    total_wiped += h.balance
                except Exception as e:
                    r["token_wipe"] = f"failed: {e}"
            # principal = face value in USDC
            principal_usd = h.balance / (10 ** asset.decimals)
            units = int(round(principal_usd * (10 ** USDC_DECIMALS)))
            try:
                await run_chain(adapter.pay_stable, h.account_id, units)
                r["principal_usdc"] = round(principal_usd, 6)
                r["principal_return"] = "success"
            except Exception as e:
                r["principal_return"] = f"failed: {e}"
            r["status"] = "redeemed"
            redemptions.append(r)
            h.balance = 0

        # Burn treasury remainder
        treasury = await self.holders.get(operator, asset_id)
        burned = treasury.balance if treasury else 0
        burn_result = "not_attempted"
        if burned > 0 and asset.token_id:
            try:
                await run_chain(adapter.burn, asset.token_id, burned)
                burn_result = "success"
                treasury.balance = 0
            except Exception as e:
                burn_result = f"failed: {e}"

        await self.assets.set_status(asset_id, "matured")
        await self.audit.record(
            adapter, asset.topic_id, asset.id, "lifecycle", "maturity_settled",
            {"tokens_wiped": total_wiped, "tokens_burned": burned, "redemptions": len(redemptions)},
        )
        return {
            "asset_id": asset_id, "chain": asset.chain, "token_id": asset.token_id,
            "status": "matured", "tokens_wiped": total_wiped, "tokens_burned": burned,
            "burn_result": burn_result, "redemptions": redemptions,
        }

    async def retire_credits(self, asset_id: int, holder_ref: str, amount: int) -> dict:
        """On-demand, per-holder carbon-credit retirement — a permanent burn with no
        principal returned, distinct from bond/equity maturity redemption. A holder
        can retire any part of their balance at any time; the asset only becomes
        fully 'retired' once every credit ever issued has been retired by someone."""
        asset = await self.assets.get(asset_id)
        if not asset:
            raise LifecycleError("Asset not found")
        if asset.asset_type != "carbon_credits":
            raise LifecycleError("retire_credits only applies to carbon_credits assets")
        if asset.status != "active":
            raise LifecycleError(f"Asset is already {asset.status}")

        holder = await self.holders.get(holder_ref, asset_id)
        if not holder or holder.balance < amount:
            raise LifecycleError("Insufficient balance to retire")

        adapter = get_registry().adapter(asset.chain)
        await run_chain(adapter.force_redeem, asset.token_id, holder_ref, amount)
        holder.balance -= amount

        remaining = sum(h.balance for h in await self.holders.list_for_asset(asset_id))
        if remaining <= 0:
            await self.assets.set_status(asset_id, "retired")

        await self.audit.record(
            adapter, asset.topic_id, asset.id, "lifecycle", "credits_retired",
            {"holder": holder_ref, "amount": amount, "remaining_supply": remaining},
        )
        return {
            "asset_id": asset_id, "chain": asset.chain, "holder": holder_ref,
            "amount_retired": amount, "remaining_supply": remaining,
            "status": "retired" if remaining <= 0 else "active",
        }
