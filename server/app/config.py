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

    # -- AI -------------------------------------------------------------------
    anthropic_api_key: str = ""

    # -- server ---------------------------------------------------------------
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    frontend_url: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
