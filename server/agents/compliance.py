"""Compliance Agent — KYC, whitelist management, transfer validation."""

import json
import logging
import os
from datetime import datetime

from server.database import get_db
from server.hedera.consensus import log_agent_action

logger = logging.getLogger(__name__)

# Load jurisdiction rules
_jurisdictions_path = os.path.join(os.path.dirname(__file__), "..", "data", "jurisdictions.json")
with open(_jurisdictions_path) as f:
    JURISDICTIONS = json.load(f)

BLOCKED_COUNTRIES = {"IR", "KP", "CU", "SY"}  # OFAC-sanctioned


async def configure_compliance(asset_id: int, jurisdiction: str, investor_type: str) -> dict:
    """Configure compliance rules for an asset based on jurisdiction."""
    rules = JURISDICTIONS.get(jurisdiction, JURISDICTIONS.get("US"))
    db = await get_db()
    try:
        row = await db.execute_fetchone("SELECT topic_id FROM assets WHERE id = ?", (asset_id,))
        if row and row["topic_id"]:
            log_agent_action(
                row["topic_id"],
                agent="compliance",
                action="configure_compliance",
                details={
                    "asset_id": asset_id,
                    "jurisdiction": jurisdiction,
                    "investor_type": investor_type,
                    "rules": list(rules.get("regulations", {}).keys()),
                },
            )

        await db.execute(
            "INSERT INTO audit_log (asset_id, action, agent, details) VALUES (?, ?, ?, ?)",
            (asset_id, "configure_compliance", "compliance",
             json.dumps({"jurisdiction": jurisdiction, "investor_type": investor_type}))
        )
        await db.commit()
    finally:
        await db.close()

    return {
        "asset_id": asset_id,
        "jurisdiction": jurisdiction,
        "investor_type": investor_type,
        "regulations": list(rules.get("regulations", {}).keys()),
        "blocked_jurisdictions": rules.get("blocked_jurisdictions", []),
    }


async def check_kyc(account_id: str, asset_id: int) -> bool:
    """Check if an account is KYC-verified and whitelisted for an asset."""
    db = await get_db()
    try:
        row = await db.execute_fetchone(
            "SELECT whitelisted, kyc_status FROM holders WHERE account_id = ? AND asset_id = ?",
            (account_id, asset_id)
        )
        if not row:
            return False
        return bool(row["whitelisted"]) and row["kyc_status"] == "approved"
    finally:
        await db.close()


async def validate_transfer(asset_id: int, from_id: str, to_id: str, amount: int) -> tuple[bool, str]:
    """Validate a token transfer against compliance rules. Returns (approved, reason)."""
    db = await get_db()
    try:
        # Get asset info
        asset = await db.execute_fetchone("SELECT * FROM assets WHERE id = ?", (asset_id,))
        if not asset:
            return False, "Asset not found"

        if asset["status"] != "active":
            return False, f"Asset is {asset['status']}, transfers not allowed"

        jurisdiction = asset["jurisdiction"]
        rules = JURISDICTIONS.get(jurisdiction, JURISDICTIONS.get("US"))

        # Check sender is whitelisted
        sender = await db.execute_fetchone(
            "SELECT * FROM holders WHERE account_id = ? AND asset_id = ?",
            (from_id, asset_id)
        )
        if not sender or not sender["whitelisted"]:
            reason = f"Sender {from_id} is not whitelisted"
            await _log_blocked_transfer(db, asset, from_id, to_id, amount, reason)
            return False, reason

        # Check receiver is whitelisted
        receiver = await db.execute_fetchone(
            "SELECT * FROM holders WHERE account_id = ? AND asset_id = ?",
            (to_id, asset_id)
        )
        if not receiver or not receiver["whitelisted"]:
            reason = f"Receiver {to_id} is not whitelisted"
            await _log_blocked_transfer(db, asset, from_id, to_id, amount, reason)
            return False, reason

        # Check receiver jurisdiction not blocked
        if receiver["jurisdiction"] in BLOCKED_COUNTRIES:
            reason = f"Receiver jurisdiction {receiver['jurisdiction']} is sanctioned"
            await _log_blocked_transfer(db, asset, from_id, to_id, amount, reason)
            return False, reason

        blocked = set(rules.get("blocked_jurisdictions", []))
        if receiver["jurisdiction"] in blocked:
            reason = f"Receiver jurisdiction {receiver['jurisdiction']} is blocked for this asset"
            await _log_blocked_transfer(db, asset, from_id, to_id, amount, reason)
            return False, reason

        # Check sender has sufficient balance
        if sender["balance"] < amount:
            reason = f"Insufficient balance: {sender['balance']} < {amount}"
            await _log_blocked_transfer(db, asset, from_id, to_id, amount, reason)
            return False, reason

        # Check max holder limit
        for reg in rules.get("regulations", {}).values():
            max_holders = reg.get("max_holders")
            if max_holders:
                holder_count_row = await db.execute_fetchone(
                    "SELECT COUNT(*) as cnt FROM holders WHERE asset_id = ? AND whitelisted = 1",
                    (asset_id,)
                )
                if holder_count_row and holder_count_row["cnt"] >= max_holders:
                    if not receiver["whitelisted"]:
                        reason = f"Max holder limit ({max_holders}) reached"
                        await _log_blocked_transfer(db, asset, from_id, to_id, amount, reason)
                        return False, reason

        # Transfer approved
        if asset["topic_id"]:
            log_agent_action(
                asset["topic_id"],
                agent="compliance",
                action="transfer_approved",
                details={"from": from_id, "to": to_id, "amount": amount},
            )

        return True, "Transfer approved"
    finally:
        await db.close()


async def _log_blocked_transfer(db, asset, from_id, to_id, amount, reason):
    """Log a blocked transfer to both HCS and local audit."""
    if asset["topic_id"]:
        log_agent_action(
            asset["topic_id"],
            agent="compliance",
            action="transfer_blocked",
            details={"from": from_id, "to": to_id, "amount": amount, "reason": reason},
        )
    await db.execute(
        "INSERT INTO audit_log (asset_id, action, agent, details) VALUES (?, ?, ?, ?)",
        (asset["id"], "transfer_blocked", "compliance",
         json.dumps({"from": from_id, "to": to_id, "amount": amount, "reason": reason}))
    )
    await db.commit()
    logger.warning(f"Transfer blocked: {reason}")


async def add_to_whitelist(
    asset_id: int,
    account_id: str | None = None,
    jurisdiction: str = "US",
    investor_type: str = "accredited",
    create_account: bool = True,
) -> dict:
    """Add an investor to the whitelist. Creates real Hedera account, associates token, grants on-chain KYC."""
    from server.hedera.token import (
        create_account as hedera_create_account,
        associate_token, grant_kyc,
    )

    db = await get_db()
    try:
        # Get asset info
        asset = await db.execute_fetchone("SELECT * FROM assets WHERE id = ?", (asset_id,))
        if not asset:
            raise ValueError("Asset not found")

        # Check jurisdiction not blocked
        if jurisdiction in BLOCKED_COUNTRIES:
            raise ValueError(f"Jurisdiction {jurisdiction} is sanctioned — cannot whitelist")

        rules = JURISDICTIONS.get(asset["jurisdiction"], JURISDICTIONS.get("US"))
        blocked = set(rules.get("blocked_jurisdictions", []))
        if jurisdiction in blocked:
            raise ValueError(f"Jurisdiction {jurisdiction} is blocked for this asset")

        # Check investor type is allowed
        allowed_types = set()
        for reg in rules.get("regulations", {}).values():
            allowed_types.update(reg.get("investor_types", []))
        if investor_type not in allowed_types and allowed_types:
            raise ValueError(f"Investor type '{investor_type}' not allowed. Allowed: {allowed_types}")

        private_key_hex = None
        token_associated = False
        kyc_granted = False

        # 1. Create a real Hedera account if none provided
        if not account_id and create_account:
            account_id, private_key_hex = hedera_create_account(initial_balance_hbar=10)
            logger.info(f"Created Hedera account {account_id} for investor")

        # 2. Associate token with the account (on-chain)
        if asset["token_id"] and account_id:
            try:
                associate_token(account_id, asset["token_id"], private_key_hex)
                token_associated = True
                logger.info(f"Token {asset['token_id']} associated with {account_id}")
            except Exception as e:
                # May already be associated (auto-association or retry)
                if "ALREADY_ASSOCIATED" in str(e) or "already associated" in str(e).lower():
                    token_associated = True
                else:
                    logger.warning(f"Token association failed: {e}")

        # 3. Grant KYC on-chain
        if asset["token_id"] and account_id and token_associated:
            try:
                grant_kyc(asset["token_id"], account_id)
                kyc_granted = True
                logger.info(f"On-chain KYC granted for {account_id}")
            except Exception as e:
                if "ALREADY_GRANTED" in str(e):
                    kyc_granted = True
                else:
                    logger.warning(f"KYC grant failed: {e}")

        # 4. Store in database
        existing = await db.execute_fetchone(
            "SELECT id FROM holders WHERE account_id = ? AND asset_id = ?",
            (account_id, asset_id)
        )

        if existing:
            await db.execute(
                """UPDATE holders SET whitelisted=1, kyc_status='approved',
                   jurisdiction=?, investor_type=?, token_associated=?, kyc_granted=?
                   WHERE id=?""",
                (jurisdiction, investor_type, int(token_associated), int(kyc_granted), existing["id"])
            )
        else:
            await db.execute(
                """INSERT INTO holders (account_id, private_key, asset_id, balance, kyc_status,
                   jurisdiction, investor_type, whitelisted, token_associated, kyc_granted)
                   VALUES (?, ?, ?, 0, 'approved', ?, ?, 1, ?, ?)""",
                (account_id, private_key_hex, asset_id, jurisdiction, investor_type,
                 int(token_associated), int(kyc_granted))
            )
        await db.commit()

        # Fetch result before closing db
        row = await db.execute_fetchone(
            "SELECT * FROM holders WHERE account_id = ? AND asset_id = ?",
            (account_id, asset_id)
        )
        result = dict(row)
        result.pop("private_key", None)  # Never expose private keys in API responses
    finally:
        await db.close()

    # 5. Log to HCS (after db closed to avoid lock)
    if asset["topic_id"]:
        log_agent_action(
            asset["topic_id"],
            agent="compliance",
            action="whitelist_add",
            details={
                "account_id": account_id,
                "jurisdiction": jurisdiction,
                "investor_type": investor_type,
                "account_created": private_key_hex is not None,
                "token_associated": token_associated,
                "kyc_granted_onchain": kyc_granted,
            },
        )

    return result


async def remove_from_whitelist(asset_id: int, account_id: str) -> dict:
    """Remove an investor from the whitelist."""
    db = await get_db()
    try:
        asset = await db.execute_fetchone("SELECT topic_id FROM assets WHERE id = ?", (asset_id,))

        await db.execute(
            "UPDATE holders SET whitelisted=0, kyc_status='revoked' WHERE account_id=? AND asset_id=?",
            (account_id, asset_id)
        )
        await db.commit()

        if asset and asset["topic_id"]:
            log_agent_action(
                asset["topic_id"],
                agent="compliance",
                action="whitelist_remove",
                details={"account_id": account_id},
            )

        return {"account_id": account_id, "asset_id": asset_id, "whitelisted": False}
    finally:
        await db.close()


async def get_compliance_status(asset_id: int) -> dict:
    """Get compliance overview for an asset."""
    db = await get_db()
    try:
        asset = await db.execute_fetchone("SELECT * FROM assets WHERE id = ?", (asset_id,))
        if not asset:
            raise ValueError("Asset not found")

        total_holders = await db.execute_fetchone(
            "SELECT COUNT(*) as cnt FROM holders WHERE asset_id = ?", (asset_id,)
        )
        whitelisted = await db.execute_fetchone(
            "SELECT COUNT(*) as cnt FROM holders WHERE asset_id = ? AND whitelisted = 1", (asset_id,)
        )
        blocked_transfers = await db.execute_fetchone(
            "SELECT COUNT(*) as cnt FROM audit_log WHERE asset_id = ? AND action = 'transfer_blocked'",
            (asset_id,)
        )

        # Jurisdiction breakdown
        jurisdictions = await db.execute_fetchall(
            """SELECT jurisdiction, COUNT(*) as cnt FROM holders
               WHERE asset_id = ? AND whitelisted = 1 GROUP BY jurisdiction""",
            (asset_id,)
        )

        return {
            "asset_id": asset_id,
            "jurisdiction": asset["jurisdiction"],
            "investor_type": asset["investor_type"],
            "total_holders": total_holders["cnt"] if total_holders else 0,
            "whitelisted_holders": whitelisted["cnt"] if whitelisted else 0,
            "blocked_transfers": blocked_transfers["cnt"] if blocked_transfers else 0,
            "jurisdiction_breakdown": {row["jurisdiction"]: row["cnt"] for row in jurisdictions},
            "status": "compliant",
        }
    finally:
        await db.close()
