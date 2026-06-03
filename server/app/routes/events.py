"""Event + audit-trail endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.chains.registry import get_registry
from app.database import get_session
from app.repositories.assets import AssetRepository
from app.repositories.events import EventRepository
from app.utils.aio import run_chain

router = APIRouter(prefix="/api/assets/{asset_id}", tags=["events"])


@router.get("/events")
async def list_events(asset_id: int, status: str | None = None, session: AsyncSession = Depends(get_session)):
    rows = await EventRepository(session).list_for_asset(asset_id, status)
    return [
        {"id": e.id, "event_type": e.event_type, "scheduled_at": e.scheduled_at,
         "executed_at": e.executed_at, "status": e.status, "tx_hash": e.tx_hash}
        for e in rows
    ]


@router.get("/audit-log")
async def audit_log(asset_id: int, limit: int = 100, session: AsyncSession = Depends(get_session)):
    asset = await AssetRepository(session).get(asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")
    if not asset.topic_id:
        return {"topic_id": None, "entries": []}
    adapter = get_registry().adapter(asset.chain)
    entries = await run_chain(adapter.read_audit, asset.topic_id, limit)
    return {
        "topic_id": asset.topic_id, "chain": asset.chain,
        "entries": [
            {"sequence": e.sequence, "timestamp": e.timestamp, "agent": e.agent,
             "action": e.action, "details": e.details}
            for e in entries
        ],
    }
