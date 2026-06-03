"""OFAC screening-result data access."""

from __future__ import annotations

from sqlalchemy import select

from app.models.orm import ScreeningResult
from app.repositories.base import BaseRepository


class ScreeningRepository(BaseRepository):
    async def add(self, **fields) -> ScreeningResult:
        result = ScreeningResult(**fields)
        self.session.add(result)
        await self.session.flush()
        return result

    async def latest_for_account(self, account_id: str) -> ScreeningResult | None:
        res = await self.session.execute(
            select(ScreeningResult)
            .where(ScreeningResult.holder_account_id == account_id)
            .order_by(ScreeningResult.id.desc())
            .limit(1)
        )
        return res.scalar_one_or_none()
