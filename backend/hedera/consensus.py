"""Hedera Consensus Service (HCS) operations — immutable audit log."""

import json
import logging
import base64
from datetime import datetime

import aiohttp
from hiero_sdk_python import (
    TopicCreateTransaction,
    TopicMessageSubmitTransaction,
    TopicId,
)
from backend.hedera.client import get_hedera_client, get_operator_private_key
from backend.config import get_settings

logger = logging.getLogger(__name__)


def create_topic(memo: str = "") -> str:
    """Create an HCS topic for audit logging. Returns topic_id string."""
    client = get_hedera_client()
    admin_key = get_operator_private_key()

    tx = TopicCreateTransaction()
    tx.set_memo(memo)
    tx.set_admin_key(admin_key)
    tx.set_submit_key(admin_key)

    receipt = tx.execute(client)
    topic_id = str(receipt.topic_id)
    logger.info(f"Created HCS topic {topic_id}: {memo}")
    return topic_id


def submit_message(topic_id: str, message: dict) -> int:
    """Submit a JSON message to an HCS topic. Returns sequence number."""
    client = get_hedera_client()
    submit_key = get_operator_private_key()

    payload = json.dumps({
        **message,
        "timestamp": datetime.utcnow().isoformat(),
    })

    tx = TopicMessageSubmitTransaction()
    tx.set_topic_id(TopicId.from_string(topic_id))
    tx.set_message(payload)
    tx.freeze_with(client)
    tx.sign(submit_key)

    receipt = tx.execute(client)
    seq = receipt.topic_sequence_number
    logger.info(f"HCS message #{seq} to {topic_id}: {message.get('action', 'unknown')}")
    return seq


async def get_topic_messages(topic_id: str, limit: int = 100) -> list[dict]:
    """Fetch messages from HCS topic via Mirror Node REST API."""
    settings = get_settings()
    url = f"{settings.mirror_node_url}/api/v1/topics/{topic_id}/messages"
    params = {"limit": limit, "order": "desc"}

    messages = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    logger.error(f"Mirror Node error {resp.status} for topic {topic_id}")
                    return messages
                data = await resp.json()

        for msg in data.get("messages", []):
            try:
                decoded = base64.b64decode(msg["message"]).decode("utf-8")
                parsed = json.loads(decoded)
            except (json.JSONDecodeError, UnicodeDecodeError):
                parsed = {"raw": base64.b64decode(msg["message"]).decode("utf-8", errors="replace")}

            messages.append({
                "sequence_number": msg.get("sequence_number"),
                "consensus_timestamp": msg.get("consensus_timestamp"),
                "content": parsed,
            })
    except aiohttp.ClientError as e:
        logger.error(f"Failed to fetch topic messages: {e}")

    return messages


def log_agent_action(topic_id: str, agent: str, action: str, details: dict | None = None) -> int:
    """Convenience: log an agent action to HCS."""
    message = {
        "agent": agent,
        "action": action,
        "details": details or {},
    }
    return submit_message(topic_id, message)
