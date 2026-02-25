"""Lamina — Autonomous RWA Lifecycle Agent on Hedera. FastAPI entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.config import get_settings
from backend.database import init_db, get_db
from backend.models.asset import AssetCreate, AssetResponse
from backend.models.holder import HolderCreate, HolderResponse
from backend.models.event import EventResponse
from backend.scheduler.jobs import run_coupon_payments, run_nav_updates, check_maturities

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing Lamina...")
    await init_db()
    logger.info("Database initialized")

    # Initialize Hedera client
    try:
        from backend.hedera.client import get_hedera_client
        client = get_hedera_client()
        logger.info(f"Hedera client connected: operator={client.operator_account_id}")
    except Exception as e:
        logger.warning(f"Hedera client init failed (will retry on first use): {e}")

    # Start scheduler
    scheduler.add_job(run_coupon_payments, "interval", hours=1, id="coupon_payments")
    scheduler.add_job(run_nav_updates, "interval", hours=24, id="nav_updates")
    scheduler.add_job(check_maturities, "interval", hours=6, id="maturity_checks")
    scheduler.start()
    logger.info("Scheduler started")

    yield

    # Shutdown
    scheduler.shutdown()
    logger.info("Lamina shutdown complete")


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


# ─── Health ────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "lamina", "version": "0.1.0"}


# ─── Assets ────────────────────────────────────────────────

@app.get("/api/assets", response_model=list[AssetResponse])
async def list_assets():
    db = await get_db()
    try:
        rows = await db.execute_fetchall("SELECT * FROM assets ORDER BY created_at DESC")
        return [dict(row) for row in rows]
    finally:
        await db.close()


@app.get("/api/assets/{asset_id}", response_model=AssetResponse)
async def get_asset(asset_id: int):
    db = await get_db()
    try:
        row = await db.execute_fetchone("SELECT * FROM assets WHERE id = ?", (asset_id,))
        if not row:
            raise HTTPException(status_code=404, detail="Asset not found")
        return dict(row)
    finally:
        await db.close()


@app.post("/api/assets", response_model=AssetResponse)
async def create_asset(asset: AssetCreate):
    """Create a new tokenized asset (use chat agent for full lifecycle issuance)."""
    from backend.agents.lifecycle import issue_asset
    result = await issue_asset(
        name=asset.name,
        symbol=asset.symbol,
        total_supply=asset.total_supply,
        decimals=asset.decimals,
        coupon_rate=asset.coupon_rate,
        maturity_date=asset.maturity_date,
        jurisdiction=asset.jurisdiction,
        investor_type=asset.investor_type,
        asset_type=asset.asset_type,
    )
    return result


# ─── Holders / Whitelist ──────────────────────────────────

@app.get("/api/assets/{asset_id}/holders", response_model=list[HolderResponse])
async def list_holders(asset_id: int):
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            "SELECT * FROM holders WHERE asset_id = ? ORDER BY balance DESC", (asset_id,)
        )
        return [dict(row) for row in rows]
    finally:
        await db.close()


@app.post("/api/assets/{asset_id}/whitelist")
async def add_to_whitelist(asset_id: int, holder: HolderCreate):
    from backend.agents.compliance import add_to_whitelist
    result = await add_to_whitelist(
        asset_id=asset_id,
        account_id=holder.account_id,
        jurisdiction=holder.jurisdiction,
        investor_type=holder.investor_type,
    )
    return result


@app.post("/api/assets/{asset_id}/validate-transfer")
async def validate_transfer(asset_id: int, from_id: str, to_id: str, amount: int):
    from backend.agents.compliance import validate_transfer
    approved, reason = await validate_transfer(asset_id, from_id, to_id, amount)
    return {"approved": approved, "reason": reason}


@app.post("/api/assets/{asset_id}/purchase")
async def purchase_tokens(asset_id: int, account_id: str, amount: int):
    """Purchase tokens: real HTS transfer from treasury to investor + compliance check."""
    from backend.agents.compliance import validate_transfer as check_transfer
    from backend.hedera.token import transfer_tokens
    from backend.hedera.consensus import log_agent_action
    from backend.hedera.client import get_operator_account_id

    db = await get_db()
    try:
        asset = await db.execute_fetchone("SELECT * FROM assets WHERE id = ?", (asset_id,))
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        operator = str(get_operator_account_id())

        # Compliance check
        approved, reason = await check_transfer(asset_id, operator, account_id, amount)
        if not approved:
            raise HTTPException(status_code=403, detail=reason)

        # Real on-chain token transfer
        tx_id = transfer_tokens(asset["token_id"], operator, account_id, amount, asset["decimals"])

        # Update balances in database
        await db.execute(
            "UPDATE holders SET balance = balance - ? WHERE account_id = ? AND asset_id = ?",
            (amount, operator, asset_id)
        )
        await db.execute(
            "UPDATE holders SET balance = balance + ? WHERE account_id = ? AND asset_id = ?",
            (amount, account_id, asset_id)
        )
        await db.commit()

        topic_id = asset["topic_id"]
    finally:
        await db.close()

    # Log to HCS
    if topic_id:
        log_agent_action(
            topic_id,
            agent="lifecycle",
            action="tokens_purchased",
            details={
                "buyer": account_id,
                "amount": amount,
                "tx_id": tx_id,
            },
        )

    return {"tx_id": tx_id, "buyer": account_id, "amount": amount, "status": "completed"}


@app.get("/api/assets/{asset_id}/compliance")
async def get_compliance_status(asset_id: int):
    from backend.agents.compliance import get_compliance_status
    return await get_compliance_status(asset_id)


# ─── Lifecycle Actions ────────────────────────────────────

@app.post("/api/assets/{asset_id}/distribute-coupon")
async def distribute_coupon(asset_id: int):
    from backend.agents.lifecycle import distribute_coupon
    result = await distribute_coupon(asset_id)
    return result


@app.post("/api/assets/{asset_id}/update-nav")
async def update_nav(asset_id: int, nav: float):
    from backend.agents.lifecycle import update_nav
    result = await update_nav(asset_id, nav)
    return result


@app.post("/api/assets/{asset_id}/mature")
async def mature_asset(asset_id: int):
    from backend.agents.lifecycle import execute_maturity
    result = await execute_maturity(asset_id)
    return result


# ─── Events ───────────────────────────────────────────────

@app.get("/api/assets/{asset_id}/events", response_model=list[EventResponse])
async def list_events(asset_id: int, status: str = None):
    db = await get_db()
    try:
        if status:
            rows = await db.execute_fetchall(
                "SELECT * FROM scheduled_events WHERE asset_id = ? AND status = ? ORDER BY scheduled_at",
                (asset_id, status)
            )
        else:
            rows = await db.execute_fetchall(
                "SELECT * FROM scheduled_events WHERE asset_id = ? ORDER BY scheduled_at DESC",
                (asset_id,)
            )
        return [dict(row) for row in rows]
    finally:
        await db.close()


# ─── Audit Log (HCS) ─────────────────────────────────────

@app.get("/api/assets/{asset_id}/audit-log")
async def get_audit_log(asset_id: int):
    db = await get_db()
    try:
        row = await db.execute_fetchone("SELECT topic_id FROM assets WHERE id = ?", (asset_id,))
        if not row or not row["topic_id"]:
            raise HTTPException(status_code=404, detail="Asset or topic not found")

        from backend.hedera.consensus import get_topic_messages
        messages = await get_topic_messages(row["topic_id"])

        # Also get local audit log
        local_rows = await db.execute_fetchall(
            "SELECT * FROM audit_log WHERE asset_id = ? ORDER BY created_at DESC LIMIT 100",
            (asset_id,)
        )
        return {
            "topic_id": row["topic_id"],
            "hcs_messages": messages,
            "local_log": [dict(r) for r in local_rows],
        }
    finally:
        await db.close()


# ─── Reports ─────────────────────────────────────────────

@app.get("/api/assets/{asset_id}/reports")
async def list_reports(asset_id: int):
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            "SELECT * FROM reports WHERE asset_id = ? ORDER BY generated_at DESC", (asset_id,)
        )
        return [dict(row) for row in rows]
    finally:
        await db.close()


@app.post("/api/assets/{asset_id}/reports")
async def generate_report(asset_id: int, report_type: str = "compliance", period: str = "Q1 2026"):
    from backend.agents.reporting import generate_compliance_report
    result = await generate_compliance_report(asset_id, period)
    return result


@app.get("/api/reports/{report_id}/download")
async def download_report(report_id: int):
    db = await get_db()
    try:
        row = await db.execute_fetchone("SELECT * FROM reports WHERE id = ?", (report_id,))
        if not row or not row["file_path"]:
            raise HTTPException(status_code=404, detail="Report not found")
        return FileResponse(row["file_path"], media_type="application/pdf", filename=f"report_{report_id}.pdf")
    finally:
        await db.close()


# ─── Chat ─────────────────────────────────────────────────

@app.post("/api/chat")
async def chat(message: dict):
    from backend.agents.chat import process_message
    result = await process_message(message.get("message", ""))
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.backend_host, port=settings.backend_port, reload=True)
