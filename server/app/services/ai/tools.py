"""AI agent tools — schemas + dispatch to services.

Each tool maps to a service method. Results are enriched with the chain's
explorer_url so the agent can build links.
"""

from __future__ import annotations

from app.chains.registry import get_registry
from app.integrations.ofac.sdn import OFACScreener
from app.repositories.assets import AssetRepository
from app.repositories.holders import HolderRepository
from app.services.compliance_service import ComplianceService
from app.services.issuance_service import IssuanceService
from app.services.lifecycle_service import LifecycleService
from app.services.payout_service import PayoutService
from app.services.reporting_service import ReportingService

TOOLS = [
    {
        "name": "list_chains",
        "description": "List the chains available to issue/manage assets on (with enabled status).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "issue_asset",
        "description": "Tokenize a new real-world asset on a chosen chain. Deploys a compliant token "
                       "+ audit topic, schedules lifecycle events, whitelists the treasury.",
        "input_schema": {
            "type": "object",
            "properties": {
                "chain": {"type": "string", "description": "Chain slug, e.g. 'robinhood-testnet'"},
                "name": {"type": "string"},
                "symbol": {"type": "string"},
                "total_supply": {"type": "integer", "description": "smallest units (e.g. 1000000 = $10k @ 2 dec)"},
                "decimals": {"type": "integer"},
                "coupon_rate": {"type": "number", "description": "annual percent, e.g. 4.5"},
                "maturity_date": {"type": "string", "description": "ISO date"},
                "jurisdiction": {"type": "string"},
                "investor_type": {"type": "string"},
                "asset_type": {"type": "string"},
            },
            "required": ["chain", "name", "symbol", "total_supply"],
        },
    },
    {
        "name": "add_to_whitelist",
        "description": "Whitelist an investor for an asset (OFAC screening + on-chain KYC).",
        "input_schema": {
            "type": "object",
            "properties": {
                "asset_id": {"type": "integer"},
                "account_id": {"type": "string", "description": "investor wallet address"},
                "name": {"type": "string", "description": "full legal name (for OFAC screening)"},
                "jurisdiction": {"type": "string"},
                "investor_type": {"type": "string"},
            },
            "required": ["asset_id", "account_id"],
        },
    },
    {
        "name": "purchase_tokens",
        "description": "Transfer tokens from treasury to an investor with compliance checks.",
        "input_schema": {
            "type": "object",
            "properties": {
                "asset_id": {"type": "integer"},
                "account_id": {"type": "string"},
                "amount": {"type": "integer"},
            },
            "required": ["asset_id", "account_id", "amount"],
        },
    },
    {
        "name": "distribute_coupon",
        "description": "Distribute a coupon/dividend in USDC to all holders proportionally.",
        "input_schema": {"type": "object", "properties": {"asset_id": {"type": "integer"}},
                         "required": ["asset_id"]},
    },
    {
        "name": "update_nav",
        "description": "Update an asset's NAV; omit nav to pull from the yield oracle.",
        "input_schema": {"type": "object",
                         "properties": {"asset_id": {"type": "integer"}, "nav": {"type": "number"}},
                         "required": ["asset_id"]},
    },
    {
        "name": "execute_maturity",
        "description": "Settle maturity: wipe holder tokens, return USDC principal, burn treasury supply.",
        "input_schema": {"type": "object", "properties": {"asset_id": {"type": "integer"}},
                         "required": ["asset_id"]},
    },
    {
        "name": "generate_report",
        "description": "Generate a compliance/investor/audit PDF report for an asset.",
        "input_schema": {"type": "object",
                         "properties": {"asset_id": {"type": "integer"}, "period": {"type": "string"},
                                        "report_type": {"type": "string"}},
                         "required": ["asset_id"]},
    },
    {
        "name": "list_assets",
        "description": "List all tokenized assets (optionally filter by chain).",
        "input_schema": {"type": "object", "properties": {"chain": {"type": "string"}}},
    },
    {
        "name": "show_holders",
        "description": "Show holders of an asset with balances and KYC/OFAC status.",
        "input_schema": {"type": "object", "properties": {"asset_id": {"type": "integer"}},
                         "required": ["asset_id"]},
    },
    {
        "name": "show_compliance",
        "description": "Show compliance status for an asset (holders, regulations, OFAC flags).",
        "input_schema": {"type": "object", "properties": {"asset_id": {"type": "integer"}},
                         "required": ["asset_id"]},
    },
    {
        "name": "screen_ofac",
        "description": "Screen a name and/or address against the OFAC SDN sanctions list.",
        "input_schema": {"type": "object",
                         "properties": {"name": {"type": "string"}, "address": {"type": "string"}}},
    },
]


def _explorer(chain: str) -> str:
    try:
        return get_registry().get_config(chain).explorer_url
    except Exception:
        return ""


def _holder_dict(h) -> dict:
    return {"account_id": h.account_id, "name": h.name, "balance": h.balance,
            "kyc_status": h.kyc_status, "whitelisted": h.whitelisted,
            "jurisdiction": h.jurisdiction, "investor_type": h.investor_type,
            "ofac_status": h.ofac_status}


def _asset_dict(a) -> dict:
    return {"id": a.id, "chain": a.chain, "name": a.name, "symbol": a.symbol,
            "token_id": a.token_id, "status": a.status, "nav": a.nav,
            "coupon_rate": a.coupon_rate, "asset_type": a.asset_type,
            "explorer_url": _explorer(a.chain)}


async def execute_tool(session, name: str, args: dict) -> dict:
    """Dispatch a tool call to the right service. Returns a JSON-serializable dict."""
    if name == "list_chains":
        return {"chains": [
            {"slug": c.slug, "name": c.name, "native_symbol": c.native_symbol,
             "enabled": c.enabled, "explorer_url": c.explorer_url}
            for c in get_registry().list_all()
        ]}

    if name == "issue_asset":
        asset = await IssuanceService(session).issue_asset(**args)
        return {**_asset_dict(asset), "token_ref": asset.token_id,
                "audit_topic": asset.topic_id}

    if name == "add_to_whitelist":
        h = await ComplianceService(session).add_to_whitelist(
            args["asset_id"], args["account_id"], args.get("jurisdiction", "US"),
            args.get("investor_type", "accredited"), args.get("name"))
        return _holder_dict(h)

    if name == "purchase_tokens":
        res = await IssuanceService(session).purchase(
            args["asset_id"], args["account_id"], args["amount"])
        return {**res, "explorer_url": _explorer(res["chain"])}

    if name == "distribute_coupon":
        return await PayoutService(session).distribute_coupon(args["asset_id"])

    if name == "update_nav":
        svc = LifecycleService(session)
        if args.get("nav") is not None:
            return await svc.update_nav(args["asset_id"], args["nav"])
        return await svc.update_nav_from_oracle(args["asset_id"])

    if name == "execute_maturity":
        return await LifecycleService(session).execute_maturity(args["asset_id"])

    if name == "generate_report":
        res = await ReportingService(session).generate_report(
            args["asset_id"], args.get("period", "Q1 2026"), args.get("report_type", "compliance"))
        res["download_url"] = f"/api/reports/{res['report_id']}/download"
        return res

    if name == "list_assets":
        repo = AssetRepository(session)
        rows = await (repo.list_by_chain(args["chain"]) if args.get("chain") else repo.list())
        return {"assets": [_asset_dict(a) for a in rows]}

    if name == "show_holders":
        rows = await HolderRepository(session).list_for_asset(args["asset_id"])
        return {"holders": [_holder_dict(h) for h in rows]}

    if name == "show_compliance":
        return await ComplianceService(session).get_compliance_status(args["asset_id"])

    if name == "screen_ofac":
        return OFACScreener.get_instance().screen(name=args.get("name"), address=args.get("address"))

    return {"error": f"unknown tool '{name}'"}
