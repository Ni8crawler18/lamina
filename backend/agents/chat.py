"""Chat Agent — Natural language interface powered by Claude API with tool use."""

import json
import logging
from datetime import datetime

from backend.config import get_settings
from backend.database import get_db

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
        "description": "Add an investor to the KYC whitelist for a specific asset. Required before they can receive tokens.",
        "input_schema": {
            "type": "object",
            "properties": {
                "asset_id": {"type": "integer", "description": "Asset ID"},
                "account_id": {"type": "string", "description": "Hedera account ID (e.g. '0.0.1234')"},
                "jurisdiction": {"type": "string", "description": "Investor's jurisdiction: US, EU, UK, SG"},
                "investor_type": {"type": "string", "description": "Investor type: accredited, qualified, professional"},
            },
            "required": ["asset_id", "account_id"],
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
]

SYSTEM_PROMPT = """You are Lamina, an autonomous RWA (Real-World Asset) lifecycle management agent on Hedera.

You help fund managers tokenize and manage real-world assets like bonds, equities, and funds. You can:
1. Tokenize new assets (create HTS tokens with compliance)
2. Manage KYC whitelists (add/remove investors)
3. Distribute coupon payments to holders
4. Generate compliance reports
5. Execute maturity settlement
6. Show asset details, holders, and compliance status

When a user asks to tokenize an asset, extract the details and use the issue_asset tool. For example:
- "$10M 5-year US Treasury bond" → total_supply=1000000000 (with 2 decimals), maturity in 5 years, asset_type=bond
- "US accredited investors only" → jurisdiction=US, investor_type=accredited

Always confirm actions with clear summaries. Be concise and professional.
If you need an asset_id and the user hasn't specified one, use list_assets first to find it.

Current date: """ + datetime.utcnow().strftime("%Y-%m-%d")


async def process_message(message: str) -> dict:
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
    messages = [{"role": "user", "content": message}]

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
        from backend.agents.lifecycle import issue_asset
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
        from backend.agents.compliance import add_to_whitelist
        return await add_to_whitelist(
            asset_id=tool_input["asset_id"],
            account_id=tool_input["account_id"],
            jurisdiction=tool_input.get("jurisdiction", "US"),
            investor_type=tool_input.get("investor_type", "accredited"),
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
        from backend.agents.lifecycle import distribute_coupon
        return await distribute_coupon(tool_input["asset_id"])

    elif tool_name == "generate_report":
        from backend.agents.reporting import generate_compliance_report
        return await generate_compliance_report(
            tool_input["asset_id"],
            tool_input.get("period", "Q1 2026"),
        )

    elif tool_name == "execute_maturity":
        from backend.agents.lifecycle import execute_maturity
        return await execute_maturity(tool_input["asset_id"])

    elif tool_name == "list_assets":
        db = await get_db()
        try:
            rows = await db.execute_fetchall("SELECT * FROM assets ORDER BY created_at DESC")
            return {"assets": [dict(row) for row in rows]}
        finally:
            await db.close()

    elif tool_name == "show_compliance":
        from backend.agents.compliance import get_compliance_status
        return await get_compliance_status(tool_input["asset_id"])

    else:
        raise ValueError(f"Unknown tool: {tool_name}")
