"""Application settings — SECRETS and environment only.

Chain RPCs, explorer URLs and contract addresses do NOT live here; they are in
config/chains/*.toml loaded by the ChainRegistry. This keeps .env small and free
of public, structural config even as we add many chains.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    # -- environment ----------------------------------------------------------
    environment: str = "development"
    log_level: str = "INFO"

    # -- database -------------------------------------------------------------
    # Async SQLAlchemy URL, e.g. postgresql+asyncpg://lamina:lamina@localhost:5433/lamina
    database_url: str = "postgresql+asyncpg://lamina:lamina@localhost:5433/lamina"

    # -- chains (secrets only) ------------------------------------------------
    # One deployer/operator EOA is reused across all EVM testnets (same key works
    # on every EVM chain). Per-chain private RPC endpoints are set via the
    # rpc_url_env vars referenced in each chain's TOML.
    deployer_private_key: str = ""
    operator_address: str = ""

    # Hedera (non-EVM family) — native HTS/HCS operator credentials.
    hedera_operator_id: str = ""
    hedera_operator_key: str = ""
    hedera_network: str = "testnet"

    # Solana (non-EVM family) — operator keypair for Token-2022 RWA tokens.
    # Provide ONE of these (path takes precedence): a solana-keygen json file, or
    # a base58-encoded 64-byte secret key.
    solana_keypair_path: str = ""
    solana_operator_key: str = ""

    # Sui (non-EVM family) — operator key for the closed-loop RWA Move package.
    # A Sui ed25519/secp256k1 private key in bech32 (suiprivkey1…) or flagged base64.
    sui_operator_key: str = ""

    # -- AI -------------------------------------------------------------------
    anthropic_api_key: str = ""

    # -- MCP server (off by default; handles critical ops, so guard carefully) -
    mcp_enabled: bool = False           # mount /mcp only when explicitly on
    mcp_allow_writes: bool = False      # value-moving tools require this AND admin scope
    mcp_read_token: str = ""            # bearer token → read scope
    mcp_admin_token: str = ""           # bearer token → admin scope (distinct from read)
    mcp_allowed_ips: str = ""           # optional CSV client-IP allowlist
    mcp_rate_limit_per_min: int = 60    # per-token sliding-window cap

    # -- Messaging channels (off by default; same care — they move value) ------
    channels_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_allowed_chat_ids: str = ""  # CSV of allowed Telegram chat IDs

    # -- server ---------------------------------------------------------------
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    frontend_url: str = "http://localhost:3000"  # comma-separated list of allowed CORS origins

    @property
    def frontend_origins(self) -> list[str]:
        """Allowed CORS origins, parsed from the comma-separated frontend_url."""
        return [o.strip() for o in self.frontend_url.split(",") if o.strip()]

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
