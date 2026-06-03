"""EVM chain adapter.

One implementation that serves every EVM chain — Robinhood, Arc, Ethereum Sepolia,
etc. All chain-specific values (RPC, chain_id, factory/audit_log/usdc addresses)
come from the injected ``ChainConfig``; nothing is hardcoded. Each adapter instance
owns its own web3 client, so multiple chains run side by side.

Ported from the original server/arbitrum/{client,token,audit}.py, with the gas
fix (estimate + buffer) and full ABIs from app/chains/evm/abi/.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from eth_account import Account
from web3 import Web3

from app.chains.base import AuditEntry, ChainAdapter, ChainConfig, TokenDeployment
from app.config import get_settings

logger = logging.getLogger(__name__)

_ABI_DIR = Path(__file__).parent / "abi"


def _load_abi(name: str) -> list:
    return json.loads((_ABI_DIR / f"{name}.json").read_text())


_MINIMAL_ERC20_ABI = [
    {
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]


class EvmAdapter(ChainAdapter):
    def __init__(self, config: ChainConfig):
        super().__init__(config)
        settings = get_settings()
        self._w3 = Web3(Web3.HTTPProvider(config.rpc_url))
        self._operator = Web3.to_checksum_address(settings.operator_address)
        self._pk = settings.deployer_private_key
        self._token_abi = _load_abi("LaminaRWAToken")
        self._factory_abi = _load_abi("LaminaFactory")
        self._audit_abi = _load_abi("AuditLog")
        self._factory = None
        self._audit = None

    # ── internals ────────────────────────────────────────────────────────────
    def _factory_contract(self):
        if self._factory is None:
            self._factory = self._w3.eth.contract(
                address=Web3.to_checksum_address(self.config.contract("factory")),
                abi=self._factory_abi,
            )
        return self._factory

    def _audit_contract(self):
        if self._audit is None:
            self._audit = self._w3.eth.contract(
                address=Web3.to_checksum_address(self.config.contract("audit_log")),
                abi=self._audit_abi,
            )
        return self._audit

    def _token_contract(self, token_ref: str):
        return self._w3.eth.contract(
            address=Web3.to_checksum_address(token_ref), abi=self._token_abi
        )

    def _gas_price(self) -> int:
        """Network gas price with a 1.5x buffer so txs don't stall when fees rise
        (busy testnets like Sepolia move between submit and mine)."""
        return int(self._w3.eth.gas_price * 1.5)

    def _send(self, fn, *, gas_fallback: int = 300_000) -> str:
        """Build, gas-estimate (+30%), sign, send, and wait for a contract call."""
        w3 = self._w3
        tx = fn.build_transaction({
            "chainId": self.config.chain_id,
            "from": self._operator,
            "nonce": w3.eth.get_transaction_count(self._operator, "pending"),
            "gasPrice": self._gas_price(),
        })
        try:
            tx["gas"] = int(w3.eth.estimate_gas({k: v for k, v in tx.items() if k != "gas"}) * 1.3)
        except Exception as e:
            logger.warning("gas estimation failed (%s); using fallback %d", e, gas_fallback)
            tx["gas"] = gas_fallback
        signed = w3.eth.account.sign_transaction(tx, self._pk)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
        if receipt.status != 1:
            raise RuntimeError(f"[{self.config.slug}] tx reverted: {tx_hash.hex()}")
        return tx_hash.hex()

    @staticmethod
    def _topic_bytes(topic_ref: str) -> bytes:
        return bytes.fromhex(topic_ref.removeprefix("0x").zfill(64))

    # ── identity / explorer ──────────────────────────────────────────────────
    def operator_ref(self) -> str:
        return self._operator

    def explorer_tx(self, tx_ref: str) -> str:
        h = tx_ref if tx_ref.startswith("0x") else f"0x{tx_ref}"
        return f"{self.config.explorer_url}/tx/{h}"

    def explorer_address(self, ref: str) -> str:
        return f"{self.config.explorer_url}/address/{ref}"

    # ── token lifecycle ──────────────────────────────────────────────────────
    def deploy_asset_token(
        self, name: str, symbol: str, decimals: int, initial_supply: int,
        asset_type: str, jurisdiction: str,
    ) -> TokenDeployment:
        factory = self._factory_contract()
        tx_hash = self._send(
            factory.functions.deployAsset(
                name, symbol, initial_supply, decimals, asset_type, jurisdiction
            ),
            gas_fallback=4_000_000,
        )
        receipt = self._w3.eth.get_transaction_receipt(tx_hash)
        events = factory.events.AssetDeployed().process_receipt(receipt)
        if not events:
            raise RuntimeError(f"AssetDeployed event missing in {tx_hash}")
        args = events[0]["args"]
        token_ref = args["tokenAddress"]
        topic_ref = args["topicId"].hex()
        logger.info("[%s] deployed %s → %s topic=%s", self.config.slug, symbol, token_ref, topic_ref)
        return TokenDeployment(token_ref=token_ref, audit_topic_ref=topic_ref)

    def mint(self, token_ref: str, amount: int) -> str:
        return self._send(self._token_contract(token_ref).functions.mint(self._operator, amount))

    def burn(self, token_ref: str, amount: int) -> str:
        return self._send(self._token_contract(token_ref).functions.burn(amount))

    def transfer_token(self, token_ref: str, to_ref: str, amount: int) -> str:
        return self._send(
            self._token_contract(token_ref).functions.transfer(
                Web3.to_checksum_address(to_ref), amount
            )
        )

    def force_redeem(self, token_ref: str, holder_ref: str, amount: int) -> str:
        return self._send(
            self._token_contract(token_ref).functions.forceBurn(
                Web3.to_checksum_address(holder_ref), amount, "maturity_settlement"
            )
        )

    def token_balance(self, token_ref: str, holder_ref: str) -> int:
        return self._token_contract(token_ref).functions.balanceOf(
            Web3.to_checksum_address(holder_ref)
        ).call()

    # ── compliance ───────────────────────────────────────────────────────────
    def grant_kyc(self, token_ref: str, holder_ref: str) -> str:
        return self._send(
            self._token_contract(token_ref).functions.grantKYC(Web3.to_checksum_address(holder_ref))
        )

    def revoke_kyc(self, token_ref: str, holder_ref: str) -> str:
        return self._send(
            self._token_contract(token_ref).functions.revokeKYC(Web3.to_checksum_address(holder_ref))
        )

    def freeze(self, token_ref: str, holder_ref: str) -> str:
        return self._send(
            self._token_contract(token_ref).functions.freeze(Web3.to_checksum_address(holder_ref))
        )

    def unfreeze(self, token_ref: str, holder_ref: str) -> str:
        return self._send(
            self._token_contract(token_ref).functions.unfreeze(Web3.to_checksum_address(holder_ref))
        )

    # ── payouts ──────────────────────────────────────────────────────────────
    def pay_stable(self, to_ref: str, amount_units: int) -> str:
        usdc = self._w3.eth.contract(
            address=Web3.to_checksum_address(self.config.contract("usdc")),
            abi=_MINIMAL_ERC20_ABI,
        )
        return self._send(usdc.functions.transfer(Web3.to_checksum_address(to_ref), amount_units))

    def pay_native(self, to_ref: str, amount_wei: int) -> str:
        w3 = self._w3
        tx = {
            "chainId": self.config.chain_id,
            "from": self._operator,
            "to": Web3.to_checksum_address(to_ref),
            "value": amount_wei,
            "nonce": w3.eth.get_transaction_count(self._operator, "pending"),
            "gasPrice": self._gas_price(),
            "gas": 21_000,
        }
        signed = w3.eth.account.sign_transaction(tx, self._pk)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
        if receipt.status != 1:
            raise RuntimeError(f"[{self.config.slug}] native transfer reverted: {tx_hash.hex()}")
        return tx_hash.hex()

    def stable_balance(self, holder_ref: str) -> int:
        usdc = self._w3.eth.contract(
            address=Web3.to_checksum_address(self.config.contract("usdc")),
            abi=_MINIMAL_ERC20_ABI,
        )
        return usdc.functions.balanceOf(Web3.to_checksum_address(holder_ref)).call()

    # ── audit ────────────────────────────────────────────────────────────────
    def open_audit_topic(self, memo: str) -> str:
        audit = self._audit_contract()
        tx_hash = self._send(audit.functions.createTopic(memo))
        receipt = self._w3.eth.get_transaction_receipt(tx_hash)
        events = audit.events.TopicCreated().process_receipt(receipt)
        return events[0]["args"]["topicId"].hex() if events else tx_hash

    def write_audit(self, topic_ref: str, agent: str, action: str, details: dict) -> int:
        audit = self._audit_contract()
        payload = json.dumps({
            "agent": agent, "action": action, "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        tx_hash = self._send(audit.functions.log(self._topic_bytes(topic_ref), agent, action, payload))
        receipt = self._w3.eth.get_transaction_receipt(tx_hash)
        try:
            events = audit.events.ActionLogged().process_receipt(receipt)
            return int(events[0]["args"]["sequenceNumber"]) if events else 0
        except Exception:
            return 0

    def read_audit(self, topic_ref: str, limit: int = 100) -> list[AuditEntry]:
        audit = self._audit_contract()
        try:
            entries = audit.functions.getMessages(self._topic_bytes(topic_ref), limit).call()
        except Exception as e:
            logger.error("[%s] read_audit failed for %s: %s", self.config.slug, topic_ref, e)
            return []
        out: list[AuditEntry] = []
        for i, (ts_unix, _caller, agent, action, details) in enumerate(entries):
            try:
                content = json.loads(details)
            except (json.JSONDecodeError, TypeError):
                content = {"raw": details}
            out.append(AuditEntry(
                sequence=i,
                timestamp=datetime.fromtimestamp(ts_unix, tz=timezone.utc).isoformat(),
                agent=agent, action=action, details=content,
            ))
        return out

    # ── helpers for accounts (not part of the interface) ─────────────────────
    @staticmethod
    def new_wallet() -> tuple[str, str]:
        """Generate an EVM keypair. Returns (address, private_key_hex)."""
        acct = Account.create()
        return acct.address, acct.key.hex()
