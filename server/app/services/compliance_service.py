"""Compliance service — KYC/whitelist, OFAC screening, transfer validation.

Chain-agnostic: jurisdiction rules and OFAC live here; on-chain KYC grants and audit
writes go through the asset's ChainAdapter. Exemptions (Reg D / Reg S) are treated as
ALTERNATIVES — a holder qualifies under one, then only that regulation's rules apply.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.chains.registry import get_registry
from app.constants.jurisdictions import (
    BLOCKED_COUNTRIES,
    US_JURISDICTIONS,
    rules_for,
)
from app.integrations.ofac.sdn import OFACScreener
from app.models.orm import Asset, Holder
from app.repositories.assets import AssetRepository
from app.repositories.holders import HolderRepository
from app.repositories.screening import ScreeningRepository
from app.services.audit_service import AuditService
from app.utils.aio import run_chain

logger = logging.getLogger(__name__)


class ComplianceError(Exception):
    """Raised when a compliance rule blocks an action (maps to HTTP 400)."""


class ComplianceService:
    def __init__(self, session):
        self.session = session
        self.assets = AssetRepository(session)
        self.holders = HolderRepository(session)
        self.screening = ScreeningRepository(session)
        self.audit = AuditService(session)

    def _adapter(self, asset: Asset):
        return get_registry().adapter(asset.chain)

    # ── KYC ──────────────────────────────────────────────────────────────────
    async def check_kyc(self, account_id: str, asset_id: int) -> bool:
        holder = await self.holders.get(account_id, asset_id)
        return bool(holder and holder.whitelisted and holder.kyc_status == "approved")

    # ── Whitelist onboarding ─────────────────────────────────────────────────
    async def add_to_whitelist(
        self, asset_id: int, account_id: str, jurisdiction: str = "US",
        investor_type: str = "accredited", name: str | None = None,
    ) -> Holder:
        asset = await self.assets.get(asset_id)
        if not asset:
            raise ComplianceError("Asset not found")
        if jurisdiction in BLOCKED_COUNTRIES:
            raise ComplianceError(f"Jurisdiction {jurisdiction} is sanctioned — cannot whitelist")

        rules = rules_for(asset.jurisdiction)
        if jurisdiction in set(rules.get("blocked_jurisdictions", [])):
            raise ComplianceError(f"Jurisdiction {jurisdiction} is blocked for this asset")

        # Investor type must qualify under at least one regulation (OR across exemptions)
        eligible = set()
        for reg in rules.get("regulations", {}).values():
            eligible |= set(reg.get("investor_types", []))
        if eligible and investor_type not in eligible:
            raise ComplianceError(
                f"Investor type '{investor_type}' not eligible. Allowed: {', '.join(sorted(eligible))}"
            )

        # OFAC screening
        ofac_status = "pending"
        ofac_at = None
        screener = OFACScreener.get_instance()
        if screener.loaded:
            result = screener.screen(name=name, address=account_id)
            ofac_at = datetime.now(timezone.utc)
            await self.screening.add(
                holder_account_id=account_id, holder_name=name, asset_id=asset_id,
                is_match=bool(result["is_match"]), score=result.get("score", 0),
                match_type=result.get("match_type"),
                matched_name=(result["details"] or {}).get("name") if result["details"] else None,
                matched_program=(result["details"] or {}).get("program") if result["details"] else None,
                action_taken="blocked" if result["is_match"] else "clear",
            )
            if result["is_match"]:
                matched = (result["details"] or {}).get("name", "unknown")
                await self.audit.record(
                    self._adapter(asset), asset.topic_id, asset.id, "compliance",
                    "ofac_screening_blocked",
                    {"name": name, "account_id": account_id, "matched_name": matched,
                     "score": result.get("score", 0)},
                )
                raise ComplianceError(
                    f"OFAC screening blocked: '{name or account_id}' matched sanctioned entity "
                    f"'{matched}' (score: {result.get('score', 0)}%)"
                )
            ofac_status = "clear"

        # On-chain KYC grant
        adapter = self._adapter(asset)
        kyc_granted = False
        if asset.token_id:
            try:
                await run_chain(adapter.grant_kyc, asset.token_id, account_id)
                kyc_granted = True
            except Exception as e:
                if "ALREADY" in str(e).upper():
                    kyc_granted = True
                else:
                    logger.warning("KYC grant failed for %s: %s", account_id, e)

        # Upsert holder
        holder = await self.holders.get(account_id, asset_id)
        if holder:
            holder.whitelisted = True
            holder.kyc_status = "approved"
            holder.jurisdiction = jurisdiction
            holder.investor_type = investor_type
            holder.token_associated = True
            holder.kyc_granted = kyc_granted
            holder.name = name
            holder.ofac_status = ofac_status
            holder.ofac_screened_at = ofac_at
        else:
            holder = await self.holders.create(
                account_id=account_id, asset_id=asset_id, name=name, balance=0,
                kyc_status="approved", jurisdiction=jurisdiction, investor_type=investor_type,
                whitelisted=True, token_associated=True, kyc_granted=kyc_granted,
                ofac_status=ofac_status, ofac_screened_at=ofac_at,
            )

        await self.audit.record(
            adapter, asset.topic_id, asset.id, "compliance", "whitelist_add",
            {"account_id": account_id, "jurisdiction": jurisdiction,
             "investor_type": investor_type, "kyc_granted_onchain": kyc_granted},
        )
        return holder

    async def remove_from_whitelist(self, asset_id: int, account_id: str) -> dict:
        asset = await self.assets.get(asset_id)
        holder = await self.holders.get(account_id, asset_id)
        if holder:
            holder.whitelisted = False
            holder.kyc_status = "revoked"
        if asset:
            await self.audit.record(
                self._adapter(asset), asset.topic_id, asset.id, "compliance",
                "whitelist_remove", {"account_id": account_id},
            )
        return {"account_id": account_id, "asset_id": asset_id, "whitelisted": False}

    # ── Transfer validation ──────────────────────────────────────────────────
    async def validate_transfer(
        self, asset_id: int, from_id: str, to_id: str, amount: int
    ) -> tuple[bool, str]:
        asset = await self.assets.get(asset_id)
        if not asset:
            return False, "Asset not found"
        if asset.status != "active":
            return False, f"Asset is {asset.status}, transfers not allowed"

        sender = await self.holders.get(from_id, asset_id)
        receiver = await self.holders.get(to_id, asset_id)
        if not sender or not sender.whitelisted:
            return await self._block(asset, from_id, to_id, amount, f"Sender {from_id} is not whitelisted")
        if not receiver or not receiver.whitelisted:
            return await self._block(asset, from_id, to_id, amount, f"Receiver {to_id} is not whitelisted")

        # OFAC on receiver
        screener = OFACScreener.get_instance()
        if screener.loaded:
            scr = screener.screen(name=receiver.name or None, address=to_id)
            if scr["is_match"]:
                matched = (scr["details"] or {}).get("name", "unknown")
                return await self._block(asset, from_id, to_id, amount,
                                         f"OFAC blocked receiver: matched '{matched}' ({scr['score']}%)")

        rules = rules_for(asset.jurisdiction)
        if receiver.jurisdiction in BLOCKED_COUNTRIES:
            return await self._block(asset, from_id, to_id, amount,
                                     f"Receiver jurisdiction {receiver.jurisdiction} is sanctioned")
        if receiver.jurisdiction in set(rules.get("blocked_jurisdictions", [])):
            return await self._block(asset, from_id, to_id, amount,
                                     f"Receiver jurisdiction {receiver.jurisdiction} is blocked")
        if sender.balance < amount:
            return await self._block(asset, from_id, to_id, amount,
                                     f"Insufficient balance: {sender.balance} < {amount}")

        # Jurisdiction regulations — alternative exemptions (OR), then per-reg rules
        regs = rules.get("regulations", {})
        recv_type = receiver.investor_type or ""
        matched_reg = None
        if recv_type != "treasury":
            eligible = set()
            for k, r in regs.items():
                t = set(r.get("investor_types", []))
                eligible |= t
                if recv_type in t and matched_reg is None:
                    matched_reg = k
            if eligible and matched_reg is None:
                return await self._block(asset, from_id, to_id, amount,
                                         f"Investor type '{recv_type}' not eligible. "
                                         f"Allowed: {', '.join(sorted(eligible))}")

        applicable = {k for k, r in regs.items() if not r.get("investor_types")}
        if matched_reg:
            applicable.add(matched_reg)

        for key in applicable:
            reg = regs[key]
            # lockup (sender's holding period; treasury exempt)
            lockup = reg.get("lockup_period_days", 0)
            if lockup and sender.investor_type != "treasury" and sender.created_at:
                lockup_end = sender.created_at.replace(tzinfo=None) + timedelta(days=lockup)
                if datetime.utcnow() < lockup_end:
                    days = (lockup_end - datetime.utcnow()).days
                    return await self._block(asset, from_id, to_id, amount,
                                             f"{reg.get('name', key)}: {lockup}-day lockup active, "
                                             f"{days} days remaining")
            # Reg S cross-border
            if key == "reg_s" and (receiver.jurisdiction or "") in US_JURISDICTIONS:
                return await self._block(asset, from_id, to_id, amount,
                                         "SEC Regulation S: cannot transfer to US persons")
            # max holders
            max_holders = reg.get("max_holders")
            if max_holders and await self.holders.count_whitelisted(asset_id) >= max_holders:
                return await self._block(asset, from_id, to_id, amount,
                                         f"{reg.get('name', key)}: max holder limit ({max_holders}) reached")

        await self.audit.record(
            self._adapter(asset), asset.topic_id, asset.id, "compliance", "transfer_approved",
            {"from": from_id, "to": to_id, "amount": amount},
        )
        return True, "Transfer approved"

    async def _block(self, asset, from_id, to_id, amount, reason) -> tuple[bool, str]:
        await self.audit.record(
            self._adapter(asset), asset.topic_id, asset.id, "compliance", "transfer_blocked",
            {"from": from_id, "to": to_id, "amount": amount, "reason": reason},
        )
        logger.warning("Transfer blocked: %s", reason)
        return False, reason

    # ── Status ───────────────────────────────────────────────────────────────
    async def get_compliance_status(self, asset_id: int) -> dict:
        asset = await self.assets.get(asset_id)
        if not asset:
            raise ComplianceError("Asset not found")
        holders = await self.holders.list_for_asset(asset_id)
        whitelisted = [h for h in holders if h.whitelisted]
        rules = rules_for(asset.jurisdiction)
        return {
            "asset_id": asset_id,
            "chain": asset.chain,
            "jurisdiction": asset.jurisdiction,
            "total_holders": len(holders),
            "whitelisted": len(whitelisted),
            "flagged_ofac": len([h for h in holders if h.ofac_status == "flagged"]),
            "regulations": list(rules.get("regulations", {}).keys()),
            "blocked_jurisdictions": rules.get("blocked_jurisdictions", []),
        }
