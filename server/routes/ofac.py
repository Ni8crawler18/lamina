"""OFAC sanctions screening routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from server.models.screening import ScreeningRequest, ScreeningResponse, OFACStatusResponse
from server.ofac.sdn import OFACScreener

router = APIRouter(prefix="/api/ofac", tags=["ofac"])


@router.post("/screen", response_model=ScreeningResponse)
async def screen_entity(req: ScreeningRequest):
    """Screen a name and/or address against the OFAC SDN list."""
    if not req.name and not req.address:
        raise HTTPException(status_code=400, detail="Provide at least a name or address")

    screener = OFACScreener.get_instance()
    if not screener.loaded:
        raise HTTPException(status_code=503, detail="OFAC screener not loaded yet")

    result = screener.screen(name=req.name, address=req.address)
    return ScreeningResponse(
        is_match=result["is_match"],
        score=result.get("score", 0),
        match_type=result.get("match_type"),
        details=result.get("details"),
        screened_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/status", response_model=OFACStatusResponse)
async def get_status():
    """Get OFAC screener status (loaded, entry count, etc.)."""
    screener = OFACScreener.get_instance()
    return screener.get_status()


@router.post("/refresh")
async def refresh_sdn():
    """Re-download the SDN list from treasury.gov."""
    screener = OFACScreener.get_instance()
    await screener.load()
    return screener.get_status()
