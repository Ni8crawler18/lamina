"""Asset CRUD routes."""

from fastapi import APIRouter, HTTPException

from server.database import get_db
from server.models.asset import AssetCreate, AssetResponse

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("", response_model=list[AssetResponse])
async def list_assets():
    db = await get_db()
    try:
        rows = await db.execute_fetchall("SELECT * FROM assets ORDER BY created_at DESC")
        return [dict(row) for row in rows]
    finally:
        await db.close()


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(asset_id: int):
    db = await get_db()
    try:
        row = await db.execute_fetchone("SELECT * FROM assets WHERE id = ?", (asset_id,))
        if not row:
            raise HTTPException(status_code=404, detail="Asset not found")
        return dict(row)
    finally:
        await db.close()


@router.post("", response_model=AssetResponse)
async def create_asset(asset: AssetCreate):
    from server.agents.lifecycle import issue_asset
    return await issue_asset(
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
