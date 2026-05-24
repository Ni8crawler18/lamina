"""
Deploy Lamina contracts to Robinhood Chain testnet.

Usage:
    cd contracts/
    pip install web3 py-solc-x python-dotenv
    python scripts/deploy.py

Requires .env with:
    OPERATOR_PRIVATE_KEY=0x...
    ARBITRUM_RPC_URL=https://rpc.testnet.chain.robinhood.com   (or Alchemy URL)
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from web3 import Web3
from solcx import compile_files, install_solc, get_installed_solc_versions

load_dotenv(Path(__file__).parent.parent.parent / "server" / ".env")

# ─── Config ──────────────────────────────────────────────────────────────────
RPC_URL     = os.getenv("ARBITRUM_RPC_URL", "https://rpc.testnet.chain.robinhood.com")
PRIVATE_KEY = os.getenv("OPERATOR_PRIVATE_KEY", "")
CHAIN_ID    = int(os.getenv("CHAIN_ID", "46630"))   # Robinhood Chain testnet

CONTRACTS_DIR = Path(__file__).parent.parent
SOLC_VERSION  = "0.8.20"

# ─── Setup ───────────────────────────────────────────────────────────────────
if not PRIVATE_KEY:
    sys.exit("ERROR: OPERATOR_PRIVATE_KEY not set in .env")

w3 = Web3(Web3.HTTPProvider(RPC_URL))
assert w3.is_connected(), f"Cannot connect to {RPC_URL}"

account = w3.eth.account.from_key(PRIVATE_KEY)
print(f"Deployer : {account.address}")
print(f"Chain ID : {CHAIN_ID}")
print(f"Balance  : {w3.from_wei(w3.eth.get_balance(account.address), 'ether'):.6f} ETH")

# ─── Compile ─────────────────────────────────────────────────────────────────
if SOLC_VERSION not in [str(v) for v in get_installed_solc_versions()]:
    print(f"Installing solc {SOLC_VERSION} ...")
    install_solc(SOLC_VERSION)

print("\nCompiling contracts ...")
compiled = compile_files(
    [
        str(CONTRACTS_DIR / "AuditLog.sol"),
        str(CONTRACTS_DIR / "LaminaRWAToken.sol"),
        str(CONTRACTS_DIR / "LaminaFactory.sol"),
    ],
    output_values=["abi", "bin"],
    solc_version=SOLC_VERSION,
    import_remappings=[
        "@openzeppelin=./node_modules/@openzeppelin",
    ],
    allow_paths=[str(CONTRACTS_DIR)],
)


def get_contract(name: str):
    for key, data in compiled.items():
        if key.endswith(f":{name}"):
            return data["abi"], data["bin"]
    raise KeyError(f"Contract {name} not found in compiled output")


def deploy(name: str, abi, bytecode, *args):
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    nonce = w3.eth.get_transaction_count(account.address)
    tx = contract.constructor(*args).build_transaction({
        "chainId": CHAIN_ID,
        "from":    account.address,
        "nonce":   nonce,
        "gas":     3_000_000,
        "gasPrice": w3.eth.gas_price,
    })
    signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    addr = receipt["contractAddress"]
    print(f"  ✅ {name} deployed → {addr}")
    print(f"     tx: {tx_hash.hex()}")
    return addr


# ─── Deploy ───────────────────────────────────────────────────────────────────
print("\nDeploying AuditLog ...")
audit_abi, audit_bin = get_contract("AuditLog")
audit_address = deploy("AuditLog", audit_abi, audit_bin)

print("\nDeploying LaminaFactory ...")
factory_abi, factory_bin = get_contract("LaminaFactory")
factory_address = deploy("LaminaFactory", factory_abi, factory_bin, audit_address)

# ─── Save addresses ───────────────────────────────────────────────────────────
addresses = {
    "network":          "robinhood-testnet",
    "chain_id":         CHAIN_ID,
    "deployer":         account.address,
    "audit_log":        audit_address,
    "lamina_factory":   factory_address,
}

out_path = CONTRACTS_DIR / "deployed_addresses.json"
with open(out_path, "w") as f:
    json.dump(addresses, f, indent=2)

print(f"\n📄 Addresses saved to {out_path}")
print(json.dumps(addresses, indent=2))
print("\n✅ Deployment complete. Copy addresses to server/.env:")
print(f"   AUDIT_LOG_ADDRESS={audit_address}")
print(f"   FACTORY_ADDRESS={factory_address}")
