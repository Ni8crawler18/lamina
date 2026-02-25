from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Hedera
    hedera_account_id: str = ""
    hedera_private_key: str = ""
    hedera_network: str = "testnet"

    # Anthropic
    anthropic_api_key: str = ""

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    frontend_url: str = "http://localhost:3000"

    # Database
    database_url: str = "sqlite+aiosqlite:///lamina.db"

    # Hedera Mirror Node
    @property
    def mirror_node_url(self) -> str:
        if self.hedera_network == "mainnet":
            return "https://mainnet.mirrornode.hedera.com"
        return "https://testnet.mirrornode.hedera.com"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
