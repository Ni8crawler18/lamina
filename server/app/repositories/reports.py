"""Report data access."""

from __future__ import annotations

from sqlalchemy import select

from app.models.orm import Report
from app.repositories.base import BaseRepository


class ReportRepository(BaseRepository):
    async def create(self, **fields) -> Report:
        report = Report(**fields)
        self.session.add(report)
        await self.session.flush()
        return report

    async def get(self, report_id: int) -> Report | None:
        return await self.session.get(Report, report_id)

    async def delete(self, report_id: int) -> bool:
        report = await self.session.get(Report, report_id)
        if not report:
            return False
        await self.session.delete(report)
        await self.session.flush()
        return True

    async def list_for_asset(self, asset_id: int) -> list[Report]:
        res = await self.session.execute(
            select(Report).where(Report.asset_id == asset_id).order_by(Report.id.desc())
        )
        return list(res.scalars().all())
