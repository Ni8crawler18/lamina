"""Event and audit log routes."""

from fastapi import APIRouter, HTTPException

from server.database import get_db
from server.models.event import EventResponse

router = APIRouter(prefix="/api/assets/{asset_id}", tags=["events"])


@router.get("/events", response_model=list[EventResponse])
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


@router.get("/audit-log")
async def get_audit_log(asset_id: int):
    db = await get_db()
    try:
        row = await db.execute_fetchone("SELECT topic_id FROM assets WHERE id = ?", (asset_id,))
        if not row or not row["topic_id"]:
            raise HTTPException(status_code=404, detail="Asset or topic not found")

        from server.hedera.consensus import get_topic_messages
        messages = await get_topic_messages(row["topic_id"])

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
