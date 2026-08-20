"""Lifecycle endpoints — NAV update, maturity settlement."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.services.lifecycle_service import LifecycleError, LifecycleService

router = APIRouter(prefix="/api/assets/{asset_id}", tags=["lifecycle"])


@router.post("/update-nav")
async def update_nav(
    asset_id: int, nav: float | None = None, session: AsyncSession = Depends(get_session)
):
    svc = LifecycleService(session)
    try:
        if nav is not None:
            return await svc.update_nav(asset_id, nav)
        return await svc.update_nav_from_oracle(asset_id)
    except LifecycleError as e:
        raise HTTPException(400, str(e))


@router.post("/mature")
async def mature(asset_id: int, session: AsyncSession = Depends(get_session)):
    try:
        return await LifecycleService(session).execute_maturity(asset_id)
    except LifecycleError as e:
        raise HTTPException(400, str(e))


@router.post("/retire")
async def retire(
    asset_id: int, holder_ref: str, amount: int, session: AsyncSession = Depends(get_session)
):
    try:
        return await LifecycleService(session).retire_credits(asset_id, holder_ref, amount)
    except LifecycleError as e:
        raise HTTPException(400, str(e))
