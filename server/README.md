# Lamina - chain architecture

Multi-chain autonomous RWA lifecycle backend. FastAPI · SQLAlchemy 2.0 (async) ·
Postgres · web3 (EVM) + Hedera · Anthropic AI agent.

See [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) for the design.

## Quick start

```bash
# 1. Infra (Postgres on host :5433)
docker compose up -d                       # from repo root

# 2. Python deps
python -m venv venv && source venv/bin/activate
pip install -e server[dev]                 # or: pip install -r server/requirements.txt

# 3. Config
cp server/.env.sample server/.env          # fill DEPLOYER_PRIVATE_KEY, OPERATOR_ADDRESS,
                                           # ANTHROPIC_API_KEY (+ HEDERA_* if using Hedera)

# 4. Run (from server/) — tables auto-create on startup
cd server && PYTHONPATH=. uvicorn app.main:app --reload --port 8001
```

Open http://localhost:8001/health and http://localhost:8001/docs.

## Layout

```
app/
  main.py            app + lifespan + router registration
  config.py          settings (secrets/env only)
  database.py        async engine + session + Base (create_tables() at startup)
  routes/            thin HTTP handlers
  services/          business logic (chain-agnostic) + services/ai (agent)
  chains/            ChainAdapter interface + registry + evm/ hedera/ adapters
  handlers/          per-asset-type strategy (bond/equity/fund)
  repositories/      all SQL (SQLAlchemy)
  models/            pydantic schemas + orm.py (tables)
  integrations/      ofac/, oracle/
  middleware/ utils/ constants/
config/chains/       one TOML per chain (non-secret)
```

## Adding a chain

Drop a TOML in `config/chains/`, deploy the contracts (EVM), set `enabled = true`.
See [`../docs/memory/chain-config.md`](../docs/memory/chain-config.md). No code change for EVM chains.

## Database

Schema is created from the ORM at startup (`create_tables()` — idempotent). There's no
migration tool yet; reintroduce Alembic when the schema needs versioned migrations.

## Tests

```bash
cd server && PYTHONPATH=. pytest           # offline: chain config + adapter conformance
```
