"""Hedera chain adapter (non-EVM family).

Ports the original, working server/hedera/{client,token,consensus}.py onto the
family-agnostic ``ChainAdapter`` interface. Hedera identifies things by 0.0.x IDs
(token_ref / holder_ref / topic_ref), uses native HTS for tokens + HCS for the
audit log, and the Mirror Node REST API for reads.

The hiero_sdk_python import is lazy so this module loads even where the SDK isn't
installed; the adapter is only built when the Hedera chain is enabled.
"""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from base64 import b64decode
from datetime import datetime, timezone

from app.chains.base import AuditEntry, ChainAdapter, ChainConfig, TokenDeployment
from app.config import get_settings

logger = logging.getLogger(__name__)


class HederaAdapter(ChainAdapter):
    def __init__(self, config: ChainConfig):
        super().__init__(config)
        self._settings = get_settings()
        self._client = None  # lazy

    # ── client ───────────────────────────────────────────────────────────────
    def _c(self):
        if self._client is None:
            from hiero_sdk_python import AccountId, Client, PrivateKey
            s = self._settings
            net = (s.hedera_network or "testnet").lower()
            client = (
                Client.for_mainnet() if net == "mainnet"
                else Client.for_previewnet() if net == "previewnet"
                else Client.for_testnet()
            )
            key_str = s.hedera_operator_key.removeprefix("0x")
            client.set_operator(
                AccountId.from_string(s.hedera_operator_id),
                PrivateKey.from_bytes_ecdsa(bytes.fromhex(key_str)),
            )
            self._client = client
        return self._client

    def _operator_key(self):
        return self._c().operator_private_key

    @staticmethod
    def _tx_id(receipt) -> str:
        return str(receipt.transaction_id) if getattr(receipt, "transaction_id", None) else "success"

    # ── identity / explorer ──────────────────────────────────────────────────
    def operator_ref(self) -> str:
        return self._settings.hedera_operator_id

    def explorer_tx(self, tx_ref: str) -> str:
        return f"{self.config.explorer_url}/transaction/{tx_ref}"

    def explorer_address(self, ref: str) -> str:
        return f"{self.config.explorer_url}/account/{ref}"

    # ── token lifecycle ──────────────────────────────────────────────────────
    def deploy_asset_token(
        self, name: str, symbol: str, decimals: int, initial_supply: int,
        asset_type: str, jurisdiction: str,
    ) -> TokenDeployment:
        from hiero_sdk_python import (
            SupplyType, TokenCreateTransaction, TokenType,
            TopicCreateTransaction,
        )
        client = self._c()
        key = self._operator_key()

        tx = TokenCreateTransaction()
        tx.set_token_name(name)
        tx.set_token_symbol(symbol)
        tx.set_decimals(decimals)
        tx.set_initial_supply(initial_supply)
        tx.set_treasury_account_id(client.operator_account_id)
        tx.set_token_type(TokenType.FUNGIBLE_COMMON)
        tx.set_supply_key(key)
        tx.set_admin_key(key)
        tx.set_freeze_key(key)
        tx.set_wipe_key(key)
        tx.set_kyc_key(key)
        tx.set_supply_type(SupplyType.INFINITE)
        token_ref = str(tx.execute(client).token_id)

        # HCS audit topic (separate tx on Hedera — no atomic factory)
        topic_tx = TopicCreateTransaction()
        topic_tx.set_memo(f"Lamina audit: {name} ({symbol})")
        topic_tx.set_admin_key(key)
        topic_tx.set_submit_key(key)
        topic_ref = str(topic_tx.execute(client).topic_id)

        logger.info("[hedera] deployed %s token=%s topic=%s", symbol, token_ref, topic_ref)
        return TokenDeployment(token_ref=token_ref, audit_topic_ref=topic_ref)

    def mint(self, token_ref: str, amount: int) -> str:
        from hiero_sdk_python import TokenId, TokenMintTransaction
        tx = TokenMintTransaction()
        tx.set_token_id(TokenId.from_string(token_ref))
        tx.set_amount(amount)
        tx.freeze_with(self._c())
        tx.sign(self._operator_key())
        return self._tx_id(tx.execute(self._c()))

    def burn(self, token_ref: str, amount: int) -> str:
        from hiero_sdk_python import TokenBurnTransaction, TokenId
        tx = TokenBurnTransaction()
        tx.set_token_id(TokenId.from_string(token_ref))
        tx.set_amount(amount)
        tx.freeze_with(self._c())
        tx.sign(self._operator_key())
        return self._tx_id(tx.execute(self._c()))

    def transfer_token(self, token_ref: str, to_ref: str, amount: int) -> str:
        from hiero_sdk_python import AccountId, TokenId, TransferTransaction
        client = self._c()
        tx = TransferTransaction()
        tx.add_token_transfer(TokenId.from_string(token_ref), client.operator_account_id, -amount)
        tx.add_token_transfer(TokenId.from_string(token_ref), AccountId.from_string(to_ref), amount)
        return self._tx_id(tx.execute(client))

    def force_redeem(self, token_ref: str, holder_ref: str, amount: int) -> str:
        from hiero_sdk_python import AccountId, TokenId, TokenWipeTransaction
        tx = TokenWipeTransaction()
        tx.set_token_id(TokenId.from_string(token_ref))
        tx.set_account_id(AccountId.from_string(holder_ref))
        tx.set_amount(amount)
        tx.freeze_with(self._c())
        tx.sign(self._operator_key())
        return self._tx_id(tx.execute(self._c()))

    def token_balance(self, token_ref: str, holder_ref: str) -> int:
        # Mirror Node: GET /accounts/{id}/tokens?token.id=...
        base = self.config.rpc_url.rstrip("/")
        q = urllib.parse.urlencode({"token.id": token_ref})
        data = self._http_get(f"{base}/api/v1/accounts/{holder_ref}/tokens?{q}")
        for t in data.get("tokens", []):
            if t.get("token_id") == token_ref:
                return int(t.get("balance", 0))
        return 0

    # ── compliance ───────────────────────────────────────────────────────────
    def grant_kyc(self, token_ref: str, holder_ref: str) -> str:
        from hiero_sdk_python import AccountId, TokenGrantKycTransaction, TokenId
        tx = TokenGrantKycTransaction()
        tx.set_token_id(TokenId.from_string(token_ref))
        tx.set_account_id(AccountId.from_string(holder_ref))
        tx.freeze_with(self._c())
        tx.sign(self._operator_key())
        return self._tx_id(tx.execute(self._c()))

    def revoke_kyc(self, token_ref: str, holder_ref: str) -> str:
        from hiero_sdk_python import AccountId, TokenId, TokenRevokeKycTransaction
        tx = TokenRevokeKycTransaction()
        tx.set_token_id(TokenId.from_string(token_ref))
        tx.set_account_id(AccountId.from_string(holder_ref))
        tx.freeze_with(self._c())
        tx.sign(self._operator_key())
        return self._tx_id(tx.execute(self._c()))

    def freeze(self, token_ref: str, holder_ref: str) -> str:
        from hiero_sdk_python import AccountId, TokenFreezeTransaction, TokenId
        tx = TokenFreezeTransaction()
        tx.set_token_id(TokenId.from_string(token_ref))
        tx.set_account_id(AccountId.from_string(holder_ref))
        tx.freeze_with(self._c())
        tx.sign(self._operator_key())
        return self._tx_id(tx.execute(self._c()))

    def unfreeze(self, token_ref: str, holder_ref: str) -> str:
        from hiero_sdk_python import AccountId, TokenId, TokenUnfreezeTransaction
        tx = TokenUnfreezeTransaction()
        tx.set_token_id(TokenId.from_string(token_ref))
        tx.set_account_id(AccountId.from_string(holder_ref))
        tx.freeze_with(self._c())
        tx.sign(self._operator_key())
        return self._tx_id(tx.execute(self._c()))

    # ── payouts ──────────────────────────────────────────────────────────────
    def pay_stable(self, to_ref: str, amount_units: int) -> str:
        """USDC on Hedera is an HTS token; recipient must be associated with it."""
        from hiero_sdk_python import AccountId, TokenId, TransferTransaction
        client = self._c()
        usdc = TokenId.from_string(self.config.contract("usdc"))
        tx = TransferTransaction()
        tx.add_token_transfer(usdc, client.operator_account_id, -amount_units)
        tx.add_token_transfer(usdc, AccountId.from_string(to_ref), amount_units)
        return self._tx_id(tx.execute(client))

    def pay_native(self, to_ref: str, amount_wei: int) -> str:
        """Native HBAR transfer. amount in tinybars (Hedera's smallest unit)."""
        from hiero_sdk_python import AccountId, Hbar, TransferTransaction
        client = self._c()
        tx = TransferTransaction()
        tx.add_hbar_transfer(client.operator_account_id, Hbar.from_tinybars(-amount_wei))
        tx.add_hbar_transfer(AccountId.from_string(to_ref), Hbar.from_tinybars(amount_wei))
        return self._tx_id(tx.execute(client))

    def stable_balance(self, holder_ref: str) -> int:
        return self.token_balance(self.config.contract("usdc"), holder_ref)

    # ── audit ────────────────────────────────────────────────────────────────
    def open_audit_topic(self, memo: str) -> str:
        from hiero_sdk_python import TopicCreateTransaction
        key = self._operator_key()
        tx = TopicCreateTransaction()
        tx.set_memo(memo)
        tx.set_admin_key(key)
        tx.set_submit_key(key)
        return str(tx.execute(self._c()).topic_id)

    def write_audit(self, topic_ref: str, agent: str, action: str, details: dict) -> int:
        from hiero_sdk_python import TopicId, TopicMessageSubmitTransaction
        payload = json.dumps({
            "agent": agent, "action": action, "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        tx = TopicMessageSubmitTransaction()
        tx.set_topic_id(TopicId.from_string(topic_ref))
        tx.set_message(payload)
        tx.freeze_with(self._c())
        tx.sign(self._operator_key())
        receipt = tx.execute(self._c())
        return int(receipt.topic_sequence_number or 0)

    def read_audit(self, topic_ref: str, limit: int = 100) -> list[AuditEntry]:
        base = self.config.rpc_url.rstrip("/")
        q = urllib.parse.urlencode({"limit": limit, "order": "asc"})
        data = self._http_get(f"{base}/api/v1/topics/{topic_ref}/messages?{q}")
        out: list[AuditEntry] = []
        for msg in data.get("messages", []):
            try:
                content = json.loads(b64decode(msg["message"]).decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError, KeyError):
                content = {"raw": msg.get("message", "")}
            out.append(AuditEntry(
                sequence=msg.get("sequence_number", 0),
                timestamp=str(msg.get("consensus_timestamp", "")),
                agent=content.get("agent", ""),
                action=content.get("action", ""),
                details=content.get("details", content),
            ))
        return out

    # ── helpers ──────────────────────────────────────────────────────────────
    @staticmethod
    def _http_get(url: str) -> dict:
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.error("[hedera] mirror node GET failed (%s): %s", url, e)
            return {}
