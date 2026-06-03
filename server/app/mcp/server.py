"""Lamina MCP server.

Exposes the RWA tool layer (services/ai/tools.py) over Streamable HTTP, reusing the
same execute_tool dispatch as the AI agent. READ tools are always available; WRITE
(value-moving) tools require admin scope AND mcp_allow_writes. Every call is audited.

Mounted into the FastAPI app at /mcp behind McpAuthASGI; the session manager's
lifespan is entered by the app lifespan.
"""

from __future__ import annotations

import json
import logging

import mcp.types as types
from mcp.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

from app.config import get_settings
from app.database import get_sessionmaker
from app.mcp.auth import McpAuthASGI, current_client, current_scope
from app.models.orm import McpAudit
from app.services.ai.tools import TOOLS, execute_tool

logger = logging.getLogger(__name__)

# Read-only tools (data exposure only). Everything else in TOOLS moves value/state.
READ_TOOLS = {"list_chains", "list_assets", "show_holders", "show_compliance", "screen_ofac"}


def _is_write(name: str) -> bool:
    return name not in READ_TOOLS


def _visible_tools() -> list[dict]:
    """Tools the current caller may see: reads always; writes only for admin + allow_writes."""
    s = get_settings()
    scope = current_scope.get()
    out = []
    for t in TOOLS:
        if _is_write(t["name"]) and not (s.mcp_allow_writes and scope == "admin"):
            continue
        out.append(t)
    return out


async def _audit(tool: str, scope: str | None, status: str, error: str | None) -> None:
    try:
        async with get_sessionmaker()() as session:
            session.add(McpAudit(
                tool=tool, scope=scope, status=status,
                client_ip=current_client.get() or None, error=(error or None) and error[:500],
            ))
            await session.commit()
    except Exception as e:  # never let auditing break a call
        logger.error("mcp audit write failed: %s", e)


_server = Server("lamina-rwa")


@_server.list_tools()
async def _list_tools() -> list[types.Tool]:
    return [
        types.Tool(name=t["name"], description=t["description"], inputSchema=t["input_schema"])
        for t in _visible_tools()
    ]


@_server.call_tool()
async def _call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    scope = current_scope.get()
    s = get_settings()
    status, error = "ok", None
    try:
        if _is_write(name):
            if not s.mcp_allow_writes:
                status = "denied"
                raise PermissionError("write tools are disabled on this MCP server")
            if scope != "admin":
                status = "denied"
                raise PermissionError("admin scope required for write tools")
        async with get_sessionmaker()() as session:
            result = await execute_tool(session, name, dict(arguments or {}))
            await session.commit()
        return [types.TextContent(type="text", text=json.dumps(result, default=str))]
    except Exception as e:
        if status == "ok":
            status = "error"
        error = str(e)
        return [types.TextContent(type="text", text=json.dumps({"error": str(e)}))]
    finally:
        await _audit(name, scope, status, error)


# ── Streamable-HTTP transport (stateless tool server) ────────────────────────
_manager: StreamableHTTPSessionManager | None = None


def get_session_manager() -> StreamableHTTPSessionManager:
    global _manager
    if _manager is None:
        _manager = StreamableHTTPSessionManager(app=_server, json_response=True, stateless=True)
    return _manager


def mcp_asgi_app():
    """Auth-wrapped ASGI app to mount at /mcp."""
    manager = get_session_manager()

    async def handle(scope, receive, send):
        await manager.handle_request(scope, receive, send)

    return McpAuthASGI(handle)
