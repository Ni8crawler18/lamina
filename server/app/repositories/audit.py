"""Local audit-log mirror data access (the on-chain log is the source of truth)."""

from __future__ import annotations

import json

from sqlalchemy import select

from app.models.orm import AuditLogEntry
from app.repositories.base import BaseRepository


class AuditRepository(BaseRepository):
    async def add(
        self, action: str, agent: str, asset_id: int | None = None,
        details: dict | None = None, onchain_sequence: int | None = None,
        onchain_timestamp: str | None = None,
    ) -> AuditLogEntry:
        entry = AuditLogEntry(
            asset_id=asset_id,
            action=action,
            agent=agent,
            details=json.dumps(details or {}),
            onchain_sequence=onchain_sequence,
            onchain_timestamp=onchain_timestamp,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def list_for_asset(self, asset_id: int, limit: int = 100) -> list[AuditLogEntry]:
        res = await self.session.execute(
            select(AuditLogEntry)
            .where(AuditLogEntry.asset_id == asset_id)
            .order_by(AuditLogEntry.id.desc())
            .limit(limit)
        )
        return list(res.scalars().all())
