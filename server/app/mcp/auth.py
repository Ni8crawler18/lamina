"""MCP auth — pure-ASGI middleware: bearer token → scope, IP allowlist, rate limit.

Runs in front of the Streamable-HTTP handler. Resolves the caller's scope from a
bearer token and stashes it in a contextvar the tool dispatcher reads to gate writes.
"""

from __future__ import annotations

import contextvars
import hmac
import json
import logging
import time
from collections import deque

from app.config import get_settings

logger = logging.getLogger(__name__)

# Set per-request by the middleware; read by the tool dispatcher.
current_scope: contextvars.ContextVar[str | None] = contextvars.ContextVar("mcp_scope", default=None)
current_client: contextvars.ContextVar[str] = contextvars.ContextVar("mcp_client", default="")


def resolve_scope(token: str) -> str | None:
    """Map a bearer token to a scope using constant-time comparison."""
    s = get_settings()
    if s.mcp_admin_token and hmac.compare_digest(token, s.mcp_admin_token):
        return "admin"
    if s.mcp_read_token and hmac.compare_digest(token, s.mcp_read_token):
        return "read"
    return None


class McpAuthASGI:
    """Wraps the MCP ASGI app with token auth, IP allowlist, and per-token rate limiting."""

    def __init__(self, app):
        self.app = app
        self._hits: dict[str, deque] = {}

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        s = get_settings()
        client = (scope.get("client") or ("", 0))[0]

        # IP allowlist (optional)
        allow = {ip.strip() for ip in s.mcp_allowed_ips.split(",") if ip.strip()}
        if allow and client not in allow:
            return await self._deny(send, 403, "client IP not allowed")

        headers = {k.lower(): v for k, v in scope.get("headers", [])}
        auth = headers.get(b"authorization", b"").decode()
        token = auth[7:].strip() if auth[:7].lower() == "bearer " else ""
        scope_name = resolve_scope(token)
        if not scope_name:
            return await self._deny(send, 401, "unauthorized")

        if self._rate_limited(token, s.mcp_rate_limit_per_min):
            return await self._deny(send, 429, "rate limit exceeded")

        t1 = current_scope.set(scope_name)
        t2 = current_client.set(client)
        try:
            await self.app(scope, receive, send)
        finally:
            current_scope.reset(t1)
            current_client.reset(t2)

    def _rate_limited(self, token: str, limit: int) -> bool:
        now = time.monotonic()
        dq = self._hits.setdefault(token, deque())
        while dq and now - dq[0] > 60:
            dq.popleft()
        if len(dq) >= limit:
            return True
        dq.append(now)
        return False

    async def _deny(self, send, code: int, msg: str):
        body = json.dumps({"error": msg}).encode()
        await send({
            "type": "http.response.start",
            "status": code,
            "headers": [(b"content-type", b"application/json"), (b"www-authenticate", b"Bearer")],
        })
        await send({"type": "http.response.body", "body": body})
