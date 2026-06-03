"""Shared channel brain — runs messages through the ChatAgent with a per-conversation
history and a write-confirmation state machine.

Value-moving commands never execute on the first message: the agent runs in
propose-mode (writes return a confirmation stub), the channel stores the pending
action and asks the user to reply YES. Only an affirmative reply executes it.
"""

from __future__ import annotations

import json
import logging

from app.chains.registry import get_registry
from app.database import get_sessionmaker
from app.services.ai import tools as tool_mod
from app.services.ai.agent import ChatAgent
from app.services.ai.tools import execute_tool

logger = logging.getLogger(__name__)

_AFFIRM = {"yes", "y", "confirm", "confirmed", "ok", "okay", "do it", "proceed"}
_DENY = {"no", "n", "cancel", "stop", "abort", "nope"}
_HISTORY_MAX = 10


class ChannelBrain:
    """One instance per process; keyed conversation state lives in dicts."""

    def __init__(self) -> None:
        self._history: dict[str, list[dict]] = {}
        self._pending: dict[str, dict] = {}  # conversation_id -> {tool, args}

    async def handle(self, conversation_id: str, text: str) -> str:
        text = (text or "").strip()
        if not text:
            return ""

        # 1. Resolve a pending confirmation first.
        pending = self._pending.get(conversation_id)
        if pending:
            low = text.lower()
            if low in _AFFIRM:
                self._pending.pop(conversation_id, None)
                return await self._execute_confirmed(conversation_id, pending)
            if low in _DENY:
                self._pending.pop(conversation_id, None)
                return "Cancelled — nothing was executed."
            # Anything else: drop the stale pending and treat as a new request.
            self._pending.pop(conversation_id, None)

        # 2. Run the agent in propose-mode (writes are not executed, just proposed).
        history = self._history.setdefault(conversation_id, [])
        token = tool_mod.propose_writes.set(True)
        try:
            async with get_sessionmaker()() as session:
                result = await ChatAgent(session).process(text, history, style="telegram")
        finally:
            tool_mod.propose_writes.reset(token)

        reply = result.get("response", "")
        history.append({"role": "user", "content": text})
        history.append({"role": "assistant", "content": reply})
        del history[: max(0, len(history) - _HISTORY_MAX)]

        # 3. If the agent proposed a write, stash it and ask for confirmation.
        if result.get("pending_write"):
            self._pending[conversation_id] = result["pending_write"]
            reply = f"{reply}\n\n⚠️ Reply *YES* to confirm, or *NO* to cancel."
        return reply

    async def _execute_confirmed(self, conversation_id: str, pending: dict) -> str:
        """Actually run the previously-proposed write tool (writes allowed)."""
        tool, args = pending["tool"], pending["args"]
        try:
            async with get_sessionmaker()() as session:
                result = await execute_tool(session, tool, args)  # propose_writes is False here
                await session.commit()
        except Exception as e:
            logger.error("confirmed action %s failed: %s", tool, e)
            return f"❌ {tool} failed: {e}"

        history = self._history.setdefault(conversation_id, [])
        history.append({"role": "assistant", "content": f"[executed {tool}] {json.dumps(result, default=str)[:500]}"})
        return self._summarize(tool, result)

    @staticmethod
    def _summarize(tool: str, r: dict) -> str:
        """Human summary of a confirmed action, with chain-correct explorer links so the
        user can verify everything on-chain (proof it's real, not a mockup)."""
        if not isinstance(r, dict):
            return f"✅ {tool} done."

        adapter = None
        if r.get("chain"):
            try:
                adapter = get_registry().adapter(r["chain"])
            except Exception:
                adapter = None

        lines = [f"✅ *{tool}* executed on {r.get('chain', 'chain')}."]
        labels = {
            "asset_id": "Asset ID", "status": "Status", "buyer": "Buyer", "amount": "Amount",
            "total_distributed_usdc": "Distributed (USDC)", "report_id": "Report ID",
            "tokens_wiped": "Tokens wiped", "tokens_burned": "Tokens burned",
        }
        for k, label in labels.items():
            if r.get(k) is not None:
                lines.append(f"- {label}: {r[k]}")

        token = r.get("token_id") or r.get("token_ref")
        if token:
            link = adapter.explorer_address(token) if adapter else None
            lines.append(f"- Token: {token}")
            if link:
                lines.append(f"  🔗 {link}")

        # Transaction links (single tx, or per-payment for coupons)
        txs = [r["tx"]] if r.get("tx") else []
        txs += [p["tx"] for p in (r.get("payments") or []) if p.get("tx")]
        for tx in txs:
            lines.append(f"🔗 tx: {adapter.explorer_tx(tx) if adapter else tx}")

        if r.get("download_url"):
            lines.append(f"📄 Report: {r['download_url']}")
        return "\n".join(lines)


brain = ChannelBrain()
