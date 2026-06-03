"""Compliance endpoints — holders, whitelist, transfer validation, purchase, status."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.holder import HolderOut, PurchaseRequest, WhitelistRequest
from app.repositories.holders import HolderRepository
from app.services.compliance_service import ComplianceError, ComplianceService
from app.services.issuance_service import IssuanceService

router = APIRouter(prefix="/api/assets/{asset_id}", tags=["compliance"])


@router.get("/holders", response_model=list[HolderOut])
async def list_holders(asset_id: int, session: AsyncSession = Depends(get_session)):
    return await HolderRepository(session).list_for_asset(asset_id)


@router.post("/whitelist", response_model=HolderOut)
async def whitelist(asset_id: int, body: WhitelistRequest, session: AsyncSession = Depends(get_session)):
    try:
        return await ComplianceService(session).add_to_whitelist(
            asset_id, body.account_id, body.jurisdiction, body.investor_type, body.name
        )
    except ComplianceError as e:
        raise HTTPException(400, str(e))


@router.post("/validate-transfer")
async def validate_transfer(
    asset_id: int, from_id: str, to_id: str, amount: int,
    session: AsyncSession = Depends(get_session),
):
    ok, reason = await ComplianceService(session).validate_transfer(asset_id, from_id, to_id, amount)
    return {"approved": ok, "reason": reason}


@router.post("/purchase")
async def purchase(asset_id: int, body: PurchaseRequest, session: AsyncSession = Depends(get_session)):
    try:
        return await IssuanceService(session).purchase(asset_id, body.account_id, body.amount)
    except PermissionError as e:
        raise HTTPException(400, f"Compliance blocked: {e}")
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/compliance")
async def compliance_status(asset_id: int, session: AsyncSession = Depends(get_session)):
    try:
        return await ComplianceService(session).get_compliance_status(asset_id)
    except ComplianceError as e:
        raise HTTPException(404, str(e))
