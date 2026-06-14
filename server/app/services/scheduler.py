"""Background jobs (APScheduler) — autonomous lifecycle execution.

Each job opens its own DB session. Failures are isolated per asset so one bad
asset never breaks a whole run.
"""

from __future__ import annotations

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

import httpx

from app.config import get_settings
from app.database import get_sessionmaker
from app.integrations.ofac.sdn import OFACScreener
from app.repositories.assets import AssetRepository
from app.repositories.events import EventRepository
from app.services.lifecycle_service import LifecycleService
from app.services.payout_service import PayoutService

logger = logging.getLogger(__name__)
_scheduler: AsyncIOScheduler | None = None


async def run_coupon_payments() -> None:
    sm = get_sessionmaker()
    async with sm() as s:
        due = await EventRepository(s).due(datetime.utcnow(), "coupon_payment")
    for evt in due:
        try:
            async with sm() as s:
                await PayoutService(s).distribute_coupon(evt.asset_id)
                await s.commit()
        except Exception as e:
            logger.error("coupon job failed for asset %s: %s", evt.asset_id, e)


async def run_nav_updates() -> None:
    sm = get_sessionmaker()
    async with sm() as s:
        assets = await AssetRepository(s).list_active()
    for a in assets:
        try:
            async with sm() as s:
                await LifecycleService(s).update_nav_from_oracle(a.id)
                await s.commit()
        except Exception as e:
            logger.error("nav job failed for asset %s: %s", a.id, e)


async def check_maturities() -> None:
    sm = get_sessionmaker()
    async with sm() as s:
        due = await EventRepository(s).due(datetime.utcnow(), "maturity")
    for evt in due:
        try:
            async with sm() as s:
                await LifecycleService(s).execute_maturity(evt.asset_id)
                await EventRepository(s).mark_completed(evt.id)
                await s.commit()
        except Exception as e:
            logger.error("maturity job failed for asset %s: %s", evt.asset_id, e)


async def refresh_ofac() -> None:
    try:
        await OFACScreener.get_instance().load(force_download=True)
    except Exception as e:
        logger.error("OFAC refresh failed: %s", e)


async def heartbeat() -> None:
    """Self-ping our own public /health so the free host doesn't spin the instance
    down on inactivity. Only inbound HTTP resets the idle timer, so this must hit
    the external URL — an internal timer alone would not keep us awake. Logs the
    health payload (enabled chains + OFAC status), so it doubles as a liveness probe.
    """
    base = get_settings().render_external_url.rstrip("/")
    if not base:
        return  # local dev — nothing to keep warm
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(f"{base}/health")
        data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        logger.info(
            "heartbeat %s → %s (chains=%d, ofac=%s)",
            base, r.status_code,
            len(data.get("chains_enabled", [])), data.get("ofac_loaded"),
        )
    except Exception as e:
        logger.warning("heartbeat ping failed: %s", e)


def start_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler:
        return _scheduler
    sched = AsyncIOScheduler()
    sched.add_job(run_coupon_payments, "interval", hours=1, id="coupons")
    sched.add_job(run_nav_updates, "interval", hours=24, id="nav")
    sched.add_job(check_maturities, "interval", hours=6, id="maturities")
    sched.add_job(refresh_ofac, "interval", hours=24, id="ofac")

    settings = get_settings()
    hb = "off"
    if settings.render_external_url:
        mins = max(1, settings.heartbeat_minutes)
        sched.add_job(heartbeat, "interval", minutes=mins, id="heartbeat",
                      next_run_time=datetime.utcnow())
        hb = f"{mins}m"

    sched.start()
    _scheduler = sched
    logger.info("Scheduler started (coupons 1h, nav 24h, maturities 6h, ofac 24h, heartbeat %s)", hb)
    return sched


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
