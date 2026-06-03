"""Telegram channel — long-polling (no public URL needed).

Polls getUpdates, enforces a chat-ID allowlist, routes messages through the shared
ChannelBrain (which handles the write-confirmation flow), and replies via sendMessage.
Runs as a background asyncio task started/stopped by the app lifespan.
"""

from __future__ import annotations

import asyncio
import logging

import aiohttp
import telegramify_markdown

from app.channels.base import brain
from app.config import get_settings

logger = logging.getLogger(__name__)

_API = "https://api.telegram.org/bot{token}/{method}"
_task: asyncio.Task | None = None


def _allowed_ids() -> set[str]:
    raw = get_settings().telegram_allowed_chat_ids
    return {x.strip() for x in raw.split(",") if x.strip()}


async def _send(session: aiohttp.ClientSession, token: str, chat_id, text: str) -> None:
    if not text:
        return
    url = _API.format(token=token, method="sendMessage")
    base = {"chat_id": chat_id, "disable_web_page_preview": True}

    # Render the agent's GitHub-flavored markdown as Telegram MarkdownV2.
    try:
        rendered = telegramify_markdown.markdownify(text)[:4000]
        async with session.post(url, json={**base, "text": rendered, "parse_mode": "MarkdownV2"}) as r:
            if r.status == 200:
                return
            logger.warning("telegram MarkdownV2 send %s: %s", r.status, (await r.text())[:200])
    except Exception as e:
        logger.warning("telegram markdown render/send failed, falling back to plain: %s", e)

    # Fallback: plain text (URLs still auto-link in Telegram).
    try:
        async with session.post(url, json={**base, "text": text[:4000]}) as r:
            if r.status != 200:
                logger.warning("telegram plain send %s: %s", r.status, (await r.text())[:200])
    except Exception as e:
        logger.error("telegram send failed: %s", e)


async def _poll_loop() -> None:
    token = get_settings().telegram_bot_token
    allowed = _allowed_ids()
    offset = 0
    logger.info("Telegram poller started (allowlist: %s)", allowed or "OPEN — set TELEGRAM_ALLOWED_CHAT_IDS!")
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                url = _API.format(token=token, method="getUpdates")
                async with session.get(url, params={"offset": offset, "timeout": 25},
                                       timeout=aiohttp.ClientTimeout(total=35)) as r:
                    data = await r.json()
                for upd in data.get("result", []):
                    offset = upd["update_id"] + 1
                    msg = upd.get("message") or upd.get("edited_message")
                    if not msg or "text" not in msg:
                        continue
                    chat_id = msg["chat"]["id"]
                    if allowed and str(chat_id) not in allowed:
                        logger.warning("telegram: ignoring message from non-allowlisted chat %s", chat_id)
                        continue
                    reply = await brain.handle(str(chat_id), msg["text"])
                    await _send(session, token, chat_id, reply)
            except asyncio.CancelledError:
                logger.info("Telegram poller stopping")
                raise
            except Exception as e:
                logger.error("telegram poll error: %s", e)
                await asyncio.sleep(3)


def start() -> None:
    global _task
    s = get_settings()
    if not s.telegram_bot_token:
        logger.warning("channels_enabled but TELEGRAM_BOT_TOKEN not set — Telegram disabled")
        return
    if _task is None or _task.done():
        _task = asyncio.create_task(_poll_loop())


async def stop() -> None:
    global _task
    if _task and not _task.done():
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
    _task = None
