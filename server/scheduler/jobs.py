"""APScheduler job definitions for automated lifecycle events."""

import logging
from datetime import datetime

from server.database import get_db

logger = logging.getLogger(__name__)


async def run_coupon_payments():
    """Check for due coupon payments and execute them."""
    from server.agents.lifecycle import distribute_coupon

    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            """SELECT se.id, se.asset_id FROM scheduled_events se
               JOIN assets a ON se.asset_id = a.id
               WHERE se.event_type = 'coupon_payment'
               AND se.status = 'pending'
               AND se.scheduled_at <= ?
               AND a.status = 'active'""",
            (datetime.utcnow().isoformat(),)
        )
        for row in rows:
            try:
                await distribute_coupon(row[1])
                await db.execute(
                    "UPDATE scheduled_events SET status='completed', executed_at=? WHERE id=?",
                    (datetime.utcnow().isoformat(), row[0])
                )
                await db.commit()
                logger.info(f"Coupon payment completed for asset {row[1]}")
            except Exception as e:
                logger.error(f"Coupon payment failed for asset {row[1]}: {e}")
    finally:
        await db.close()


async def run_nav_updates():
    """Update NAV for all active assets."""
    from server.agents.lifecycle import update_nav_from_oracle

    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            "SELECT id FROM assets WHERE status = 'active'"
        )
        for row in rows:
            try:
                await update_nav_from_oracle(row[0])
            except Exception as e:
                logger.error(f"NAV update failed for asset {row[0]}: {e}")
    finally:
        await db.close()


async def refresh_ofac_data():
    """Daily refresh of the OFAC SDN list."""
    from server.ofac.sdn import OFACScreener
    try:
        screener = OFACScreener.get_instance()
        await screener.load()
        logger.info("OFAC SDN data refreshed")
    except Exception as e:
        logger.error(f"OFAC refresh failed: {e}")


async def check_maturities():
    """Check for assets reaching maturity and execute settlement."""
    from server.agents.lifecycle import execute_maturity

    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            """SELECT id, maturity_date FROM assets
               WHERE status = 'active'
               AND maturity_date IS NOT NULL
               AND maturity_date <= ?""",
            (datetime.utcnow().isoformat(),)
        )
        for row in rows:
            try:
                await execute_maturity(row[0])
                logger.info(f"Maturity executed for asset {row[0]}")
            except Exception as e:
                logger.error(f"Maturity execution failed for asset {row[0]}: {e}")
    finally:
        await db.close()
