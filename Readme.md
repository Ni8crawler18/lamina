<p align="center">
  <img src="https://img.shields.io/badge/Networks-10_testnets-8259ef?style=flat-square" />
  <img src="https://img.shields.io/badge/Families-EVM·Hedera·Solana·Sui-6d4bd6?style=flat-square" />
  <img src="https://img.shields.io/badge/Standard-ERC--3643-4B6BFB?style=flat-square" />
  <img src="https://img.shields.io/badge/Settlement-USDC-2775CA?style=flat-square" />
  <img src="https://img.shields.io/badge/Python-FastAPI-009688?style=flat-square" />
  <img src="https://img.shields.io/badge/Next.js-16-000?style=flat-square" />
</p>

# Laminaa

**Autonomous, multi-chain RWA lifecycle agent.**

One command to tokenize a bond. Zero humans to manage it after. Laminaa handles compliance, coupon payments, NAV updates, regulatory reporting and maturity settlement — autonomously — on whichever network your investors are on.

---

## The Problem

Tokenizing an asset takes minutes. Managing it takes years.

Every tokenized bond needs: coupon payments on schedule, KYC checks on every transfer, OFAC sanctions screening, NAV updates from price feeds, quarterly reports for regulators, and maturity redemption at the end. Today, fund admins and lawyers do this manually — costing 5–15 basis points on AUM.

Tokenized RWAs are ~$25B on-chain today and projected at $16T by 2030 (BCG). Every single asset needs lifecycle management. Nobody has automated it — across chains.

## How It Works

```
"Tokenize a $10M 5-year US Treasury bond, US accredited investors only"

Laminaa:
├── Maps asset type → regulatory framework (SEC Reg D / Reg S, MiFID II)
├── Configures KYC whitelist + OFAC SDN sanctions screening
├── Deploys a compliant token on the chosen chain
│     • EVM    → ERC-3643 permissioned token via LaminaFactory
│     • Hedera → native HTS token
│     • Solana → Token-2022 permissioned mint
│     • Sui    → Move closed-loop token (TokenPolicy + KYC rule)
├── Opens an immutable audit trail (AuditLog contract / HCS topic / SPL memo)
├── Schedules coupon payments, NAV updates and maturity
├── Validates every transfer against the compliance rules
├── Settles coupons & principal in USDC
├── Generates quarterly regulatory reports (PDF)
├── At maturity → redeems tokens, returns principal, burns supply
└── Every action recorded on-chain — verifiable on the chain's explorer
```

The compliance, lifecycle and reporting logic is written once; a thin per-chain **adapter** speaks each chain's native protocol. The agent (backend) holds the operator key and signs every on-chain action — users connect a wallet only to identify themselves and their investors.

## Networks

Deployed and live on **10 testnets** across 4 families — 7 EVM + Hedera + Solana + Sui.
USDC settles on 9 of them with genuine Circle USDC (Robinhood, an Arbitrum Orbit demo
chain, uses a public-mint Mock USDC). Full addresses, explorer links and per-chain
notes: [`deployment_contract.txt`](./deployment_contract.txt) · [`docs/DEPLOYMENTS.md`](./docs/DEPLOYMENTS.md).

| Network                             | Chain ID | Family     | Token model       | Settlement  |
| ----------------------------------- | -------: | ---------- | ----------------- | ----------- |
| Arbitrum Sepolia*(source-verified)* |   421614 | EVM        | ERC-3643          | USDC        |
| Robinhood Chain (Arbitrum Orbit)    |    46630 | EVM        | ERC-3643          | USDC (Mock) |
| Base Sepolia                        |    84532 | EVM        | ERC-3643          | USDC        |
| Arc (Circle L1, USDC = gas)         |  5042002 | EVM        | ERC-3643          | USDC + EURC |
| Avalanche Fuji                      |    43113 | EVM        | ERC-3643          | USDC        |
| Ethereum Sepolia                    | 11155111 | EVM        | ERC-3643          | USDC        |
| Polygon Amoy                        |    80002 | EVM        | ERC-3643          | USDC        |
| Hedera Testnet                      |      296 | Hedera     | HTS / HCS         | USDC        |
| Solana Devnet                       |      103 | Solana     | Token-2022        | USDC        |
| Sui Testnet                         |       — | Sui (Move) | Closed-loop token | USDC        |

## Agent Modules

| Module               | What it does                                                                                                                      |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| **Issuance**   | Deploys a compliant token + audit trail in one transaction, on the selected chain                                                 |
| **Compliance** | KYC whitelist, OFAC SDN screening (fuzzy name + address match), jurisdiction enforcement (Reg D/S, MiFID II), transfer validation |
| **Lifecycle**  | Scheduled coupon distribution (USDC), NAV updates from treasury yields, maturity redemption & burn                                |
| **Reporting**  | Quarterly compliance reports, investor statements, audit-trail compilation — downloadable PDFs                                   |

## Interfaces

People **and** agents drive the same engine:

- **Web console / REST** — operator dashboard (Next.js)
- **Telegram** — natural-language ops with write-confirmation on value-moving actions
- **MCP server** — agent-to-agent access with tiered (read/admin) bearer tokens
- **Chat** — Claude-powered natural language ("Who holds this bond?", "Generate Q1 report")

## Architecture

```
 Interfaces                 Laminaa engine (AI agent)            Networks
 ───────────                ────────────────────────           ──────────────────────────
 REST / Web console   ──▶   Issuance · Compliance        ──▶   EVM adapter (web3.py)
 Telegram             ──▶   Lifecycle · Reporting               → ERC-3643 / ERC-20
 MCP server           ──▶   Claude · PostgreSQL · OFAC          Hedera adapter → HTS / HCS
 Chat (NL)            ──▶   scheduler · yield oracle            Solana adapter → Token-2022
                                                                Sui adapter    → Move token
                                                                deploy · settle · audit (USDC)
```

A single **`ChainAdapter`** interface abstracts every chain behind opaque string refs
(`token_ref` / `holder_ref` / `tx_ref`), so the EVM, Hedera, Solana and Sui adapters all
satisfy one contract — the core business logic never imports a chain SDK. A `ChainRegistry`
loads one TOML per network. Adding an EVM chain is a config entry; a new family is one
adapter — never a rewrite of the lifecycle, compliance or reporting code.

## Stack

```
Backend     Python · FastAPI · SQLAlchemy (async) · PostgreSQL · APScheduler
Chains      web3.py (EVM) · hiero-sdk-python (Hedera) · solders/solana-py (Solana) · pysui (Sui)
            — per-chain TOML registry behind one ChainAdapter interface
Contracts   EVM: Solidity 0.8.20 · Foundry · OpenZeppelin · ERC-3643 · AuditLog · LaminaFactory
            Sui: Move · sui::token closed-loop package (contracts-sui/)
Frontend    Next.js 16 · TypeScript · TailwindCSS · shadcn/ui
AI          Claude (Anthropic) — chat agent with tool use; shared tool layer (REST · MCP · Telegram)
Screening   OFAC SDN list · rapidfuzz fuzzy matching · daily refresh
Settlement  USDC (Circle) on 9 chains · Mock USDC on Robinhood · EURC on Arc
Wallets     MetaMask (EVM) · HashPack (Hedera) · Phantom (Solana) · Sui Wallet · Google sign-in
```

## Quick Start

```bash
git clone https://github.com/Ni8crawler18/lamina.git && cd lamina

# 1. infra — PostgreSQL on :5433
docker compose up -d

# 2. backend
python -m venv venv && source venv/bin/activate
pip install -e server/                 # optional chains: pip install -e "server/[solana,hedera,sui]"
cp server/.env.example server/.env     # add RPC URLs, deployer key, Anthropic key

# 3. frontend
cd client && npm install && cp .env.example .env.local && cd ..
# (set NEXT_PUBLIC_GOOGLE_CLIENT_ID for Google sign-in)

# 4. run
cd server && PYTHONPATH=. uvicorn app.main:app --port 8000 --reload   # terminal 1
cd client && npm run dev                                              # terminal 2
```

**Dashboard** → `localhost:3000` · **API docs** → `localhost:8000/docs` · **Pitch deck** → `localhost:3000/slides.html`

## Demo Flow

1. **Issue** — Natural-language command → agent deploys the token + audit trail on the selected chain
2. **Onboard** — Whitelist an investor with KYC + OFAC screening (KYC granted on-chain)
3. **Block** — Sanctioned/non-compliant party tries to transfer → agent blocks, logs the reason on-chain
4. **Coupon** — Agent distributes interest to all holders proportionally, in USDC
5. **NAV** — Agent pulls a treasury yield and updates valuation
6. **Report** — Agent generates a compliance report PDF from on-chain data
7. **Mature** — Agent redeems all tokens, returns principal, burns supply, final report

Every step appears in **Audit History** with a one-click explorer link to its on-chain transaction.

## API

| Method   | Endpoint                               | Description                           |
| -------- | -------------------------------------- | ------------------------------------- |
| `GET`  | `/api/chains`                        | List configured networks              |
| `GET`  | `/api/assets?chain=<slug>`           | List assets (chain-scoped)            |
| `POST` | `/api/assets`                        | Issue a new asset (`chain` in body) |
| `POST` | `/api/assets/{id}/whitelist`         | Add to KYC whitelist (OFAC-screened)  |
| `POST` | `/api/assets/{id}/purchase`          | Compliant primary-market purchase     |
| `POST` | `/api/assets/{id}/distribute-coupon` | Distribute coupon in USDC             |
| `POST` | `/api/assets/{id}/update-nav`        | Update NAV (oracle or manual)         |
| `POST` | `/api/assets/{id}/mature`            | Execute maturity & redemption         |
| `GET`  | `/api/assets/{id}/audit-log`         | On-chain audit trail                  |
| `POST` | `/api/assets/{id}/reports`           | Generate a report PDF                 |
| `POST` | `/api/ofac/screen`                   | OFAC sanctions check                  |
| `POST` | `/api/chat`                          | Natural-language agent                |

## Project Structure

```

Laminaa/
├── server/                       # Python FastAPI backend
│   ├── app/
│   │   ├── main.py               # app init, routers, lifespan
│   │   ├── chains/               # ChainAdapter interface + registry
│   │   │   ├── evm/              #   web3.py adapter (ERC-3643 / ERC-20)
│   │   │   ├── hedera/           #   hiero-sdk adapter (HTS / HCS)
│   │   │   ├── solana/           #   solders adapter (Token-2022)
│   │   │   └── sui/              #   pysui adapter (Move closed-loop token)
│   │   ├── services/             # issuance, compliance, lifecycle, payout, reporting, ai
│   │   ├── routes/               # REST endpoints
│   │   ├── channels/             # Telegram bot
│   │   ├── mcp/                  # MCP server + tiered auth
│   │   ├── integrations/         # OFAC screening, yield/FX oracles
│   │   └── models/               # SQLAlchemy ORM
│   └── config/chains/*.toml      # one config per network
├── contracts/                    # Solidity (Foundry) — ERC-3643 token, AuditLog, factory
├── contracts-sui/                # Move — sui::token closed-loop RWA package (lamina_rwa)
├── client/                       # Next.js 16 frontend
│   ├── src/app/                  # dashboard, assets, liquidity, payouts, reports, history, agent
│   ├── src/components/           # UI, login, chain toggle
│   └── src/lib/chains.ts         # network registry (frontend)
├── docs/DEPLOYMENTS.md           # per-chain deployment guide (all 10 chains)
├── deployment_contract.txt       # deployed addresses + explorer links (all 10 chains)
└── CLAUDE.md                     # project spec
```

## License

MIT
