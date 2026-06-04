"""ChainRegistry — loads chain configs at startup and hands out adapters.

Mirrors meru's OrgRegistry pattern: read structural config from files into an
in-memory registry once, then resolve on demand. Services call
`registry.adapter(slug)` and get a ready ChainAdapter; they never know which
family (EVM/Solana) backs it.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.chains.base import ChainAdapter, ChainConfig

logger = logging.getLogger(__name__)

# backend/config/chains/
_CHAINS_DIR = Path(__file__).resolve().parents[2] / "config" / "chains"


def _build_adapter(config: ChainConfig) -> ChainAdapter:
    """Resolve a concrete adapter for a chain family. Lazy-imports per family."""
    if config.family == "evm":
        from app.chains.evm.adapter import EvmAdapter
        return EvmAdapter(config)
    if config.family == "hedera":
        from app.chains.hedera.adapter import HederaAdapter
        return HederaAdapter(config)
    if config.family == "solana":
        from app.chains.solana.adapter import SolanaAdapter
        return SolanaAdapter(config)
    raise ValueError(f"Unknown chain family '{config.family}' for chain '{config.slug}'")


class ChainRegistry:
    _instance: "ChainRegistry | None" = None

    def __init__(self) -> None:
        self._configs: dict[str, ChainConfig] = {}
        self._adapters: dict[str, ChainAdapter] = {}

    @classmethod
    def get_instance(cls) -> "ChainRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load(self, chains_dir: Path | None = None) -> None:
        """Load every *.toml from config/chains/. Call once at startup."""
        chains_dir = chains_dir or _CHAINS_DIR
        self._configs.clear()
        self._adapters.clear()
        for path in sorted(chains_dir.glob("*.toml")):
            cfg = ChainConfig.from_toml(path)
            self._configs[cfg.slug] = cfg
        enabled = [c.slug for c in self._configs.values() if c.enabled]
        logger.info(
            "ChainRegistry loaded %d chains (%d enabled: %s)",
            len(self._configs), len(enabled), ", ".join(enabled) or "none",
        )

    # -- config access ---------------------------------------------------------
    def get_config(self, slug: str) -> ChainConfig:
        if slug not in self._configs:
            raise KeyError(f"Unknown chain '{slug}'")
        return self._configs[slug]

    def list_enabled(self) -> list[ChainConfig]:
        return [c for c in self._configs.values() if c.enabled]

    def list_all(self) -> list[ChainConfig]:
        return list(self._configs.values())

    # -- adapter access --------------------------------------------------------
    def adapter(self, slug: str) -> ChainAdapter:
        """Return a cached adapter for an enabled chain."""
        cfg = self.get_config(slug)
        if not cfg.enabled:
            raise ValueError(f"Chain '{slug}' is not enabled")
        if slug not in self._adapters:
            self._adapters[slug] = _build_adapter(cfg)
        return self._adapters[slug]


def get_registry() -> ChainRegistry:
    return ChainRegistry.get_instance()
