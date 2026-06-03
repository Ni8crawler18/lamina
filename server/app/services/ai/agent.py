"""Lamina AI agent — Claude with tool use over the RWA services."""

from __future__ import annotations

import json
import logging

from app.config import get_settings
from app.services.ai.prompts import system_prompt
from app.services.ai.tools import TOOLS, execute_tool

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5-20251001"
MAX_TOOL_ROUNDS = 8


class ChatAgent:
    def __init__(self, session):
        self.session = session

    async def process(self, message: str, history: list | None = None, style: str | None = None) -> dict:
        settings = get_settings()
        if not settings.anthropic_api_key:
            return {"response": "AI is not configured (set ANTHROPIC_API_KEY).", "actions_taken": []}

        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        system = system_prompt()
        if style == "telegram":
            system += (
                "\n\nYou are replying in a Telegram chat. Keep responses SHORT and scannable: "
                "no big headers, no markdown tables. Use *bold* for key terms and '- ' bullets. "
                "Lead with the answer; avoid long intros."
            )

        messages = []
        for m in (history or [])[-10:]:
            if m.get("role") in ("user", "assistant") and m.get("content"):
                messages.append({"role": m["role"], "content": m["content"]})
        messages.append({"role": "user", "content": message})

        actions_taken: list[dict] = []
        pending_write: dict | None = None
        for _ in range(MAX_TOOL_ROUNDS):
            resp = client.messages.create(
                model=MODEL, max_tokens=2048, system=system,
                tools=TOOLS, messages=messages,
            )
            if resp.stop_reason != "tool_use":
                text = "".join(b.text for b in resp.content if b.type == "text")
                return {"response": text, "actions_taken": actions_taken,
                        "pending_write": pending_write}

            messages.append({"role": "assistant", "content": resp.content})
            tool_results = []
            for block in resp.content:
                if block.type != "tool_use":
                    continue
                logger.info("agent tool: %s(%s)", block.name, block.input)
                try:
                    result = await execute_tool(self.session, block.name, dict(block.input))
                    await self.session.commit()
                    if isinstance(result, dict) and result.get("confirmation_required"):
                        pending_write = {"tool": result["tool"], "args": result["args"]}
                    actions_taken.append({"tool": block.name, "status": "success"})
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id,
                                         "content": json.dumps(result, default=str)})
                except Exception as e:
                    await self.session.rollback()
                    logger.error("tool %s failed: %s", block.name, e)
                    actions_taken.append({"tool": block.name, "status": "error", "error": str(e)})
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id,
                                         "content": json.dumps({"error": str(e)}), "is_error": True})
            messages.append({"role": "user", "content": tool_results})

        return {"response": "Stopped after too many tool rounds.", "actions_taken": actions_taken}
