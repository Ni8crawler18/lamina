"""Chain layer tests: config loading + adapter conformance.

These are offline (no network): they prove the registry loads every TOML and that
each concrete adapter implements the full ChainAdapter interface.
"""

from app.chains.base import ChainAdapter
from app.chains.evm.adapter import EvmAdapter
from app.chains.hedera.adapter import HederaAdapter
from app.chains.registry import ChainRegistry


def _registry() -> ChainRegistry:
    reg = ChainRegistry()
    reg.load()
    return reg


def test_registry_loads_chains():
    reg = _registry()
    slugs = {c.slug for c in reg.list_all()}
    assert {"robinhood-testnet", "arc-testnet", "hedera-testnet"} <= slugs
    # robinhood is the live, enabled chain
    assert any(c.slug == "robinhood-testnet" and c.enabled for c in reg.list_enabled())


def test_chain_families_known():
    reg = _registry()
    assert {c.family for c in reg.list_all()} <= {"evm", "hedera", "solana"}


def test_evm_adapter_conforms():
    reg = _registry()
    adapter = EvmAdapter(reg.get_config("robinhood-testnet"))
    assert isinstance(adapter, ChainAdapter)


def test_hedera_adapter_conforms():
    reg = _registry()
    adapter = HederaAdapter(reg.get_config("hedera-testnet"))
    assert isinstance(adapter, ChainAdapter)


def test_disabled_chain_not_resolvable():
    reg = _registry()
    # arc-testnet is configured but not enabled → adapter() must refuse
    try:
        reg.adapter("arc-testnet")
        assert False, "expected ValueError for disabled chain"
    except ValueError:
        pass
