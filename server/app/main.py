"""Laminaa backend — FastAPI app, lifespan, router registration.

Orchestration only: business logic lives in services/.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.chains.registry import get_registry
from app.config import get_settings
from app.database import create_tables, ping
from app.integrations.ofac.sdn import OFACScreener
from app.middleware.logging import RequestContextMiddleware
from app.routes import (
    assets,
    chains,
    chat,
    compliance,
    events,
    lifecycle,
    ofac,
    payouts,
    reports,
)
from app.services.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    logger.info("Starting Laminaa backend (%s)…", settings.environment)

    get_registry().load()
    try:
        await ping()
        await create_tables()
        logger.info("Postgres connected; schema ensured")
    except Exception as e:
        logger.error("Postgres connection/schema setup failed: %s", e)

    await OFACScreener.get_instance().load()  # cache-first; fast unless stale
    start_scheduler()

    from contextlib import AsyncExitStack
    async with AsyncExitStack() as stack:
        if settings.mcp_enabled:
            from app.mcp.server import get_session_manager
            await stack.enter_async_context(get_session_manager().run())
            logger.info("MCP server enabled at /mcp (writes=%s)", settings.mcp_allow_writes)
        if settings.channels_enabled:
            from app.channels import telegram
            telegram.start()
            logger.info("Messaging channels enabled (telegram)")
        logger.info("Laminaa ready")
        yield
        if settings.channels_enabled:
            from app.channels import telegram
            await telegram.stop()
    stop_scheduler()


app = FastAPI(title="Laminaa API", version="0.2.0", lifespan=lifespan)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[*get_settings().frontend_origins, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (chains, assets, compliance, payouts, lifecycle, events, reports, ofac, chat):
    app.include_router(r.router)
app.include_router(events.events_router)

# MCP server (authed) — mounted only when explicitly enabled.
if get_settings().mcp_enabled:
    from app.mcp.server import mcp_asgi_app
    app.mount("/mcp", mcp_asgi_app())


@app.get("/health", tags=["health"])
async def health():
    reg = get_registry()
    return {
        "status": "ok",
        "service": "Laminaa",
        "version": "0.2.0",
        "chains_enabled": [c.slug for c in reg.list_enabled()],
        "ofac_loaded": OFACScreener.get_instance().loaded,
    }
