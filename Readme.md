# Lamina — Autonomous RWA Lifecycle Agent on Hedera

An AI agent that autonomously manages the full lifecycle of tokenized real-world assets (RWAs) on Hedera — from issuance and compliance configuration to coupon distribution, NAV updates, maturity settlement, and regulatory reporting.

**Fund manager issues one command** ("Tokenize this bond") and Lamina handles everything for the asset's entire life.

## How It Works

```
Fund Manager: "Tokenize a $10M 5-year US Treasury bond, US accredited investors only"

Lamina Agent:
├── Identifies asset type → maps to regulatory framework (SEC Reg D)
├── Configures KYC whitelist + transfer restrictions
├── Deploys compliant token via Hedera Token Service (HTS)
├── Creates immutable audit topic via Hedera Consensus Service (HCS)
├── Schedules recurring coupon payments
├── Monitors all transfers for compliance
├── Generates quarterly regulatory reports (PDF)
├── At maturity: redeems all tokens, returns principal, burns tokens
└── Every action logged to HCS (immutable audit trail)
```

## Architecture

### Agent Modules

| Agent | Responsibility |
|-------|---------------|
| **Compliance** | KYC whitelist management, transfer validation, jurisdiction rules (SEC Reg D/S, MiFID II) |
| **Lifecycle** | Token issuance, coupon distribution, NAV updates, maturity settlement |
| **Reporting** | Compliance report generation (PDF), audit trail compilation |
| **Chat** | Natural language interface powered by Claude API with tool use |

### Tech Stack

- **Backend**: Python / FastAPI / SQLite / APScheduler
- **Frontend**: Next.js 14 / TypeScript / TailwindCSS / shadcn/ui
- **Hedera**: HTS (tokens), HCS (audit logs), Mirror Node (queries)
- **AI**: Claude API (Anthropic) for chat agent + report generation
- **SDK**: hiero-sdk-python (native Python Hedera SDK)

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- Hedera testnet account ([portal.hedera.com](https://portal.hedera.com))
- Anthropic API key ([console.anthropic.com](https://console.anthropic.com))

### Setup

```bash
# Clone
git clone <repo-url> && cd lamina

# Backend
python -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt

# Frontend
cd frontend && npm install && cd ..

# Environment
cp .env.example .env
# Edit .env with your Hedera and Anthropic credentials
```

### Run

```bash
# Backend (terminal 1)
source venv/bin/activate
python -m uvicorn backend.main:app --reload --port 8000

# Frontend (terminal 2)
cd frontend && npm run dev
```

- Dashboard: http://localhost:3000
- Chat Agent: http://localhost:3000/chat
- API: http://localhost:8000/docs

## Demo Flow

1. **Issuance** — Chat: "Tokenize a $10M 5-year US Treasury bond, US accredited investors only"
2. **Whitelist** — Add investor to KYC whitelist
3. **Compliance Block** — Sanctioned country wallet gets blocked
4. **Coupon Payment** — Agent distributes interest to all holders
5. **NAV Update** — Agent pulls treasury rate, updates valuation
6. **Report** — Agent generates compliance report PDF
7. **Maturity** — Agent redeems tokens, burns supply, logs final settlement

## Hedera Integration

| Service | Usage |
|---------|-------|
| **HTS** | Token creation, minting, burning, transfers with KYC/freeze keys |
| **HCS** | Every agent action logged as immutable audit trail per asset |
| **Mirror Node** | Query HCS messages, verify token operations |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/assets` | List all tokenized assets |
| POST | `/api/assets` | Issue new asset |
| GET | `/api/assets/{id}` | Asset details |
| POST | `/api/assets/{id}/whitelist` | Add investor to whitelist |
| POST | `/api/assets/{id}/validate-transfer` | Check transfer compliance |
| POST | `/api/assets/{id}/distribute-coupon` | Distribute coupon payments |
| POST | `/api/assets/{id}/mature` | Execute maturity settlement |
| GET | `/api/assets/{id}/audit-log` | HCS audit trail |
| POST | `/api/assets/{id}/reports` | Generate compliance report |
| POST | `/api/chat` | Natural language agent interface |

## Project Structure

```
lamina/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── config.py             # Environment settings
│   ├── database.py           # SQLite schema + helpers
│   ├── hedera/
│   │   ├── client.py         # Hedera SDK client
│   │   ├── token.py          # HTS operations
│   │   └── consensus.py      # HCS audit logging
│   ├── agents/
│   │   ├── compliance.py     # KYC, whitelist, transfer validation
│   │   ├── lifecycle.py      # Issuance, coupons, maturity
│   │   ├── reporting.py      # PDF report generation
│   │   └── chat.py           # Claude-powered NL interface
│   ├── oracle/
│   │   ├── treasury_rates.py # US Treasury yield data
│   │   └── fx_rates.py       # Forex rates
│   └── scheduler/
│       └── jobs.py           # Automated coupon/NAV/maturity jobs
├── frontend/
│   ├── src/app/
│   │   ├── page.tsx          # Dashboard
│   │   ├── asset/[id]/       # Asset detail
│   │   └── chat/             # Chat interface
│   └── src/components/       # UI components
└── pitch/
    └── demo-script.md        # Demo walkthrough
```

## Hackathon

Built for the [Hedera Hello Future Apex Hackathon 2026](https://hackathon.stackup.dev/web/events/hedera-hello-future-apex-hackathon-2026-the-finale) — DeFi & Tokenization track.

## License

MIT
