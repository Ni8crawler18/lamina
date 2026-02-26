"""Lifecycle Agent — Asset issuance, coupon payments, NAV updates, maturity settlement."""

import json
import logging
from datetime import datetime, timedelta

from server.database import get_db
from server.hedera.token import create_token, mint_tokens, burn_tokens, transfer_tokens
from server.hedera.consensus import create_topic, log_agent_action
from server.hedera.client import get_operator_account_id

logger = logging.getLogger(__name__)


async def issue_asset(
    name: str,
    symbol: str,
    total_supply: int,
    decimals: int = 2,
    coupon_rate: float = 0.0,
    maturity_date: str | None = None,
    jurisdiction: str = "US",
    investor_type: str = "accredited",
    asset_type: str = "bond",
) -> dict:
    """Issue a new tokenized asset: create HTS token, HCS topic, store in DB, schedule events."""

    # 1. Create HCS topic for audit logging
    topic_id = create_topic(memo=f"Lamina audit: {name} ({symbol})")
    logger.info(f"Created audit topic: {topic_id}")

    # 2. Create HTS token
    token_id = create_token(
        name=name,
        symbol=symbol,
        decimals=decimals,
        initial_supply=total_supply,
    )
    logger.info(f"Created token: {token_id}")

    # 3. Log issuance to HCS
    log_agent_action(
        topic_id,
        agent="lifecycle",
        action="asset_issued",
        details={
            "name": name,
            "symbol": symbol,
            "token_id": token_id,
            "total_supply": total_supply,
            "coupon_rate": coupon_rate,
            "maturity_date": maturity_date,
            "jurisdiction": jurisdiction,
            "investor_type": investor_type,
            "asset_type": asset_type,
        },
    )

    # 4. Store in database
    nav = total_supply / (10 ** decimals) if decimals > 0 else float(total_supply)

    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO assets (name, symbol, token_id, topic_id, asset_type, total_supply,
               decimals, coupon_rate, maturity_date, nav, status, jurisdiction, investor_type)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)""",
            (name, symbol, token_id, topic_id, asset_type, total_supply,
             decimals, coupon_rate, maturity_date, nav, jurisdiction, investor_type)
        )
        asset_id = cursor.lastrowid

        # 5. Schedule recurring events
        await _schedule_coupon_payments(db, asset_id, coupon_rate, maturity_date)
        await _schedule_maturity(db, asset_id, maturity_date)

        # 6. Whitelist the treasury account (operator)
        operator = str(get_operator_account_id())
        await db.execute(
            """INSERT OR IGNORE INTO holders (account_id, asset_id, balance, kyc_status, jurisdiction, investor_type, whitelisted)
               VALUES (?, ?, ?, 'approved', ?, 'treasury', 1)""",
            (operator, asset_id, total_supply, jurisdiction)
        )

        # 7. Log audit entry
        await db.execute(
            "INSERT INTO audit_log (asset_id, action, agent, details) VALUES (?, ?, ?, ?)",
            (asset_id, "asset_issued", "lifecycle",
             json.dumps({"token_id": token_id, "topic_id": topic_id, "total_supply": total_supply}))
        )
        await db.execute(
            "INSERT INTO audit_log (asset_id, action, agent, details) VALUES (?, ?, ?, ?)",
            (asset_id, "configure_compliance", "compliance",
             json.dumps({"jurisdiction": jurisdiction, "investor_type": investor_type}))
        )
        await db.commit()

        row = await db.execute_fetchone("SELECT * FROM assets WHERE id = ?", (asset_id,))
        result = dict(row)
    finally:
        await db.close()

    # 8. Log compliance configuration to HCS (after db closed to avoid locks)
    try:
        log_agent_action(
            topic_id,
            agent="compliance",
            action="configure_compliance",
            details={"asset_id": result["id"], "jurisdiction": jurisdiction, "investor_type": investor_type},
        )
    except Exception as e:
        logger.warning(f"Failed to log compliance config to HCS: {e}")

    return result


async def _schedule_coupon_payments(db, asset_id: int, coupon_rate: float, maturity_date: str | None):
    """Schedule coupon payment events based on coupon rate and frequency."""
    if coupon_rate <= 0:
        return

    now = datetime.utcnow()
    end = datetime.fromisoformat(maturity_date) if maturity_date else now + timedelta(days=365 * 5)

    # Semi-annual coupon payments
    interval_days = 182  # ~6 months
    next_payment = now + timedelta(days=interval_days)

    while next_payment < end:
        await db.execute(
            "INSERT INTO scheduled_events (asset_id, event_type, scheduled_at, status) VALUES (?, ?, ?, 'pending')",
            (asset_id, "coupon_payment", next_payment.isoformat())
        )
        next_payment += timedelta(days=interval_days)

    await db.commit()


async def _schedule_maturity(db, asset_id: int, maturity_date: str | None):
    """Schedule maturity settlement event."""
    if not maturity_date:
        return

    await db.execute(
        "INSERT INTO scheduled_events (asset_id, event_type, scheduled_at, status) VALUES (?, ?, ?, 'pending')",
        (asset_id, "maturity", maturity_date)
    )
    await db.commit()


async def distribute_coupon(asset_id: int) -> dict:
    """Distribute coupon payment as real HBAR transfers to all token holders proportionally."""
    from server.hedera.token import transfer_hbar

    db = await get_db()
    try:
        asset = await db.execute_fetchone("SELECT * FROM assets WHERE id = ?", (asset_id,))
        if not asset:
            raise ValueError("Asset not found")
        if asset["status"] != "active":
            raise ValueError(f"Asset is {asset['status']}, cannot distribute coupon")
        if asset["coupon_rate"] <= 0:
            raise ValueError("Asset has no coupon rate")

        # Get all holders with non-zero balance (excluding treasury)
        operator = str(get_operator_account_id())
        holders = await db.execute_fetchall(
            "SELECT * FROM holders WHERE asset_id = ? AND whitelisted = 1 AND balance > 0 AND account_id != ?",
            (asset_id, operator)
        )

        if not holders:
            return {"asset_id": asset_id, "message": "No eligible holders for coupon distribution", "payments": []}

        # Calculate per-period coupon (semi-annual = annual_rate / 2)
        # Coupon paid in HBAR (1 HBAR per token unit for demo scale)
        total_supply = asset["total_supply"]
        annual_rate = asset["coupon_rate"]
        period_rate = annual_rate / 2  # Semi-annual

        payments = []
        for holder in holders:
            proportion = holder["balance"] / total_supply
            # Coupon in tinybars: scale to small amounts for testnet
            # E.g., 4.5% annual on 1000 tokens = 22.5 tokens worth per period
            coupon_tokens = int(holder["balance"] * period_rate)
            # Convert to tinybars (1 HBAR = 100_000_000 tinybars, use 1000 tinybars per token unit for demo)
            coupon_tinybars = max(coupon_tokens, 1)  # At least 1 tinybar

            if coupon_tinybars > 0:
                # Real HBAR transfer from operator to holder
                try:
                    tx_id = transfer_hbar(holder["account_id"], coupon_tinybars)
                    payments.append({
                        "account_id": holder["account_id"],
                        "balance": holder["balance"],
                        "coupon_amount": coupon_tinybars,
                        "tx_id": tx_id,
                        "status": "paid",
                    })
                    logger.info(f"Coupon paid: {coupon_tinybars} tinybar to {holder['account_id']}")
                except Exception as e:
                    payments.append({
                        "account_id": holder["account_id"],
                        "balance": holder["balance"],
                        "coupon_amount": coupon_tinybars,
                        "error": str(e),
                        "status": "failed",
                    })
                    logger.error(f"Coupon payment failed for {holder['account_id']}: {e}")

        topic_id = asset["topic_id"]

        # Mark the next pending coupon_payment event as completed
        next_event = await db.execute_fetchone(
            "SELECT id FROM scheduled_events WHERE asset_id = ? AND event_type = 'coupon_payment' AND status = 'pending' ORDER BY scheduled_at ASC LIMIT 1",
            (asset_id,)
        )
        if next_event:
            await db.execute(
                "UPDATE scheduled_events SET status = 'completed', executed_at = datetime('now') WHERE id = ?",
                (next_event["id"],)
            )

        # Record in audit log
        await db.execute(
            "INSERT INTO audit_log (asset_id, action, agent, details) VALUES (?, ?, ?, ?)",
            (asset_id, "coupon_distributed", "lifecycle",
             json.dumps({"payments": len(payments), "total_tinybars": sum(p["coupon_amount"] for p in payments)}))
        )
        await db.commit()
    finally:
        await db.close()

    # Log to HCS (after db closed)
    if topic_id:
        log_agent_action(
            topic_id,
            agent="lifecycle",
            action="coupon_distributed",
            details={
                "coupon_rate": annual_rate,
                "period_rate": period_rate,
                "num_holders": len(payments),
                "total_tinybars": sum(p["coupon_amount"] for p in payments),
                "all_paid": all(p.get("status") == "paid" for p in payments),
            },
        )

    return {
        "asset_id": asset_id,
        "coupon_rate": annual_rate,
        "period_rate": period_rate,
        "payments": payments,
        "total_distributed_tinybars": sum(p["coupon_amount"] for p in payments),
    }


async def update_nav(asset_id: int, new_nav: float) -> dict:
    """Update the NAV (Net Asset Value) for an asset."""
    db = await get_db()
    try:
        asset = await db.execute_fetchone("SELECT * FROM assets WHERE id = ?", (asset_id,))
        if not asset:
            raise ValueError("Asset not found")

        old_nav = asset["nav"]
        await db.execute("UPDATE assets SET nav = ? WHERE id = ?", (new_nav, asset_id))
        await db.commit()

        if asset["topic_id"]:
            log_agent_action(
                asset["topic_id"],
                agent="lifecycle",
                action="nav_updated",
                details={"old_nav": old_nav, "new_nav": new_nav},
            )

        await db.execute(
            "INSERT INTO audit_log (asset_id, action, agent, details) VALUES (?, ?, ?, ?)",
            (asset_id, "nav_updated", "lifecycle",
             json.dumps({"old_nav": old_nav, "new_nav": new_nav}))
        )
        await db.commit()

        return {"asset_id": asset_id, "old_nav": old_nav, "new_nav": new_nav}
    finally:
        await db.close()


async def update_nav_from_oracle(asset_id: int) -> dict:
    """Update NAV using treasury rate oracle data."""
    from server.oracle.treasury_rates import get_yield_for_duration

    db = await get_db()
    try:
        asset = await db.execute_fetchone("SELECT * FROM assets WHERE id = ?", (asset_id,))
        if not asset:
            raise ValueError("Asset not found")

        # Simple NAV calculation: face_value * (1 + yield_adjustment)
        face_value = asset["total_supply"] / (10 ** asset["decimals"])
        current_yield = await get_yield_for_duration(5)
        coupon_rate = asset["coupon_rate"]

        # Price adjustment: if market yield > coupon, bond trades below par
        if current_yield > 0 and coupon_rate > 0:
            price_factor = coupon_rate / (current_yield / 100) if current_yield > 0 else 1.0
            price_factor = min(max(price_factor, 0.8), 1.2)  # Cap at ±20%
            new_nav = face_value * price_factor
        else:
            new_nav = face_value
    finally:
        await db.close()

    return await update_nav(asset_id, round(new_nav, 2))


async def execute_maturity(asset_id: int) -> dict:
    """Execute maturity: wipe investor tokens, return HBAR principal, burn treasury tokens."""
    from server.hedera.token import wipe_tokens, transfer_hbar

    db = await get_db()
    try:
        asset = await db.execute_fetchone("SELECT * FROM assets WHERE id = ?", (asset_id,))
        if not asset:
            raise ValueError("Asset not found")
        if asset["status"] != "active":
            raise ValueError(f"Asset is already {asset['status']}")

        token_id = asset["token_id"]
        operator = str(get_operator_account_id())

        # Get all non-treasury holders with balance
        holders = await db.execute_fetchall(
            "SELECT * FROM holders WHERE asset_id = ? AND balance > 0 AND account_id != ?",
            (asset_id, operator)
        )

        redemptions = []
        total_wiped = 0

        for holder in holders:
            balance = holder["balance"]
            redemption = {
                "account_id": holder["account_id"],
                "balance": balance,
            }

            # 1. Wipe tokens from holder using wipe key (issuer authority at maturity)
            if token_id and balance > 0:
                try:
                    wipe_tokens(token_id, holder["account_id"], balance)
                    redemption["token_wipe"] = "success"
                    total_wiped += balance
                    logger.info(f"Wiped {balance} tokens from {holder['account_id']}")
                except Exception as e:
                    redemption["token_wipe"] = f"failed: {e}"
                    logger.error(f"Token wipe failed for {holder['account_id']}: {e}")

            # 2. Return principal as HBAR (real on-chain)
            principal_tinybars = max(balance, 1)
            try:
                transfer_hbar(holder["account_id"], principal_tinybars)
                redemption["principal_return"] = "success"
                redemption["principal_tinybars"] = principal_tinybars
                logger.info(f"Returned {principal_tinybars} tinybar principal to {holder['account_id']}")
            except Exception as e:
                redemption["principal_return"] = f"failed: {e}"
                logger.error(f"Principal return failed for {holder['account_id']}: {e}")

            redemption["status"] = "redeemed"
            redemptions.append(redemption)

            # Update holder balance to 0
            await db.execute("UPDATE holders SET balance = 0 WHERE id = ?", (holder["id"],))

        # 3. Burn remaining treasury tokens (real on-chain)
        treasury_holder = await db.execute_fetchone(
            "SELECT * FROM holders WHERE asset_id = ? AND account_id = ?",
            (asset_id, operator)
        )
        treasury_balance = treasury_holder["balance"] if treasury_holder else 0

        burn_result = "not_attempted"
        if treasury_balance > 0 and token_id:
            try:
                burn_tokens(token_id, treasury_balance)
                burn_result = "success"
                logger.info(f"Burned {treasury_balance} treasury tokens for {token_id}")
            except Exception as e:
                burn_result = f"failed: {e}"
                logger.error(f"Token burn failed: {e}")

        # Update treasury balance
        if treasury_holder:
            await db.execute("UPDATE holders SET balance = 0 WHERE id = ?", (treasury_holder["id"],))

        total_removed = total_wiped + treasury_balance

        # Mark asset as matured
        await db.execute("UPDATE assets SET status = 'matured' WHERE id = ?", (asset_id,))

        # Cancel remaining scheduled events
        await db.execute(
            "UPDATE scheduled_events SET status = 'cancelled' WHERE asset_id = ? AND status = 'pending'",
            (asset_id,)
        )

        topic_id = asset["topic_id"]

        await db.execute(
            "INSERT INTO audit_log (asset_id, action, agent, details) VALUES (?, ?, ?, ?)",
            (asset_id, "maturity_settled", "lifecycle",
             json.dumps({
                 "tokens_wiped": total_wiped, "tokens_burned": treasury_balance,
                 "burn_result": burn_result, "redemptions": len(redemptions),
             }))
        )
        await db.commit()
    finally:
        await db.close()

    # Log to HCS (after db closed)
    if topic_id:
        log_agent_action(
            topic_id,
            agent="lifecycle",
            action="maturity_settled",
            details={
                "tokens_wiped": total_wiped,
                "tokens_burned": treasury_balance,
                "burn_result": burn_result,
                "num_holders_redeemed": len(redemptions),
                "principal_returned": True,
            },
        )

    return {
        "asset_id": asset_id,
        "status": "matured",
        "tokens_wiped": total_wiped,
        "tokens_burned": treasury_balance,
        "burn_result": burn_result,
        "redemptions": redemptions,
    }
