"""Hedera Token Service (HTS) operations — all real on-chain."""

import logging
from hiero_sdk_python import (
    AccountCreateTransaction,
    TokenCreateTransaction,
    TokenMintTransaction,
    TokenBurnTransaction,
    TokenAssociateTransaction,
    TokenGrantKycTransaction,
    TokenRevokeKycTransaction,
    TokenFreezeTransaction,
    TokenUnfreezeTransaction,
    TokenWipeTransaction,
    TransferTransaction,
    TokenId,
    AccountId,
    PrivateKey,
    PublicKey,
    TokenType,
    SupplyType,
    Hbar,
)
from backend.hedera.client import get_hedera_client, get_operator_account_id, get_operator_private_key

logger = logging.getLogger(__name__)


# ─── Account Operations ──────────────────────────────────

def create_account(initial_balance_hbar: int = 10) -> tuple[str, str]:
    """Create a new Hedera account funded from operator. Returns (account_id, private_key_hex)."""
    client = get_hedera_client()

    new_key = PrivateKey.generate_ecdsa()
    public_key = new_key.public_key()

    tx = AccountCreateTransaction()
    tx.set_key(public_key)
    tx.set_initial_balance(Hbar(initial_balance_hbar))
    tx.set_max_automatic_token_associations(10)

    receipt = tx.execute(client)
    account_id = str(receipt.account_id)
    private_key_hex = new_key.to_bytes_raw().hex()

    logger.info(f"Created account {account_id} with {initial_balance_hbar} HBAR")
    return account_id, private_key_hex


# ─── Token Operations ────────────────────────────────────

def create_token(
    name: str,
    symbol: str,
    decimals: int = 2,
    initial_supply: int = 0,
    max_supply: int = 0,
) -> str:
    """Create a fungible token on HTS. Returns token_id string."""
    client = get_hedera_client()
    treasury = get_operator_account_id()
    supply_key = get_operator_private_key()

    tx = TokenCreateTransaction()
    tx.set_token_name(name)
    tx.set_token_symbol(symbol)
    tx.set_decimals(decimals)
    tx.set_initial_supply(initial_supply)
    tx.set_treasury_account_id(treasury)
    tx.set_token_type(TokenType.FUNGIBLE_COMMON)
    tx.set_supply_key(supply_key)
    tx.set_admin_key(supply_key)
    tx.set_freeze_key(supply_key)
    tx.set_wipe_key(supply_key)
    tx.set_kyc_key(supply_key)

    if max_supply > 0:
        tx.set_supply_type(SupplyType.FINITE)
        tx.set_max_supply(max_supply)
    else:
        tx.set_supply_type(SupplyType.INFINITE)

    receipt = tx.execute(client)
    token_id = str(receipt.token_id)
    logger.info(f"Created token {token_id}: {name} ({symbol})")
    return token_id


def mint_tokens(token_id: str, amount: int) -> str:
    """Mint additional fungible tokens. Returns transaction ID."""
    client = get_hedera_client()
    supply_key = get_operator_private_key()

    tx = TokenMintTransaction()
    tx.set_token_id(TokenId.from_string(token_id))
    tx.set_amount(amount)
    tx.freeze_with(client)
    tx.sign(supply_key)

    receipt = tx.execute(client)
    logger.info(f"Minted {amount} tokens for {token_id}")
    return str(receipt.transaction_id) if receipt.transaction_id else "success"


def burn_tokens(token_id: str, amount: int) -> str:
    """Burn fungible tokens. Returns transaction ID."""
    client = get_hedera_client()
    supply_key = get_operator_private_key()

    tx = TokenBurnTransaction()
    tx.set_token_id(TokenId.from_string(token_id))
    tx.set_amount(amount)
    tx.freeze_with(client)
    tx.sign(supply_key)

    receipt = tx.execute(client)
    logger.info(f"Burned {amount} tokens for {token_id}")
    return str(receipt.transaction_id) if receipt.transaction_id else "success"


# ─── Token Association & KYC ─────────────────────────────

def associate_token(account_id: str, token_id: str, account_private_key: str | None = None) -> str:
    """Associate a token with an account. Account must sign if not using auto-association."""
    client = get_hedera_client()

    tx = TokenAssociateTransaction()
    tx.set_account_id(AccountId.from_string(account_id))
    tx.set_token_ids([TokenId.from_string(token_id)])

    # If account is not the operator, need account's key to sign
    if account_private_key:
        tx.freeze_with(client)
        key = PrivateKey.from_bytes_ecdsa(bytes.fromhex(account_private_key))
        tx.sign(key)

    receipt = tx.execute(client)
    logger.info(f"Associated token {token_id} with account {account_id}")
    return str(receipt.transaction_id) if receipt.transaction_id else "success"


def grant_kyc(token_id: str, account_id: str) -> str:
    """Grant KYC status to an account for a token (real on-chain KYC)."""
    client = get_hedera_client()
    kyc_key = get_operator_private_key()

    tx = TokenGrantKycTransaction()
    tx.set_token_id(TokenId.from_string(token_id))
    tx.set_account_id(AccountId.from_string(account_id))
    tx.freeze_with(client)
    tx.sign(kyc_key)

    receipt = tx.execute(client)
    logger.info(f"Granted KYC for {account_id} on token {token_id}")
    return str(receipt.transaction_id) if receipt.transaction_id else "success"


def revoke_kyc(token_id: str, account_id: str) -> str:
    """Revoke KYC status from an account for a token."""
    client = get_hedera_client()
    kyc_key = get_operator_private_key()

    tx = TokenRevokeKycTransaction()
    tx.set_token_id(TokenId.from_string(token_id))
    tx.set_account_id(AccountId.from_string(account_id))
    tx.freeze_with(client)
    tx.sign(kyc_key)

    receipt = tx.execute(client)
    logger.info(f"Revoked KYC for {account_id} on token {token_id}")
    return str(receipt.transaction_id) if receipt.transaction_id else "success"


def freeze_account(token_id: str, account_id: str) -> str:
    """Freeze an account's token balance (compliance enforcement)."""
    client = get_hedera_client()
    freeze_key = get_operator_private_key()

    tx = TokenFreezeTransaction()
    tx.set_token_id(TokenId.from_string(token_id))
    tx.set_account_id(AccountId.from_string(account_id))
    tx.freeze_with(client)
    tx.sign(freeze_key)

    receipt = tx.execute(client)
    logger.info(f"Froze account {account_id} for token {token_id}")
    return str(receipt.transaction_id) if receipt.transaction_id else "success"


def unfreeze_account(token_id: str, account_id: str) -> str:
    """Unfreeze an account's token balance."""
    client = get_hedera_client()
    freeze_key = get_operator_private_key()

    tx = TokenUnfreezeTransaction()
    tx.set_token_id(TokenId.from_string(token_id))
    tx.set_account_id(AccountId.from_string(account_id))
    tx.freeze_with(client)
    tx.sign(freeze_key)

    receipt = tx.execute(client)
    logger.info(f"Unfroze account {account_id} for token {token_id}")
    return str(receipt.transaction_id) if receipt.transaction_id else "success"


# ─── Transfers ────────────────────────────────────────────

def transfer_tokens(
    token_id: str,
    from_id: str,
    to_id: str,
    amount: int,
    decimals: int = 2,
) -> str:
    """Transfer fungible tokens between accounts (real on-chain). Returns tx ID."""
    client = get_hedera_client()

    tx = TransferTransaction()
    tx.add_token_transfer_with_decimals(
        TokenId.from_string(token_id),
        AccountId.from_string(from_id),
        -amount,
        decimals,
    )
    tx.add_token_transfer_with_decimals(
        TokenId.from_string(token_id),
        AccountId.from_string(to_id),
        amount,
        decimals,
    )

    receipt = tx.execute(client)
    logger.info(f"Transferred {amount} of {token_id} from {from_id} to {to_id}")
    return str(receipt.transaction_id) if receipt.transaction_id else "success"


def wipe_tokens(token_id: str, account_id: str, amount: int) -> str:
    """Wipe tokens from an account using the wipe key (compliance/maturity enforcement)."""
    client = get_hedera_client()
    wipe_key = get_operator_private_key()

    tx = TokenWipeTransaction()
    tx.set_token_id(TokenId.from_string(token_id))
    tx.set_account_id(AccountId.from_string(account_id))
    tx.set_amount(amount)
    tx.freeze_with(client)
    tx.sign(wipe_key)

    receipt = tx.execute(client)
    logger.info(f"Wiped {amount} tokens from {account_id} for {token_id}")
    return str(receipt.transaction_id) if receipt.transaction_id else "success"


def transfer_hbar(to_id: str, amount_tinybars: int) -> str:
    """Transfer HBAR from operator to an account. Amount is in tinybars. Returns tx ID."""
    client = get_hedera_client()
    from_id = str(get_operator_account_id())

    tx = TransferTransaction()
    tx.add_hbar_transfer(AccountId.from_string(from_id), Hbar.from_tinybars(-amount_tinybars))
    tx.add_hbar_transfer(AccountId.from_string(to_id), Hbar.from_tinybars(amount_tinybars))

    receipt = tx.execute(client)
    logger.info(f"Transferred {amount_tinybars} tinybar from {from_id} to {to_id}")
    return str(receipt.transaction_id) if receipt.transaction_id else "success"
