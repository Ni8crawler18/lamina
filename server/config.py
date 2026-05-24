from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ─── Arbitrum / Robinhood Chain ──────────────────────────────────────────
    operator_address:    str = ""
    operator_private_key: str = ""
    arbitrum_rpc_url:    str = "https://rpc.testnet.chain.robinhood.com"
    chain_id:            int = 46630   # Robinhood Chain testnet

    # Deployed contract addresses (set after running contracts/scripts/deploy.py)
    factory_address:     str = ""
    audit_log_address:   str = ""
    usdc_address:        str = ""   # USDC on Robinhood Chain (testnet mock or real)

    # Block explorer base URL (for HashScan-equivalent links)
    explorer_url:        str = "https://explorer.testnet.chain.robinhood.com"

    # ─── Anthropic ───────────────────────────────────────────────────────────
    anthropic_api_key:   str = ""

    # ─── Server ──────────────────────────────────────────────────────────────
    backend_host:        str = "0.0.0.0"
    backend_port:        int = 8000
    frontend_url:        str = "http://localhost:3000"

    # ─── Database ────────────────────────────────────────────────────────────
    database_url:        str = "sqlite+aiosqlite:///lamina.db"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
