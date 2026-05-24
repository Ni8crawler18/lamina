"""Compliance routes — whitelist, KYC, transfer validation, purchase."""

from fastapi import APIRouter, HTTPException

from server.database import get_db
from server.models.holder import HolderCreate, HolderResponse

router = APIRouter(prefix="/api/assets/{asset_id}", tags=["compliance"])


@router.get("/holders", response_model=list[HolderResponse])
async def list_holders(asset_id: int):
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            "SELECT * FROM holders WHERE asset_id = ? ORDER BY balance DESC", (asset_id,)
        )
        return [dict(row) for row in rows]
    finally:
        await db.close()


@router.post("/whitelist")
async def add_to_whitelist(asset_id: int, holder: HolderCreate):
    from server.agents.compliance import add_to_whitelist
    try:
        return await add_to_whitelist(
            asset_id=asset_id,
            account_id=holder.account_id,
            jurisdiction=holder.jurisdiction,
            investor_type=holder.investor_type,
            name=holder.name,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/validate-transfer")
async def validate_transfer(asset_id: int, from_id: str, to_id: str, amount: int):
    from server.agents.compliance import validate_transfer
    approved, reason = await validate_transfer(asset_id, from_id, to_id, amount)
    return {"approved": approved, "reason": reason}


@router.post("/purchase")
async def purchase_tokens(asset_id: int, account_id: str, amount: int):
    from server.agents.compliance import validate_transfer as check_transfer
    from server.arbitrum.token import transfer_tokens
    from server.arbitrum.audit import log_agent_action
    from server.arbitrum.client import get_operator_address as get_operator_account_id

    db = await get_db()
    try:
        asset = await db.execute_fetchone("SELECT * FROM assets WHERE id = ?", (asset_id,))
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        operator = str(get_operator_account_id())

        approved, reason = await check_transfer(asset_id, operator, account_id, amount)
        if not approved:
            raise HTTPException(status_code=403, detail=reason)

        tx_id = transfer_tokens(asset["token_id"], operator, account_id, amount, asset["decimals"])

        await db.execute(
            "UPDATE holders SET balance = balance - ? WHERE account_id = ? AND asset_id = ?",
            (amount, operator, asset_id)
        )
        await db.execute(
            "UPDATE holders SET balance = balance + ? WHERE account_id = ? AND asset_id = ?",
            (amount, account_id, asset_id)
        )
        await db.commit()
        topic_id = asset["topic_id"]
    finally:
        await db.close()

    if topic_id:
        log_agent_action(
            topic_id,
            agent="lifecycle",
            action="tokens_purchased",
            details={"buyer": account_id, "amount": amount, "tx_id": tx_id},
        )

    return {"tx_id": tx_id, "buyer": account_id, "amount": amount, "status": "completed"}


@router.get("/compliance")
async def get_compliance_status(asset_id: int):
    from server.agents.compliance import get_compliance_status
    return await get_compliance_status(asset_id)
