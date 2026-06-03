"""Payout endpoints — coupon/dividend distribution."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.services.payout_service import PayoutError, PayoutService

router = APIRouter(prefix="/api/assets/{asset_id}", tags=["payouts"])


@router.post("/distribute-coupon")
async def distribute_coupon(asset_id: int, session: AsyncSession = Depends(get_session)):
    try:
        return await PayoutService(session).distribute_coupon(asset_id)
    except PayoutError as e:
        raise HTTPException(400, str(e))
