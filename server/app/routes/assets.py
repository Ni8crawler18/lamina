"""Asset endpoints — list, get, issue (tokenize)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.jurisdictions import ASSET_TYPES
from app.database import get_session
from app.models.asset import AssetCreate, AssetOut
from app.repositories.assets import AssetRepository
from app.services.issuance_service import IssuanceService

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("/types")
async def list_asset_types():
    """Asset-type metadata (has_coupon/has_maturity/required_metadata/...) driving
    which fields the create-asset form shows for each type. Single source of truth,
    shared with the backend validation in IssuanceService."""
    return ASSET_TYPES


@router.get("", response_model=list[AssetOut])
async def list_assets(
    chain: str | None = None, owner: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    return await AssetRepository(session).list(chain=chain, owner=owner)


@router.get("/{asset_id}", response_model=AssetOut)
async def get_asset(asset_id: int, session: AsyncSession = Depends(get_session)):
    asset = await AssetRepository(session).get(asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")
    return asset


@router.post("", response_model=AssetOut)
async def create_asset(body: AssetCreate, session: AsyncSession = Depends(get_session)):
    try:
        return await IssuanceService(session).issue_asset(**body.model_dump())
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e))
