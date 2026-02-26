"""Lifecycle routes — coupon distribution, NAV updates, maturity settlement."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/assets/{asset_id}", tags=["lifecycle"])


@router.post("/distribute-coupon")
async def distribute_coupon(asset_id: int):
    from server.agents.lifecycle import distribute_coupon
    return await distribute_coupon(asset_id)


@router.post("/update-nav")
async def update_nav(asset_id: int, nav: float):
    from server.agents.lifecycle import update_nav
    return await update_nav(asset_id, nav)


@router.post("/mature")
async def mature_asset(asset_id: int):
    from server.agents.lifecycle import execute_maturity
    return await execute_maturity(asset_id)
