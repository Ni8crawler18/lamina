"""Asset endpoints — list, get, issue (tokenize)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.asset import AssetCreate, AssetOut
from app.repositories.assets import AssetRepository
from app.services.issuance_service import IssuanceService

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("", response_model=list[AssetOut])
async def list_assets(chain: str | None = None, session: AsyncSession = Depends(get_session)):
    repo = AssetRepository(session)
    return await (repo.list_by_chain(chain) if chain else repo.list())


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
