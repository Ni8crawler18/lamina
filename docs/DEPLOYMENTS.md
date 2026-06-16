# Laminaa — Deployments & On-Chain Footprint

A complete, verifiable map of everything Laminaa has deployed across **10 testnets**
in **4 chain families**. Every address below links to its block explorer.

- **Raw address list (plain text):** [`deployment_contract.txt`](../deployment_contract.txt)
- **Config source of truth:** `server/config/chains/*.toml`
- **Analytics:** Dune project `laminaa` — https://dune.com/cinnamon125169/laminaa

_Last updated: 2026-06-16._

---

## At a glance

| # | Network | Chain ID | Family | Token model | Settlement | Status |
|--:|---------|---------:|--------|-------------|-----------|--------|
| 1 | Arbitrum Sepolia | 421614 | EVM | ERC-3643 | USDC (Circle) | ✅ live · source-verified |
| 2 | Robinhood Chain (Orbit) | 46630 | EVM | ERC-3643 | USDC (Mock) | ✅ live |
| 3 | Base Sepolia | 84532 | EVM | ERC-3643 | USDC (Circle) | ✅ live |
| 4 | Arc Testnet | 5042002 | EVM | ERC-3643 | USDC (native gas) + EURC | ✅ live |
| 5 | Avalanche Fuji | 43113 | EVM | ERC-3643 | USDC (Circle) | ✅ live |
| 6 | Ethereum Sepolia | 11155111 | EVM | ERC-3643 | USDC (Circle) | ✅ live · Dune-decoded |
| 7 | Polygon Amoy | 80002 | EVM | ERC-3643 | USDC (Circle) | ✅ live |
| 8 | Hedera Testnet | 296 | Hedera | HTS + HCS | USDC (Circle HTS) | ✅ live |
| 9 | Solana Devnet | 103 | Solana | Token-2022 | USDC (Circle) | ✅ live |
| 10 | Sui Testnet | — | Sui (Move) | Closed-loop token | USDC (Circle) | ✅ live |

> USDC settles on **9 of 10** chains with genuine Circle USDC; Robinhood (an Arbitrum
> Orbit demo chain) uses a public-mint **Mock USDC** since Circle does not issue there.

### What "deployed" means per family

- **EVM (7 chains):** a `LaminaFactory` + `AuditLog` are deployed once per chain. Each
  asset is an **ERC-3643-style** `LaminaRWAToken` minted by the factory at runtime
  (so token addresses are per-asset, not fixed). Adding a new EVM chain is a TOML entry.
- **Hedera:** no contracts — assets are native **HTS** tokens, the audit trail is an
  **HCS** topic, both created at runtime by the operator account.
- **Solana:** no program — assets are native **Token-2022** mints (permissioned via
  Token-2022 extensions); the audit trail is on-chain **SPL memos** anchored per asset.
- **Sui:** a Move **`lamina_rwa`** package is published once; compliance is enforced by a
  `sui::token` **TokenPolicy** + allowlist (KYC) rule; each asset is a shared `Asset`
  ledger object. The operator holds the capability objects.

### Operators (hold the keys, sign every action)

| Family | Operator |
|--------|----------|
| EVM (all) | `0xFa3e5d58ea338A274B7d739117AFfAe80168A429` |
| Hedera | `0.0.8003096` |
| Sui | `0x70b2d6e827e3690eefb9f0912b92a7c9309fba2b8f26cff88dfc5c51900e91d9` |
| Solana | keypair in `SOLANA_OPERATOR_KEY` / `SOLANA_KEYPAIR_PATH` (not a fixed address) |

> **Deterministic addresses:** Base, Arc, Avalanche and Ethereum Sepolia share the same
> `LaminaFactory`/`AuditLog` addresses — same operator + same nonce → `CREATE` yields
> identical addresses across chains. This is expected, not a copy-paste error.

---

## EVM chains

ERC-3643 permissioned token · `LaminaFactory` · `AuditLog` · USDC settlement.

### 1 · Arbitrum Sepolia — `421614` · source-verified on Arbiscan
Explorer: https://sepolia.arbiscan.io

| Contract | Address |
|----------|---------|
| LaminaFactory | [`0x8610E57f1357a41c2991ba64764c2Fdc8b2DD33e`](https://sepolia.arbiscan.io/address/0x8610E57f1357a41c2991ba64764c2Fdc8b2DD33e) |
| AuditLog | [`0x2721b95C0fF4756D71Ab6357A38C35e458627595`](https://sepolia.arbiscan.io/address/0x2721b95C0fF4756D71Ab6357A38C35e458627595) |
| USDC (Circle) | [`0x75faf114eafb1BDbe2F0316DF893fd58CE46AA4d`](https://sepolia.arbiscan.io/address/0x75faf114eafb1BDbe2F0316DF893fd58CE46AA4d) |

### 2 · Robinhood Chain testnet — `46630` · Arbitrum Orbit
Explorer: https://explorer.testnet.chain.robinhood.com

| Contract | Address |
|----------|---------|
| LaminaFactory | [`0xd556c46758B2C4B62f929256dc3FA53fbd375A3A`](https://explorer.testnet.chain.robinhood.com/address/0xd556c46758B2C4B62f929256dc3FA53fbd375A3A) |
| AuditLog | [`0x153786D589c1d3bddEa68f232269d47Cb110D6Cd`](https://explorer.testnet.chain.robinhood.com/address/0x153786D589c1d3bddEa68f232269d47Cb110D6Cd) |
| USDC (Mock, public mint) | [`0x5B6C7cAF7F99f99154fD8375ec935Fcf03F326f5`](https://explorer.testnet.chain.robinhood.com/address/0x5B6C7cAF7F99f99154fD8375ec935Fcf03F326f5) |

> The Robinhood explorer occasionally returns 5xx (their infra); the RPC stays live.

### 3 · Base Sepolia — `84532`
Explorer: https://sepolia.basescan.org

| Contract | Address |
|----------|---------|
| LaminaFactory | [`0x45a36ea47577A4415cAc75256F78ccD66bC29E2c`](https://sepolia.basescan.org/address/0x45a36ea47577A4415cAc75256F78ccD66bC29E2c) |
| AuditLog | [`0xca7f1c8BC559F0E20c3F12085A7Fa426397977f7`](https://sepolia.basescan.org/address/0xca7f1c8BC559F0E20c3F12085A7Fa426397977f7) |
| USDC (Circle) | [`0x036CbD53842c5426634e7929541eC2318f3dCF7e`](https://sepolia.basescan.org/address/0x036CbD53842c5426634e7929541eC2318f3dCF7e) |

### 4 · Arc Testnet — `5042002` · Circle's stablecoin L1 (USDC is the gas token)
Explorer: https://testnet.arcscan.app

| Contract | Address |
|----------|---------|
| LaminaFactory | [`0x45a36ea47577A4415cAc75256F78ccD66bC29E2c`](https://testnet.arcscan.app/address/0x45a36ea47577A4415cAc75256F78ccD66bC29E2c) |
| AuditLog | [`0xca7f1c8BC559F0E20c3F12085A7Fa426397977f7`](https://testnet.arcscan.app/address/0xca7f1c8BC559F0E20c3F12085A7Fa426397977f7) |
| USDC (native ERC-20, 6 dp) | [`0x3600000000000000000000000000000000000000`](https://testnet.arcscan.app/address/0x3600000000000000000000000000000000000000) |
| EURC (6 dp) | [`0x89B50855Aa3bE2F677cD6303Cec089B5F319D72a`](https://testnet.arcscan.app/address/0x89B50855Aa3bE2F677cD6303Cec089B5F319D72a) |

### 5 · Avalanche Fuji — `43113`
Explorer: https://testnet.snowtrace.io

| Contract | Address |
|----------|---------|
| LaminaFactory | [`0x45a36ea47577A4415cAc75256F78ccD66bC29E2c`](https://testnet.snowtrace.io/address/0x45a36ea47577A4415cAc75256F78ccD66bC29E2c) |
| AuditLog | [`0xca7f1c8BC559F0E20c3F12085A7Fa426397977f7`](https://testnet.snowtrace.io/address/0xca7f1c8BC559F0E20c3F12085A7Fa426397977f7) |
| USDC (Circle) | [`0x5425890298aed601595a70AB815c96711a31Bc65`](https://testnet.snowtrace.io/address/0x5425890298aed601595a70AB815c96711a31Bc65) |

### 6 · Ethereum Sepolia — `11155111` · decoded on Dune (`laminaa_sepolia.*`)
Explorer: https://sepolia.etherscan.io

| Contract | Address |
|----------|---------|
| LaminaFactory | [`0x45a36ea47577A4415cAc75256F78ccD66bC29E2c`](https://sepolia.etherscan.io/address/0x45a36ea47577A4415cAc75256F78ccD66bC29E2c) |
| AuditLog | [`0xca7f1c8BC559F0E20c3F12085A7Fa426397977f7`](https://sepolia.etherscan.io/address/0xca7f1c8BC559F0E20c3F12085A7Fa426397977f7) |
| USDC (Circle) | [`0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238`](https://sepolia.etherscan.io/address/0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238) |

### 7 · Polygon Amoy — `80002`
Explorer: https://amoy.polygonscan.com

| Contract | Address |
|----------|---------|
| LaminaFactory | [`0xa96aAbCE0Ab4c9758B05D361d09A11144F3F6D6A`](https://amoy.polygonscan.com/address/0xa96aAbCE0Ab4c9758B05D361d09A11144F3F6D6A) |
| AuditLog | [`0x45a36ea47577A4415cAc75256F78ccD66bC29E2c`](https://amoy.polygonscan.com/address/0x45a36ea47577A4415cAc75256F78ccD66bC29E2c) |
| USDC (Circle) | [`0x41E94Eb019C0762f9Bfcf9Fb1E58725BfB0e7582`](https://amoy.polygonscan.com/address/0x41E94Eb019C0762f9Bfcf9Fb1E58725BfB0e7582) |
| Sample asset — "Amoy Test Bond" (ATB) | [`0x8a3722aD41072d9c39b1CB4a7fEF05B8b5DE42C9`](https://amoy.polygonscan.com/address/0x8a3722aD41072d9c39b1CB4a7fEF05B8b5DE42C9) |

---

## Non-EVM chains

### 8 · Hedera Testnet — `296` (identifier only) · HTS + HCS
Explorer: https://hashscan.io/testnet

No fixed contracts. Each asset is an **HTS** token and its audit trail is an **HCS**
topic, created at runtime by the operator account (so IDs are per-asset).

| Resource | ID |
|----------|----|
| USDC (Circle testnet HTS) | [`0.0.429274`](https://hashscan.io/testnet/token/0.0.429274) |
| Operator account | [`0.0.8003096`](https://hashscan.io/testnet/account/0.0.8003096) |

### 9 · Solana Devnet — cluster `103` · Token-2022
Explorer: https://solscan.io (append `?cluster=devnet`)

No program. Each asset is a native **Token-2022** mint (permissioned via Token-2022
extensions); the audit trail is on-chain **SPL memos** anchored per asset. The
production audit upgrade is an Anchor program (its program id would go in the TOML as
`audit_log`).

| Resource | Address |
|----------|---------|
| USDC (Circle devnet mint) | [`4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU`](https://solscan.io/token/4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU?cluster=devnet) |
| Operator | keypair from `SOLANA_OPERATOR_KEY` / `SOLANA_KEYPAIR_PATH` |

### 10 · Sui Testnet · Move closed-loop token (`lamina_rwa`, published 2026-06-07)
Explorer: https://suiscan.xyz/testnet · source in `contracts-sui/`

Compliance is enforced by a `sui::token` **TokenPolicy<RWA>** + allowlist (KYC) rule;
each asset is a shared `Asset` ledger object. The operator holds the capability objects.

| Object | ID |
|--------|----|
| Operator | [`0x70b2d6e827e3690eefb9f0912b92a7c9309fba2b8f26cff88dfc5c51900e91d9`](https://suiscan.xyz/testnet/account/0x70b2d6e827e3690eefb9f0912b92a7c9309fba2b8f26cff88dfc5c51900e91d9) |
| Package `lamina_rwa` | [`0x536b168e3784d71e5f93775ec5ca6ee9b54f85b9a47e492ef901dd3310ca3dbe`](https://suiscan.xyz/testnet/object/0x536b168e3784d71e5f93775ec5ca6ee9b54f85b9a47e492ef901dd3310ca3dbe) |
| TokenPolicy\<RWA\> (shared) | `0x161e1033d03d131b8d36939daf56c28617dbb0797f9782c8b64a5f61601eec8d` |
| TokenPolicyCap\<RWA\> | `0x19a8043b75092027cbe61f7cc0f3aa80d7b1413a6a1f90cdf3a83594ef1f4602` |
| TreasuryCap\<RWA\> | `0x042e35fdbc6e68285da80a893691be33fa3c141e028850699380f0d830247594` |
| OperatorCap | `0x6efe70e4689c43becddf933d83b3a47f2fb7f96b2ab6eb4537f0946610244d4c` |
| UpgradeCap | `0x30fd0cdbd404aa5016d845b81bde041076a8dc45bebd3e43016627db1382ef07` |
| USDC (Circle testnet) | `0xa1ec7fc00a6f40db9693ad1415d0c193ad3906494428cf252621037bd7117e29::usdc::USDC` (6 dec) |

---

## Analytics (Dune)

`LaminaFactory` and `AuditLog` are submitted for decoding on **Ethereum Sepolia** under
the Dune project `laminaa`, producing tables under `laminaa_sepolia.*`:

| Table | What it captures |
|-------|------------------|
| `laminaa_sepolia.LaminaFactory_evt_AssetDeployed` | Every asset tokenized (token addr, name, symbol, deployer) |
| `laminaa_sepolia.AuditLog_evt_ActionLogged` | Every lifecycle action (KYC, transfer, coupon, NAV, maturity) |
| `laminaa_sepolia.AuditLog_evt_TopicCreated` | Audit topic opened per asset |

Dashboard: **https://dune.com/cinnamon125169/laminaa**

Dune indexes mainnets and a limited set of testnets — among Laminaa's chains, **Ethereum
Sepolia** is the one currently decodable. The full multi-chain dashboard lands when the
contracts deploy to mainnet (Arc + EVM mainnets).

---

## How to add a chain

- **EVM:** drop a `server/config/chains/<chain>.toml` (RPC, explorer, `chain_id`,
  `[contracts]` factory/audit_log/usdc), deploy with `contracts/deploy.sh`, set
  `enabled = true`. No code change.
- **New family (Hedera / Solana / Sui style):** add an adapter under `app/chains/<family>/`
  implementing `ChainAdapter`, plus a `_build_adapter` branch in `registry.py`, then a TOML.
