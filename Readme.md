<p align="center">
  <img src="https://img.shields.io/badge/Hedera-Testnet-8259ef?style=flat-square" />
  <img src="https://img.shields.io/badge/Python-FastAPI-009688?style=flat-square" />
  <img src="https://img.shields.io/badge/Next.js-16-000?style=flat-square" />
  <img src="https://img.shields.io/badge/AI-Claude_API-d97706?style=flat-square" />
</p>

# Lamina

**Autonomous RWA lifecycle agent on Hedera.**

One command to tokenize a bond. Zero humans to manage it after. Lamina handles compliance, coupon payments, NAV updates, regulatory reporting, and maturity settlement — autonomously.

---

## The Problem

Tokenizing an asset takes minutes. Managing it takes years.

Every tokenized bond needs: coupon payments on schedule, KYC checks on every transfer, OFAC sanctions screening, NAV updates from price feeds, quarterly reports for regulators, and maturity redemption at the end. Today, fund admins and lawyers do this manually — costing 5-15 basis points on AUM.

The tokenized RWA market is $33B today, projected $16T by 2030. Every single asset needs lifecycle management. Nobody has automated it.

## How It Works

```
"Tokenize a $10M 5-year US Treasury bond, US accredited investors only"

Lamina:
├── Maps asset type → regulatory framework (SEC Reg D)
├── Configures KYC whitelist + OFAC sanctions screening
├── Deploys compliant token on Hedera (HTS)
├── Creates immutable audit topic (HCS)
├── Schedules coupon payments, NAV updates, maturity
├── Validates every transfer against compliance rules
├── Generates quarterly regulatory reports (PDF)
├── At maturity → redeems tokens, returns principal, burns supply
└── Every action logged on-chain — verifiable on HashScan
```

## Agent Modules

| Module | What it does |
|--------|-------------|
| **Compliance** | KYC whitelist, OFAC SDN screening (fuzzy match), jurisdiction enforcement (SEC Reg D/S, MiFID II), transfer validation |
| **Lifecycle** | Token issuance, scheduled coupon distribution, NAV updates from treasury yields, maturity redemption & burn |
| **Reporting** | Quarterly compliance reports, investor statements, audit trail compilation — all as downloadable PDFs |
| **Chat** | Natural language interface powered by Claude. "Who holds this bond?" "Generate Q1 report." |

## Hedera Integration

Not a wrapper. Lamina uses Hedera's native services for every operation.

| Service | Usage |
|---------|-------|
| **HTS** | Token create, mint, transfer, wipe, burn — with KYC and freeze keys for compliance |
| **HCS** | Per-asset audit topics. Every agent action logged immutably. Verifiable on HashScan |
| **Mirror Node** | Token balances, transaction history, HCS message retrieval for reports |
| **HashConnect** | Real wallet pairing via HashPack — not a simulated connection |

## Stack

```
Backend     Python · FastAPI · SQLite · APScheduler · hiero-sdk-python
Frontend    Next.js 16 · TypeScript · TailwindCSS · shadcn/ui
AI          Claude API (Anthropic) — chat agent with tool use
Screening   OFAC SDN list · rapidfuzz fuzzy matching · daily refresh
Wallet      HashConnect · WalletConnect · HashPack
```

## Quick Start

```bash
git clone https://github.com/Ni8crawler18/lamina.git && cd lamina

# backend
python -m venv venv && source venv/bin/activate
pip install -r server/requirements.txt

# frontend
cd client && npm install && cd ..

# environment — add your Hedera + Anthropic keys
cp .env.example .env

# run
python -m uvicorn server.main:app --port 8000 --reload   # terminal 1
cd client && npm run dev                                   # terminal 2
```

**Dashboard** → `localhost:3000` · **API** → `localhost:8000/docs` · **Pitch Deck** → `localhost:3000/slides.html`

## Demo Flow

1. **Issue** — Natural language command → agent deploys HTS token + HCS audit topic
2. **Onboard** — Whitelist investor with KYC + OFAC screening
3. **Block** — Sanctioned party tries to buy → agent blocks, logs reason on-chain
4. **Coupon** — Agent distributes interest to all holders proportionally
5. **NAV** — Agent pulls treasury yield, updates valuation
6. **Report** — Agent generates compliance report PDF from on-chain data
7. **Mature** — Agent redeems all tokens, returns principal, burns supply, final report

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/assets` | List all assets |
| `POST` | `/api/assets` | Issue new asset |
| `POST` | `/api/assets/{id}/whitelist` | Add to KYC whitelist |
| `POST` | `/api/assets/{id}/distribute-coupon` | Distribute coupon |
| `POST` | `/api/assets/{id}/mature` | Execute maturity |
| `GET` | `/api/assets/{id}/audit-log` | HCS audit trail |
| `POST` | `/api/assets/{id}/reports` | Generate report |
| `GET` | `/api/events/upcoming` | Cross-asset event timeline |
| `POST` | `/api/ofac/screen` | OFAC sanctions check |
| `POST` | `/api/chat` | Natural language agent |

## Project Structure

```
lamina/
├── server/
│   ├── main.py                 # FastAPI app
│   ├── agents/                 # compliance, lifecycle, reporting, chat
│   ├── hedera/                 # HTS token ops, HCS audit logging
│   ├── ofac/                   # OFAC SDN screening
│   ├── oracle/                 # treasury rates, FX rates
│   ├── routes/                 # API endpoints
│   └── scheduler/              # automated jobs
├── client/
│   ├── src/app/                # Next.js pages
│   ├── src/components/         # UI components
│   └── public/slides.html      # pitch deck
└── CLAUDE.md                   # project spec
```

## License

MIT
