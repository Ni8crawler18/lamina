"""Lamina — Autonomous RWA Lifecycle Agent on Hedera. FastAPI entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from server.config import get_settings
from server.database import init_db
from server.scheduler.jobs import run_coupon_payments, run_nav_updates, check_maturities, refresh_ofac_data

# Routes
from server.routes.assets import router as assets_router
from server.routes.compliance import router as compliance_router
from server.routes.lifecycle import router as lifecycle_router
from server.routes.events import router as events_router, global_events_router
from server.routes.reports import router as reports_router
from server.routes.chat import router as chat_router
from server.routes.ofac import router as ofac_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


# ─── Lifespan ────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Lamina...")
    await init_db()
    logger.info("Database initialized")

    try:
        from server.hedera.client import get_hedera_client
        client = get_hedera_client()
        logger.info(f"Hedera client connected: operator={client.operator_account_id}")
    except Exception as e:
        logger.warning(f"Hedera client init failed (will retry on first use): {e}")

    # Load OFAC SDN list
    try:
        from server.ofac.sdn import OFACScreener
        screener = OFACScreener.get_instance()
        await screener.load()
    except Exception as e:
        logger.warning(f"OFAC screener init failed (will retry on refresh): {e}")

    scheduler.add_job(run_coupon_payments, "interval", hours=1, id="coupon_payments")
    scheduler.add_job(run_nav_updates, "interval", hours=24, id="nav_updates")
    scheduler.add_job(check_maturities, "interval", hours=6, id="maturity_checks")
    scheduler.add_job(refresh_ofac_data, "interval", hours=24, id="ofac_refresh")
    scheduler.start()
    logger.info("Scheduler started")

    yield

    scheduler.shutdown()
    logger.info("Lamina shutdown complete")


# ─── App ─────────────────────────────────────────────────

settings = get_settings()

app = FastAPI(
    title="Lamina",
    description="Autonomous RWA Lifecycle Agent on Hedera",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Routes ──────────────────────────────────────────────

app.include_router(assets_router)
app.include_router(compliance_router)
app.include_router(lifecycle_router)
app.include_router(events_router)
app.include_router(global_events_router)
app.include_router(reports_router)
app.include_router(chat_router)
app.include_router(ofac_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "lamina", "version": "0.1.0"}


# ─── Entry ───────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.main:app", host=settings.backend_host, port=settings.backend_port, reload=True)
