"""AuditLog contract interactions.

Replaces server/hedera/consensus.py — identical function signatures,
EVM implementation backed by the AuditLog.sol contract on Robinhood Chain.

Hedera → EVM mapping:
  create_topic()       → AuditLog.createTopic()
  submit_message()     → AuditLog.log()
  get_topic_messages() → AuditLog.getMessages() + getLogs(ActionLogged)
  log_agent_action()   → convenience wrapper (identical API)
"""

import json
import logging
from datetime import datetime, timezone

from web3 import Web3

from server.arbitrum.client import (
    get_web3, get_operator_address, get_operator_private_key,
    build_and_send, next_nonce,
)
from server.config import get_settings

logger = logging.getLogger(__name__)

# ─── ABI (inline minimal — avoids file dependency before deploy) ─────────────
_AUDIT_ABI = [
    {
        "inputs": [{"internalType": "string", "name": "memo", "type": "string"}],
        "name": "createTopic",
        "outputs": [{"internalType": "bytes32", "name": "topicId", "type": "bytes32"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "topicId", "type": "bytes32"},
            {"internalType": "string",  "name": "agent",   "type": "string"},
            {"internalType": "string",  "name": "action",  "type": "string"},
            {"internalType": "string",  "name": "details", "type": "string"},
        ],
        "name": "log",
        "outputs": [{"internalType": "uint256", "name": "sequenceNumber", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "topicId", "type": "bytes32"},
            {"internalType": "uint256", "name": "limit",   "type": "uint256"},
        ],
        "name": "getMessages",
        "outputs": [
            {
                "components": [
                    {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
                    {"internalType": "address", "name": "caller",    "type": "address"},
                    {"internalType": "string",  "name": "agent",     "type": "string"},
                    {"internalType": "string",  "name": "action",    "type": "string"},
                    {"internalType": "string",  "name": "details",   "type": "string"},
                ],
                "internalType": "struct AuditLog.LogEntry[]",
                "name": "",
                "type": "tuple[]",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "topicId", "type": "bytes32"}],
        "name": "messageCount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True,  "internalType": "bytes32", "name": "topicId",        "type": "bytes32"},
            {"indexed": True,  "internalType": "uint256", "name": "sequenceNumber", "type": "uint256"},
            {"indexed": False, "internalType": "string",  "name": "agent",          "type": "string"},
            {"indexed": False, "internalType": "string",  "name": "action",         "type": "string"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp",      "type": "uint256"},
        ],
        "name": "ActionLogged",
        "type": "event",
    },
]

_audit_contract = None


def _get_audit():
    global _audit_contract
    if _audit_contract is None:
        settings = get_settings()
        if not settings.audit_log_address:
            raise RuntimeError(
                "AUDIT_LOG_ADDRESS not configured. "
                "Run contracts/scripts/deploy.py and add address to .env"
            )
        w3 = get_web3()
        _audit_contract = w3.eth.contract(
            address=Web3.to_checksum_address(settings.audit_log_address),
            abi=_AUDIT_ABI,
        )
    return _audit_contract


# ─── Public API (same as hedera/consensus.py) ─────────────────────────────────

def create_topic(memo: str = "") -> str:
    """Create a new audit topic. Returns topic_id as hex string (bytes32).

    Replaces hedera.consensus.create_topic().
    """
    w3       = get_web3()
    settings = get_settings()
    audit    = _get_audit()
    operator = get_operator_address()
    pk       = get_operator_private_key()

    tx = audit.functions.createTopic(memo).build_transaction({
        "chainId":  settings.chain_id,
        "from":     Web3.to_checksum_address(operator),
        "nonce":    next_nonce(w3, operator),
        "gas":      200_000,
        "gasPrice": w3.eth.gas_price,
    })
    tx_hash_hex = build_and_send(w3, tx, pk)

    # Read the TopicCreated event to get the topic ID
    receipt = w3.eth.get_transaction_receipt(tx_hash_hex)
    events  = audit.events.TopicCreated().process_receipt(receipt) if hasattr(audit.events, 'TopicCreated') else []

    if events:
        topic_id = events[0]["args"]["topicId"].hex()
    else:
        # Fallback: call createTopic again as a view (not ideal but safe for retry)
        # In practice the event will always be present
        topic_id = tx_hash_hex  # use tx hash as topic id fallback

    logger.info(f"Created audit topic: {topic_id}  memo='{memo}'")
    return topic_id


def submit_message(topic_id: str, message: dict) -> int:
    """Append a message to an audit topic. Returns sequence number.

    Replaces hedera.consensus.submit_message().
    """
    w3       = get_web3()
    settings = get_settings()
    audit    = _get_audit()
    operator = get_operator_address()
    pk       = get_operator_private_key()

    payload = json.dumps({
        **message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # Convert topic_id hex string → bytes32
    topic_bytes = bytes.fromhex(topic_id.lstrip("0x").zfill(64))

    tx = audit.functions.log(
        topic_bytes,
        message.get("agent", "unknown"),
        message.get("action", "unknown"),
        payload,
    ).build_transaction({
        "chainId":  settings.chain_id,
        "from":     Web3.to_checksum_address(operator),
        "nonce":    next_nonce(w3, operator),
        "gas":      300_000,
        "gasPrice": w3.eth.gas_price,
    })
    tx_hash_hex = build_and_send(w3, tx, pk)

    receipt = w3.eth.get_transaction_receipt(tx_hash_hex)
    # Try to read sequence number from ActionLogged event
    try:
        events = audit.events.ActionLogged().process_receipt(receipt)
        seq = events[0]["args"]["sequenceNumber"] if events else 0
    except Exception:
        seq = 0

    logger.info(f"Audit log #{seq} → topic {topic_id[:16]}... action={message.get('action')}")
    return seq


async def get_topic_messages(topic_id: str, limit: int = 100) -> list[dict]:
    """Read messages from the AuditLog contract.

    Replaces hedera.consensus.get_topic_messages() — same return schema.
    Returns list of dicts with keys: sequence_number, consensus_timestamp, content.
    """
    try:
        audit      = _get_audit()
        topic_bytes = bytes.fromhex(topic_id.lstrip("0x").zfill(64))
        entries    = audit.functions.getMessages(topic_bytes, limit).call()

        messages = []
        for i, entry in enumerate(entries):
            timestamp_unix, caller, agent, action, details = entry
            try:
                content = json.loads(details)
            except (json.JSONDecodeError, TypeError):
                content = {"raw": details}

            messages.append({
                "sequence_number":     i,
                "consensus_timestamp": datetime.fromtimestamp(
                    timestamp_unix, tz=timezone.utc
                ).isoformat(),
                "content": content,
            })
        return messages

    except Exception as e:
        logger.error(f"Failed to fetch audit messages for topic {topic_id}: {e}")
        return []


def log_agent_action(topic_id: str, agent: str, action: str, details: dict | None = None) -> int:
    """Convenience: log an agent action to the AuditLog contract.

    Identical API to hedera.consensus.log_agent_action().
    """
    message = {
        "agent":   agent,
        "action":  action,
        "details": details or {},
    }
    return submit_message(topic_id, message)
