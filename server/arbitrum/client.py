"""Arbitrum / Robinhood Chain web3 client.

Replaces server/hedera/client.py — same surface API used by token.py and audit.py.
"""

import logging
from functools import lru_cache

from web3 import Web3
from eth_account import Account

from server.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_web3() -> Web3:
    """Return a connected Web3 instance (cached)."""
    settings = get_settings()
    w3 = Web3(Web3.HTTPProvider(settings.arbitrum_rpc_url))
    if not w3.is_connected():
        raise RuntimeError(f"Cannot connect to Robinhood Chain RPC: {settings.arbitrum_rpc_url}")
    logger.info(f"Connected to Robinhood Chain — chain_id={w3.eth.chain_id}")
    return w3


def get_operator_address() -> str:
    """Return the operator EOA address (0x...)."""
    return get_settings().operator_address


def get_operator_private_key() -> str:
    """Return the operator private key (hex, with or without 0x prefix)."""
    return get_settings().operator_private_key


def build_and_send(w3: Web3, tx: dict, private_key: str) -> str:
    """Sign, send, and wait for a transaction. Returns tx_hash hex string."""
    signed = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    if receipt.status != 1:
        raise RuntimeError(f"Transaction reverted: {tx_hash.hex()}")
    logger.debug(f"tx confirmed: {tx_hash.hex()}")
    return tx_hash.hex()


def next_nonce(w3: Web3, address: str) -> int:
    return w3.eth.get_transaction_count(Web3.to_checksum_address(address))
