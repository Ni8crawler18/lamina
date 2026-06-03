"""Chain discovery — the chain picker lists what's available."""

from fastapi import APIRouter

from app.chains.registry import get_registry
from app.models.chain import ChainOut

router = APIRouter(prefix="/api/chains", tags=["chains"])


@router.get("", response_model=list[ChainOut])
async def list_chains(enabled_only: bool = False):
    reg = get_registry()
    configs = reg.list_enabled() if enabled_only else reg.list_all()
    return [
        ChainOut(
            slug=c.slug, name=c.name, family=c.family, chain_id=c.chain_id,
            native_symbol=c.native_symbol, explorer_url=c.explorer_url, enabled=c.enabled,
        )
        for c in configs
    ]
