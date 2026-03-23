"""Chat Agent — Natural language interface powered by Claude API with tool use."""

import json
import logging
from datetime import datetime

from server.config import get_settings
from server.database import get_db

logger = logging.getLogger(__name__)

# Tool definitions for Claude
TOOLS = [
    {
        "name": "issue_asset",
        "description": "Tokenize a new real-world asset (bond, equity, fund) on Hedera. Creates HTS token, HCS audit topic, configures compliance, schedules lifecycle events.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Full name of the asset, e.g. 'US Treasury Bond 2031'"},
                "symbol": {"type": "string", "description": "Token symbol, e.g. 'UST31'"},
                "total_supply": {"type": "integer", "description": "Total token supply (in smallest unit, e.g. 1000000 for $10,000 with 2 decimals)"},
                "coupon_rate": {"type": "number", "description": "Annual coupon rate as decimal, e.g. 0.045 for 4.5%"},
                "maturity_date": {"type": "string", "description": "ISO date when the bond matures, e.g. '2031-02-25'"},
                "jurisdiction": {"type": "string", "description": "Jurisdiction code: US, EU, UK, SG"},
                "investor_type": {"type": "string", "description": "Investor type: accredited, qualified, professional, institutional"},
                "asset_type": {"type": "string", "description": "Asset type: bond, equity, fund, real_estate"},
            },
            "required": ["name", "symbol", "total_supply"],
        },
    },
    {
        "name": "add_to_whitelist",
        "description": "Add an investor to the KYC whitelist for a specific asset. Required before they can receive tokens. If no account_id is provided, a new Hedera account will be created automatically. OFAC sanctions screening is performed automatically.",
        "input_schema": {
            "type": "object",
            "properties": {
                "asset_id": {"type": "integer", "description": "Asset ID"},
                "account_id": {"type": "string", "description": "Hedera account ID (e.g. '0.0.1234'). Leave empty to auto-create a new account."},
                "name": {"type": "string", "description": "Investor's full legal name (used for OFAC sanctions screening)"},
                "jurisdiction": {"type": "string", "description": "Investor's jurisdiction: US, EU, UK, SG"},
                "investor_type": {"type": "string", "description": "Investor type: accredited, qualified, professional"},
            },
            "required": ["asset_id"],
        },
    },
    {
        "name": "show_holders",
        "description": "Show all token holders for a specific asset with their balances and KYC status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "asset_id": {"type": "integer", "description": "Asset ID"},
            },
            "required": ["asset_id"],
        },
    },
    {
        "name": "distribute_coupon",
        "description": "Trigger coupon payment distribution to all holders of an asset proportional to their holdings.",
        "input_schema": {
            "type": "object",
            "properties": {
                "asset_id": {"type": "integer", "description": "Asset ID"},
            },
            "required": ["asset_id"],
        },
    },
    {
        "name": "generate_report",
        "description": "Generate a compliance report (PDF) for a specific asset and reporting period.",
        "input_schema": {
            "type": "object",
            "properties": {
                "asset_id": {"type": "integer", "description": "Asset ID"},
                "period": {"type": "string", "description": "Reporting period, e.g. 'Q1 2026'"},
            },
            "required": ["asset_id"],
        },
    },
    {
        "name": "execute_maturity",
        "description": "Execute maturity settlement for a bond: redeem all tokens, return principal, burn tokens.",
        "input_schema": {
            "type": "object",
            "properties": {
                "asset_id": {"type": "integer", "description": "Asset ID"},
            },
            "required": ["asset_id"],
        },
    },
    {
        "name": "list_assets",
        "description": "List all tokenized assets managed by Lamina.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "show_compliance",
        "description": "Show compliance status for an asset including holder counts, jurisdiction breakdown, and blocked transfers.",
        "input_schema": {
            "type": "object",
            "properties": {
                "asset_id": {"type": "integer", "description": "Asset ID"},
            },
            "required": ["asset_id"],
        },
    },
    {
        "name": "purchase_tokens",
        "description": "Purchase/transfer tokens from the treasury to an investor account. Performs compliance check, executes real HTS transfer on Hedera, and logs to HCS.",
        "input_schema": {
            "type": "object",
            "properties": {
                "asset_id": {"type": "integer", "description": "Asset ID"},
                "account_id": {"type": "string", "description": "Buyer's Hedera account ID (e.g. '0.0.1234')"},
                "amount": {"type": "integer", "description": "Number of tokens to purchase"},
            },
            "required": ["asset_id", "account_id", "amount"],
        },
    },
    {
        "name": "validate_transfer",
        "description": "Validate whether a token transfer between two accounts is compliant. Checks KYC, jurisdiction, sanctions, and balance.",
        "input_schema": {
            "type": "object",
            "properties": {
                "asset_id": {"type": "integer", "description": "Asset ID"},
                "from_id": {"type": "string", "description": "Sender's Hedera account ID"},
                "to_id": {"type": "string", "description": "Receiver's Hedera account ID"},
                "amount": {"type": "integer", "description": "Number of tokens"},
            },
            "required": ["asset_id", "from_id", "to_id", "amount"],
        },
    },
    {
        "name": "update_nav",
        "description": "Update the Net Asset Value (NAV) for a tokenized asset.",
        "input_schema": {
            "type": "object",
            "properties": {
                "asset_id": {"type": "integer", "description": "Asset ID"},
                "nav": {"type": "number", "description": "New NAV value in dollars, e.g. 100.50"},
            },
            "required": ["asset_id", "nav"],
        },
    },
    {
        "name": "screen_ofac",
        "description": "Screen a name or crypto address against the OFAC SDN (Specially Designated Nationals) sanctions list. Returns whether there's a match and the match score.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Full name to screen against the SDN list"},
                "address": {"type": "string", "description": "Crypto address or Hedera account ID to screen"},
            },
        },
    },
]

SYSTEM_PROMPT = """You are Lamina, an autonomous RWA (Real-World Asset) lifecycle management agent on Hedera.

You help fund managers tokenize and manage real-world assets like bonds, equities, and funds. You can:
1. Tokenize new assets (create HTS tokens with compliance)
2. Manage KYC whitelists (add/remove investors, with OFAC sanctions screening)
3. Distribute coupon payments to holders
4. Generate compliance reports
5. Execute maturity settlement
6. Show asset details, holders, and compliance status
7. Purchase/transfer tokens to investor accounts
8. Validate transfers for compliance
9. Update asset NAV (Net Asset Value)
10. Screen names/addresses against the OFAC SDN sanctions list

When adding investors to a whitelist, always ask for their full legal name so OFAC screening can be performed. OFAC screening is automatic during whitelisting.

When a user asks to tokenize an asset, extract the details and use the issue_asset tool. For example:
- "$10M 5-year US Treasury bond" → total_supply=1000000000 (with 2 decimals), maturity in 5 years, asset_type=bond
- "US accredited investors only" → jurisdiction=US, investor_type=accredited

When a user asks to purchase tokens, use the purchase_tokens tool. For example:
- "Buy 500 tokens for 0.0.12345" → purchase_tokens with the account_id and amount

Always confirm actions with clear summaries. Be concise and professional.
If you need an asset_id and the user hasn't specified one, use list_assets first to find it.

IMPORTANT: Never generate or guess URLs. Do not include links to HashScan, documentation, or any external site unless the data comes directly from a tool result (like a transaction ID). If you need to reference a transaction, just show the transaction ID — do not construct a URL.

Current date: """ + datetime.utcnow().strftime("%Y-%m-%d")


async def process_message(message: str, history: list = None) -> dict:
    """Process a natural language message through Claude with tool use."""
    settings = get_settings()

    if not settings.anthropic_api_key:
        return {
            "response": "Claude API key not configured. Please set ANTHROPIC_API_KEY in .env",
            "actions_taken": [],
        }

    import anthropic
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    actions_taken = []

    # Build messages with conversation history
    messages = []
    if history:
        for msg in history[-10:]:  # Keep last 10 messages for context
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})

    # Agentic loop: keep processing until Claude gives a final text response
    while True:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Check if Claude wants to use tools
        if response.stop_reason == "tool_use":
            # Process all tool calls
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    logger.info(f"Chat agent calling tool: {tool_name}({tool_input})")

                    try:
                        result = await _execute_tool(tool_name, tool_input)
                        actions_taken.append({
                            "tool": tool_name,
                            "input": tool_input,
                            "result": result,
                            "status": "success",
                        })
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result, default=str),
                        })
                    except Exception as e:
                        logger.error(f"Tool execution failed: {tool_name}: {e}")
                        actions_taken.append({
                            "tool": tool_name,
                            "input": tool_input,
                            "error": str(e),
                            "status": "error",
                        })
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps({"error": str(e)}),
                            "is_error": True,
                        })

            # Add assistant message and tool results, continue the loop
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
        else:
            # Claude gave a final text response
            text_response = ""
            for block in response.content:
                if hasattr(block, "text"):
                    text_response += block.text

            return {
                "response": text_response,
                "actions_taken": actions_taken,
            }


async def _execute_tool(tool_name: str, tool_input: dict) -> dict:
    """Execute a tool call from the chat agent."""
    if tool_name == "issue_asset":
        from server.agents.lifecycle import issue_asset
        return await issue_asset(
            name=tool_input["name"],
            symbol=tool_input["symbol"],
            total_supply=tool_input["total_supply"],
            coupon_rate=tool_input.get("coupon_rate", 0.0),
            maturity_date=tool_input.get("maturity_date"),
            jurisdiction=tool_input.get("jurisdiction", "US"),
            investor_type=tool_input.get("investor_type", "accredited"),
            asset_type=tool_input.get("asset_type", "bond"),
        )

    elif tool_name == "add_to_whitelist":
        from server.agents.compliance import add_to_whitelist
        return await add_to_whitelist(
            asset_id=tool_input["asset_id"],
            account_id=tool_input.get("account_id"),
            jurisdiction=tool_input.get("jurisdiction", "US"),
            investor_type=tool_input.get("investor_type", "accredited"),
            create_account=not tool_input.get("account_id"),
            name=tool_input.get("name"),
        )

    elif tool_name == "show_holders":
        db = await get_db()
        try:
            rows = await db.execute_fetchall(
                "SELECT * FROM holders WHERE asset_id = ? ORDER BY balance DESC",
                (tool_input["asset_id"],)
            )
            return {"holders": [dict(row) for row in rows]}
        finally:
            await db.close()

    elif tool_name == "distribute_coupon":
        from server.agents.lifecycle import distribute_coupon
        return await distribute_coupon(tool_input["asset_id"])

    elif tool_name == "generate_report":
        from server.agents.reporting import generate_report
        return await generate_report(
            tool_input["asset_id"],
            tool_input.get("period", "Q1 2026"),
        )

    elif tool_name == "execute_maturity":
        from server.agents.lifecycle import execute_maturity
        return await execute_maturity(tool_input["asset_id"])

    elif tool_name == "list_assets":
        db = await get_db()
        try:
            rows = await db.execute_fetchall("SELECT * FROM assets ORDER BY created_at DESC")
            return {"assets": [dict(row) for row in rows]}
        finally:
            await db.close()

    elif tool_name == "show_compliance":
        from server.agents.compliance import get_compliance_status
        return await get_compliance_status(tool_input["asset_id"])

    elif tool_name == "purchase_tokens":
        from server.agents.compliance import validate_transfer as check_transfer
        from server.hedera.token import transfer_tokens
        from server.hedera.consensus import log_agent_action as log_action
        from server.hedera.client import get_operator_account_id

        asset_id = tool_input["asset_id"]
        account_id = tool_input["account_id"]
        amount = tool_input["amount"]

        db = await get_db()
        try:
            asset = await db.execute_fetchone("SELECT * FROM assets WHERE id = ?", (asset_id,))
            if not asset:
                return {"error": "Asset not found"}

            operator = str(get_operator_account_id())

            # Compliance check
            approved, reason = await check_transfer(asset_id, operator, account_id, amount)
            if not approved:
                return {"error": f"Transfer blocked: {reason}", "approved": False}

            # Real on-chain token transfer
            tx_id = transfer_tokens(asset["token_id"], operator, account_id, amount, asset["decimals"])

            # Update balances
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
            log_action(
                topic_id,
                agent="lifecycle",
                action="tokens_purchased",
                details={"buyer": account_id, "amount": amount, "tx_id": tx_id},
            )

        return {"tx_id": tx_id, "buyer": account_id, "amount": amount, "status": "completed"}

    elif tool_name == "validate_transfer":
        from server.agents.compliance import validate_transfer as check_transfer
        approved, reason = await check_transfer(
            tool_input["asset_id"],
            tool_input["from_id"],
            tool_input["to_id"],
            tool_input["amount"],
        )
        return {"approved": approved, "reason": reason}

    elif tool_name == "update_nav":
        from server.agents.lifecycle import update_nav
        return await update_nav(tool_input["asset_id"], tool_input["nav"])

    elif tool_name == "screen_ofac":
        from server.ofac.sdn import OFACScreener
        screener = OFACScreener.get_instance()
        if not screener.loaded:
            return {"error": "OFAC screener not loaded"}
        result = screener.screen(
            name=tool_input.get("name"),
            address=tool_input.get("address"),
        )
        return {
            "is_match": result["is_match"],
            "score": result.get("score", 0),
            "match_type": result.get("match_type"),
            "matched_entity": result["details"]["name"] if result.get("details") else None,
            "program": result["details"]["program"] if result.get("details") else None,
        }

    else:
        raise ValueError(f"Unknown tool: {tool_name}")
