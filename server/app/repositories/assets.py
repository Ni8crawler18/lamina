"""Asset data access."""

from __future__ import annotations

from sqlalchemy import select

from app.models.orm import Asset
from app.repositories.base import BaseRepository


class AssetRepository(BaseRepository):
    async def create(self, **fields) -> Asset:
        asset = Asset(**fields)
        self.session.add(asset)
        await self.session.flush()  # populate id
        return asset

    async def get(self, asset_id: int) -> Asset | None:
        return await self.session.get(Asset, asset_id)

    async def list(self) -> list[Asset]:
        res = await self.session.execute(select(Asset).order_by(Asset.id.desc()))
        return list(res.scalars().all())

    async def list_by_chain(self, chain: str) -> list[Asset]:
        res = await self.session.execute(
            select(Asset).where(Asset.chain == chain).order_by(Asset.id.desc())
        )
        return list(res.scalars().all())

    async def list_active(self) -> list[Asset]:
        res = await self.session.execute(select(Asset).where(Asset.status == "active"))
        return list(res.scalars().all())

    async def set_status(self, asset_id: int, status: str) -> None:
        asset = await self.get(asset_id)
        if asset:
            asset.status = status

    async def set_nav(self, asset_id: int, nav: float) -> None:
        asset = await self.get(asset_id)
        if asset:
            asset.nav = nav
