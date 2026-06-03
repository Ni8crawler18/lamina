"""Chain abstraction layer.

`ChainAdapter` is the single interface every settlement chain implements. It is
deliberately *family-agnostic*: it speaks in opaque string references (token_ref,
holder_ref, tx_ref) rather than EVM addresses or Solana pubkeys, so an EVM adapter
and a future Solana adapter satisfy the same contract. Services depend only on
this interface — never on web3 / solders / a specific chain module.

The concrete EVM adapter lives in `app/chains/evm/`. Solana is phase 2.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import os
import tomllib
from pathlib import Path


# ─── Config ──────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ChainConfig:
    """One settlement chain, loaded from config/chains/<slug>.toml."""

    name: str
    slug: str
    family: str                 # "evm" | "solana"
    chain_id: int
    enabled: bool
    native_symbol: str
    rpc_url: str
    explorer_url: str
    contracts: dict[str, str] = field(default_factory=dict)  # factory, audit_log, usdc, ...

    @classmethod
    def from_toml(cls, path: Path) -> "ChainConfig":
        data = tomllib.loads(path.read_text())
        # An rpc_url_env entry lets a private/paid endpoint override the public default.
        rpc_url = data["rpc_url"]
        env_key = data.get("rpc_url_env")
        if env_key and os.environ.get(env_key):
            rpc_url = os.environ[env_key]
        return cls(
            name=data["name"],
            slug=data["slug"],
            family=data["family"],
            chain_id=int(data["chain_id"]),
            enabled=bool(data.get("enabled", False)),
            native_symbol=data.get("native_symbol", "ETH"),
            rpc_url=rpc_url,
            explorer_url=data["explorer_url"],
            contracts=dict(data.get("contracts", {})),
        )

    def contract(self, key: str) -> str:
        addr = self.contracts.get(key, "")
        if not addr:
            raise ValueError(f"Chain '{self.slug}' has no '{key}' contract configured")
        return addr


# ─── Value objects returned by adapters (chain-neutral) ──────────────────────

@dataclass(frozen=True)
class TokenDeployment:
    token_ref: str          # deployed asset-token reference (EVM address / Solana mint)
    audit_topic_ref: str    # audit topic/log reference for this asset


@dataclass(frozen=True)
class AuditEntry:
    sequence: int
    timestamp: str          # ISO-8601 UTC
    agent: str
    action: str
    details: dict


# ─── Adapter interface ───────────────────────────────────────────────────────

class ChainAdapter(ABC):
    """Settlement primitives the RWA services rely on. One impl per chain family."""

    def __init__(self, config: ChainConfig):
        self.config = config

    # -- identity / explorer ---------------------------------------------------
    @abstractmethod
    def operator_ref(self) -> str: ...

    @abstractmethod
    def explorer_tx(self, tx_ref: str) -> str: ...

    @abstractmethod
    def explorer_address(self, ref: str) -> str: ...

    # -- token lifecycle -------------------------------------------------------
    @abstractmethod
    def deploy_asset_token(
        self, name: str, symbol: str, decimals: int, initial_supply: int,
        asset_type: str, jurisdiction: str,
    ) -> TokenDeployment: ...

    @abstractmethod
    def mint(self, token_ref: str, amount: int) -> str: ...

    @abstractmethod
    def burn(self, token_ref: str, amount: int) -> str: ...

    @abstractmethod
    def transfer_token(self, token_ref: str, to_ref: str, amount: int) -> str: ...

    @abstractmethod
    def force_redeem(self, token_ref: str, holder_ref: str, amount: int) -> str:
        """Wipe/claw back tokens from a holder at maturity (issuer authority)."""

    @abstractmethod
    def token_balance(self, token_ref: str, holder_ref: str) -> int: ...

    # -- compliance ------------------------------------------------------------
    @abstractmethod
    def grant_kyc(self, token_ref: str, holder_ref: str) -> str: ...

    @abstractmethod
    def revoke_kyc(self, token_ref: str, holder_ref: str) -> str: ...

    @abstractmethod
    def freeze(self, token_ref: str, holder_ref: str) -> str: ...

    @abstractmethod
    def unfreeze(self, token_ref: str, holder_ref: str) -> str: ...

    # -- payouts ---------------------------------------------------------------
    @abstractmethod
    def pay_stable(self, to_ref: str, amount_units: int) -> str:
        """Pay USDC (6-dec micro-units) from the treasury — coupons, principal."""

    @abstractmethod
    def pay_native(self, to_ref: str, amount_wei: int) -> str:
        """Pay the native gas token (ETH/AVAX/POL) from the treasury."""

    @abstractmethod
    def stable_balance(self, holder_ref: str) -> int: ...

    # -- audit -----------------------------------------------------------------
    @abstractmethod
    def open_audit_topic(self, memo: str) -> str: ...

    @abstractmethod
    def write_audit(self, topic_ref: str, agent: str, action: str, details: dict) -> int: ...

    @abstractmethod
    def read_audit(self, topic_ref: str, limit: int = 100) -> list[AuditEntry]: ...
