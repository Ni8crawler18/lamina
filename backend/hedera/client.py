"""Hedera client initialization and singleton access."""

from hiero_sdk_python import Client, AccountId, PrivateKey
from backend.config import get_settings

_client: Client | None = None


def get_hedera_client() -> Client:
    """Get or create the singleton Hedera client."""
    global _client
    if _client is not None:
        return _client

    settings = get_settings()

    if settings.hedera_network == "mainnet":
        client = Client.for_mainnet()
    elif settings.hedera_network == "previewnet":
        client = Client.for_previewnet()
    else:
        client = Client.for_testnet()

    account_id = AccountId.from_string(settings.hedera_account_id)
    # Strip 0x prefix for hex key and use ECDSA (Hedera default for portal accounts)
    key_str = settings.hedera_private_key
    if key_str.startswith("0x"):
        key_str = key_str[2:]
    private_key = PrivateKey.from_bytes_ecdsa(bytes.fromhex(key_str))
    client.set_operator(account_id, private_key)

    _client = client
    return _client


def get_operator_account_id() -> AccountId:
    client = get_hedera_client()
    return client.operator_account_id


def get_operator_private_key() -> PrivateKey:
    client = get_hedera_client()
    return client.operator_private_key
