"""Holder data access."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from app.models.orm import Holder
from app.repositories.base import BaseRepository


class HolderRepository(BaseRepository):
    async def create(self, **fields) -> Holder:
        holder = Holder(**fields)
        self.session.add(holder)
        await self.session.flush()
        return holder

    async def get(self, account_id: str, asset_id: int) -> Holder | None:
        res = await self.session.execute(
            select(Holder).where(Holder.account_id == account_id, Holder.asset_id == asset_id)
        )
        return res.scalar_one_or_none()

    async def list_for_asset(self, asset_id: int) -> list[Holder]:
        res = await self.session.execute(select(Holder).where(Holder.asset_id == asset_id))
        return list(res.scalars().all())

    async def holders_with_balance(self, asset_id: int, exclude: str | None = None) -> list[Holder]:
        stmt = select(Holder).where(
            Holder.asset_id == asset_id, Holder.whitelisted.is_(True), Holder.balance > 0
        )
        if exclude:
            stmt = stmt.where(Holder.account_id != exclude)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def count_whitelisted(self, asset_id: int) -> int:
        res = await self.session.execute(
            select(Holder).where(Holder.asset_id == asset_id, Holder.whitelisted.is_(True))
        )
        return len(res.scalars().all())

    async def adjust_balance(self, account_id: str, asset_id: int, delta: int) -> None:
        holder = await self.get(account_id, asset_id)
        if holder:
            holder.balance += delta

    async def set_ofac(self, account_id: str, asset_id: int, status: str) -> None:
        holder = await self.get(account_id, asset_id)
        if holder:
            holder.ofac_status = status
            holder.ofac_screened_at = datetime.utcnow()
