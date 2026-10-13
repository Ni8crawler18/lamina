<p align="center">
  <img src="client/public/brand/banner-1500x500.png" alt="Laminaa" width="100%" />
</p>

<h1 align="center">Laminaa</h1>

<p align="center">
  <b>The back office for tokenized assets.</b><br/>
  One instruction to issue. One agent to run everything after: compliance, payouts, NAV, reporting and redemption, on 11 networks.
</p>

<p align="center">
  <a href="https://laminaa.com"><b>laminaa.com</b></a> ·
  <a href="#see-it-live">Live on-chain proof</a> ·
  <a href="#quick-start">Quick start</a> ·
  <a href="./deployment_contract.txt">Deployed contracts</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Networks-11_testnets-8259ef?style=flat-square" />
  <img src="https://img.shields.io/badge/Families-EVM·Hedera·Solana·Sui-6d4bd6?style=flat-square" />
  <img src="https://img.shields.io/badge/Standard-ERC--3643-4B6BFB?style=flat-square" />
  <img src="https://img.shields.io/badge/Settlement-USDC-2775CA?style=flat-square" />
  <img src="https://img.shields.io/badge/Agent-Claude-D97757?style=flat-square" />
  <img src="https://img.shields.io/badge/License-MIT-333?style=flat-square" />
</p>

---

## Why

Tokenizing an asset takes minutes. Running it takes years.

A tokenized bond or fund share is a living instrument. Every transfer has to clear KYC and sanctions screening, coupons have to reach every eligible holder on schedule, NAV has to move, regulators want reports, and at maturity every holder has to be redeemed. Issuance platforms stop at the mint. The rest still runs on spreadsheets, transfer agents and fund admins, at 5–15+ bps of AUM a year.

On-chain RWAs have grown from ~$5.5B to ~$24B in three years, with BCG projecting up to $16T by 2030. Every one of those assets needs its lifecycle operated. **Laminaa automates that, on whichever chain the investors are on.**

## What it does

```text
"Tokenize a $10M 5-year US Treasury bond, US accredited investors only"
```

| Stage | What the agent does |
| --- | --- |
| **Issue** | Deploys a permissioned security token and opens its on-chain audit trail in one call |
| **Comply** | KYC whitelist, jurisdiction and investor-type rules, and OFAC SDN screening (fuzzy name + exact address, refreshed daily). Non-compliant transfers revert **in the token contract**, not just in the UI |
| **Pay** | Calculates and distributes coupons and dividends per holder, in Circle USDC |
| **Value** | Updates NAV from treasury-yield oracles or by instruction |
| **Report** | Compliance reports, investor statements and audit compilations as downloadable PDFs |
| **Mature** | Redeems every holder, returns principal in USDC, burns supply, issues the final report |
| **Audit** | Writes every state-changing action to an on-chain audit log, mirrored in Postgres, with one-click explorer links |

You operate it in plain English, or through code:

- **Web console:** dashboard, assets, payouts, reports, history and an agent chat
- **MCP server:** any AI client can drive Laminaa, with tiered read/admin tokens; value-moving tools are gated separately
- **Telegram:** natural-language ops with confirmation on every value-moving action
- **REST API:** everything the agent can do, as endpoints

All four share one tool layer, so a capability added once appears everywhere.

## See it live

Everything below is a real transaction on **Monad Testnet**, the newest network added to Laminaa:

| Action | Proof |
| --- | --- |
| Bond issued: *Meridian US Treasury Note 2031*, 4.25% semi-annual | [token](https://testnet.monadexplorer.com/address/0x772169f151A3Edbe3Ab2AE601f3d5d27BB64fcAE) |
| Investor KYC'd, OFAC-cleared, subscribed | [tx](https://testnet.monadexplorer.com/tx/0xec9be8c420a903e3e8e01421c40ea1dc36ecf9dc7eae5ca985a34bb5f476dca4) |
| Lazarus Group wallet blocked at onboarding | 100% OFAC SDN match, rejected before any on-chain action |
| Equity issued: *Meridian Growth Equity* | [token](https://testnet.monadexplorer.com/address/0xe75E7651fd8D4D1Ff8160B0Ae561Ac7999eaAd4b) |
| Quarterly dividend paid to 4 holders in Circle USDC | [tx](https://testnet.monadexplorer.com/tx/0x9a5cc07f3519388a3d00770577d2215757b9daeecac7b23e824031d3521dfce2) |

Or try it yourself: open [laminaa.com](https://laminaa.com), click **Explore without a wallet**, pick a network and ask the agent anything.

## Networks

Live on **11 testnets** across 4 chain families. One engine; a thin adapter per chain.

| Network | Chain ID | Family | Token model | Settlement |
| --- | ---: | --- | --- | --- |
| Monad Testnet | 10143 | EVM | ERC-3643 | USDC |
| Arbitrum Sepolia *(source-verified)* | 421614 | EVM | ERC-3643 | USDC |
| Robinhood Chain (Arbitrum Orbit) | 46630 | EVM | ERC-3643 | USDG (Paxos) |
| Base Sepolia | 84532 | EVM | ERC-3643 | USDC |
| Arc (Circle L1, USDC as gas) | 5042002 | EVM | ERC-3643 | USDC + EURC |
| Avalanche Fuji | 43113 | EVM | ERC-3643 | USDC |
| Ethereum Sepolia | 11155111 | EVM | ERC-3643 | USDC |
| Polygon Amoy | 80002 | EVM | ERC-3643 | USDC |
| Hedera Testnet | 296 | Hedera | HTS token + HCS topic | USDC |
| Solana Devnet | — | Solana | Token-2022 | USDC |
| Sui Testnet | — | Sui (Move) | Closed-loop token | USDC |

Payouts settle in Circle's official USDC everywhere except Robinhood Chain, where Circle doesn't issue, so they settle in Paxos's regulated Global Dollar (USDG). Addresses and explorer links: [`deployment_contract.txt`](./deployment_contract.txt). Per-chain guide: [`docs/DEPLOYMENTS.md`](./docs/DEPLOYMENTS.md).

## Architecture

```text
 Interfaces              Laminaa engine                          Settlement
 ──────────              ──────────────                          ──────────
 Web console  ─┐         routes/        thin HTTP layer          ┌─ EVM adapter (web3.py)
 Agent chat   ─┤                                                 │    ERC-3643 · AuditLog · Factory
 MCP server   ─┼──▶      services/      issuance · compliance ──▶├─ Hedera adapter  → HTS / HCS
 Telegram     ─┤                        payout · lifecycle       ├─ Solana adapter  → Token-2022
 REST         ─┘                        reporting · audit · AI   └─ Sui adapter     → Move token
                         repositories/  all SQL (Postgres)
                         handlers/      bond · equity · fund · real estate · carbon
                         integrations/  OFAC SDN · yield & FX oracles
```

- **One interface, every chain.** `ChainAdapter` speaks in opaque refs (`token_ref`, `holder_ref`, `tx_ref`), so EVM addresses, Solana pubkeys and Sui object IDs all fit the same contract. Business logic never imports a chain SDK.
- **Adding an EVM chain is config, not code.** Drop a TOML into `server/config/chains/`, deploy the two contracts and set `enabled = true`. Monad went from zero to live this way. A new chain family needs one new adapter.
- **Asset types are strategies.** Bond coupons, equity dividends, fund distributions, monthly rental income and carbon-credit retirement come from per-type handlers, not `if` chains.
- **The backend signs, users identify.** The operator key signs every on-chain action. Investors and issuers connect a wallet only to identify themselves.

## Stack

| Layer | Tech |
| --- | --- |
| Backend | Python · FastAPI · SQLAlchemy 2.0 (async) · PostgreSQL · APScheduler |
| Chains | web3.py · hiero-sdk-python · solana-py/solders · pysui |
| Contracts | Solidity 0.8.20 · Foundry · OpenZeppelin (`contracts/`) · Sui Move (`contracts-sui/`) |
| Indexing | The Graph subgraph for independently verifiable lifecycle history (`subgraph/`) |
| AI | Claude (Anthropic) with tool use, one tool layer for chat, MCP and Telegram |
| Compliance | OFAC SDN list · rapidfuzz WRatio matching · daily refresh |
| Frontend | Next.js 16 · TypeScript · Tailwind · shadcn/ui |
| Wallets | MetaMask · HashPack · Phantom · Sui Wallet · Google sign-in |

## Quick start

**Prerequisites:** Docker, Python 3.11+, Node 20+, and [Foundry](https://getfoundry.sh) for contracts.

```bash
git clone https://github.com/Ni8crawler18/lamina.git && cd lamina

# 1. Postgres on :5433
docker compose up -d

# 2. Backend
python -m venv venv && source venv/bin/activate
pip install -e "server[dev]"                 # non-EVM chains: add solana,hedera,sui
cp server/.env.sample server/.env            # DEPLOYER_PRIVATE_KEY, OPERATOR_ADDRESS, ANTHROPIC_API_KEY
cd server && PYTHONPATH=. uvicorn app.main:app --reload --port 8000

# 3. Frontend (new terminal)
cd client && npm install && npm run dev
```

| | |
| --- | --- |
| Dashboard | http://localhost:3000 |
| API docs | http://localhost:8000/docs |
| Health (enabled chains, OFAC status) | http://localhost:8000/health |

```bash
# Tests
cd server && PYTHONPATH=. pytest              # chain config + adapter conformance
cd contracts && forge test                     # token, factory, audit log
```

## API

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/chains` | Configured networks |
| `GET` | `/api/assets?chain=<slug>` | Assets, optionally per chain |
| `POST` | `/api/assets` | Issue an asset (`chain` in body) |
| `POST` | `/api/assets/{id}/whitelist` | KYC-whitelist an investor (OFAC-screened) |
| `POST` | `/api/assets/{id}/purchase` | Compliant primary subscription |
| `POST` | `/api/assets/{id}/distribute-coupon` | Pay coupon or dividend in USDC |
| `POST` | `/api/assets/{id}/update-nav` | Update NAV (oracle or manual) |
| `POST` | `/api/assets/{id}/mature` | Maturity redemption |
| `GET` | `/api/assets/{id}/audit-log` | On-chain audit trail |
| `POST` | `/api/assets/{id}/reports` | Generate a report PDF |
| `POST` | `/api/ofac/screen` | Sanctions check |
| `POST` | `/api/chat` | Natural-language agent |

Full schema at `/docs` when the server is running.

## Repository

```text
server/            FastAPI backend: routes · services · repositories · chains · handlers · integrations · mcp · channels
server/config/     one TOML per network (public config; secrets live in server/.env)
contracts/         Solidity: LaminaRWAToken (ERC-3643-style) · LaminaFactory · AuditLog
contracts-sui/     Move: closed-loop RWA token package
subgraph/          The Graph indexer for lifecycle events
client/            Next.js operator console
docs/              deployment guide and images
```

## License

[MIT](./LICENSE)
