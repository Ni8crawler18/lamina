# Adding a new chain

Chains are pure config. To add one:

1. **Create `backend/config/chains/<slug>.toml`** (copy an existing one):
   ```toml
   name = "..."; slug = "<slug>"; family = "evm"   # or "hedera" / "solana"
   chain_id = <id>; enabled = false; native_symbol = "ETH"
   rpc_url = "<public testnet rpc>"
   rpc_url_env = "RPC_URL_<SLUG_UPPER>"   # optional private override
   explorer_url = "<blockscout/etherscan>"
   [contracts]
   factory = ""; audit_log = ""; usdc = "<usdc address>"
   ```
2. **(EVM) Deploy the Laminaa contracts** to that chain and fill `factory` + `audit_log`.
   Find the chain's canonical USDC (Circle docs) and set `usdc`.
3. **Secrets** stay in `.env` — the deployer key is reused across EVM chains. For a
   private/paid RPC set the `rpc_url_env` var. Hedera needs `HEDERA_OPERATOR_ID/KEY`.
4. **Flip `enabled = true`.** The `ChainRegistry` picks it up at next startup; the
   adapter is resolved by `family`.

No code change is needed to add an EVM chain — only TOML + deployed contracts.

## Families

- **evm** → `app/chains/evm/` (one adapter, parametrized per chain via ChainConfig).
- **hedera** → `app/chains/hedera/` (native HTS/HCS; ports the old `server/hedera/`).
- **solana** → phase 2.

## Gotchas

- `chain_id` for non-EVM chains is just an identifier (Hedera uses 296).
- A chain is only adapter-resolvable when `enabled = true` AND its required contracts
  are set; `registry.adapter(slug)` raises otherwise.
