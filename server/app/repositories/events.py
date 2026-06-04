"""Scheduled-event data access."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from app.models.orm import Asset, ScheduledEvent
from app.repositories.base import BaseRepository


class EventRepository(BaseRepository):
    async def create(self, **fields) -> ScheduledEvent:
        evt = ScheduledEvent(**fields)
        self.session.add(evt)
        await self.session.flush()
        return evt

    async def list_for_asset(self, asset_id: int, status: str | None = None) -> list[ScheduledEvent]:
        stmt = select(ScheduledEvent).where(ScheduledEvent.asset_id == asset_id)
        if status:
            stmt = stmt.where(ScheduledEvent.status == status)
        res = await self.session.execute(stmt.order_by(ScheduledEvent.scheduled_at))
        return list(res.scalars().all())

    async def upcoming(self, chain: str | None = None, limit: int = 10) -> list[tuple[ScheduledEvent, Asset]]:
        """Pending events across assets (optionally one chain), soonest first, with their asset."""
        stmt = (
            select(ScheduledEvent, Asset)
            .join(Asset, ScheduledEvent.asset_id == Asset.id)
            .where(ScheduledEvent.status == "pending")
        )
        if chain:
            stmt = stmt.where(Asset.chain == chain)
        stmt = stmt.order_by(ScheduledEvent.scheduled_at).limit(limit)
        res = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in res.all()]

    async def next_pending(self, asset_id: int, event_type: str) -> ScheduledEvent | None:
        res = await self.session.execute(
            select(ScheduledEvent)
            .where(
                ScheduledEvent.asset_id == asset_id,
                ScheduledEvent.event_type == event_type,
                ScheduledEvent.status == "pending",
            )
            .order_by(ScheduledEvent.scheduled_at)
            .limit(1)
        )
        return res.scalar_one_or_none()

    async def due(self, before: datetime, event_type: str | None = None) -> list[ScheduledEvent]:
        stmt = select(ScheduledEvent).where(
            ScheduledEvent.status == "pending", ScheduledEvent.scheduled_at <= before
        )
        if event_type:
            stmt = stmt.where(ScheduledEvent.event_type == event_type)
        res = await self.session.execute(stmt.order_by(ScheduledEvent.scheduled_at))
        return list(res.scalars().all())

    async def mark_completed(self, event_id: int, tx_hash: str | None = None) -> None:
        evt = await self.session.get(ScheduledEvent, event_id)
        if evt:
            evt.status = "completed"
            evt.executed_at = datetime.utcnow()
            if tx_hash:
                evt.tx_hash = tx_hash
