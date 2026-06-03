"""Audit service — writes every agent action to the chain AND mirrors it in Postgres.

Old code did these two writes separately in 5+ places; here it's one call.
"""

from __future__ import annotations

import logging

from app.chains.base import ChainAdapter
from app.repositories.audit import AuditRepository
from app.utils.aio import run_chain

logger = logging.getLogger(__name__)


class AuditService:
    def __init__(self, session):
        self.repo = AuditRepository(session)

    async def record(
        self, adapter: ChainAdapter, topic_ref: str | None, asset_id: int | None,
        agent: str, action: str, details: dict,
    ) -> int | None:
        """Write to the chain's audit log (best-effort) and always mirror to DB."""
        seq = None
        if topic_ref:
            try:
                seq = await run_chain(adapter.write_audit, topic_ref, agent, action, details)
            except Exception as e:
                logger.error("on-chain audit write failed (%s/%s): %s", agent, action, e)
        await self.repo.add(
            action=action, agent=agent, asset_id=asset_id,
            details=details, onchain_sequence=seq,
        )
        return seq
