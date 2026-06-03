"""OFAC sanctions-screening endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.integrations.ofac.sdn import OFACScreener

router = APIRouter(prefix="/api/ofac", tags=["ofac"])


class ScreenRequest(BaseModel):
    name: str | None = None
    address: str | None = None


@router.post("/screen")
async def screen(body: ScreenRequest):
    return OFACScreener.get_instance().screen(name=body.name, address=body.address)


@router.get("/status")
async def status():
    return OFACScreener.get_instance().get_status()


@router.post("/refresh")
async def refresh():
    screener = OFACScreener.get_instance()
    await screener.load(force_download=True)
    return screener.get_status()
