# Lamina Architecture

Lamina is a **multi-chain autonomous RWA lifecycle backend**. A fund manager issues
one instruction; Lamina handles issuance, compliance, payouts, valuation, maturity,
and reporting across the chain the user selects — driven by an AI agent on top of a
clean service API.

## Principles

1. **Thin routes → stateless services → injected dependencies.** Routes only
   orchestrate (validate, call a service, shape the response). All business logic is
   in `services/`; services receive `db` and a `ChainAdapter`, never reach for globals.
2. **Chain-agnostic core.** Business logic (compliance rules, KYC, OFAC, payouts,
   reporting) never imports a chain SDK. It talks to the `ChainAdapter` interface.
3. **Config = secrets only.** `.env` holds keys, DB URL, environment. Public,
   structural chain config (RPCs, explorers, contract addresses) lives in
   `config/chains/*.toml`, loaded into a `ChainRegistry` at startup.
4. **Registry/handler patterns for extension.** New chain family → new adapter.
   New asset type → new handler. Drop a file, register, done.
5. **Audit everything.** Every state-changing agent action is written to the chain's
   audit log and mirrored in Postgres.

## Layers

```
HTTP → routes/ (thin) → services/ (logic) ─┬→ repositories/ (all SQL, SQLAlchemy)
                                           ├→ chains/ (ChainAdapter: settlement)
                                           ├→ handlers/ (asset-type strategy)
                                           └→ integrations/ (ofac, oracle)
```

- **routes/** — FastAPI routers, one per resource. No business logic.
- **services/** — issuance, compliance, payout, lifecycle, reporting, audit; `ai/` agent.
- **chains/** — `base.ChainAdapter` (family-agnostic interface), `registry.ChainRegistry`,
  `evm/` (one adapter parametrized per EVM chain), `solana/` (phase 2).
- **handlers/** — per-asset-type behavior (bond coupons vs equity dividends).
- **repositories/** — SQLAlchemy data access; services never write raw SQL inline.
- **models/** — Pydantic request/response schemas.
- **integrations/** — `ofac/` sanctions screening, `oracle/` price/yield feeds.
- **middleware/**, **utils/**, **constants/** — cross-cutting concerns, pure helpers, enums.

## Multi-chain

Every chain implements `ChainAdapter` (see `app/chains/base.py`): token lifecycle
(deploy/mint/burn/transfer/force-redeem), compliance (KYC/freeze), payouts
(USDC + native), and audit (topic/write/read). The interface speaks in opaque
`*_ref` strings, not EVM addresses, so a Solana adapter satisfies the same contract.

Chains are declared in `config/chains/<slug>.toml`:

```toml
name = "Robinhood Chain Testnet"
slug = "robinhood-testnet"
family = "evm"
chain_id = 46630
enabled = true
native_symbol = "ETH"
rpc_url = "https://rpc.testnet.chain.robinhood.com"
rpc_url_env = "RPC_URL_ROBINHOOD_TESTNET"   # optional private override
explorer_url = "https://explorer.testnet.chain.robinhood.com"
[contracts]
factory = "0x..."; audit_log = "0x..."; usdc = "0x..."
```

A chain is usable once `enabled = true` and its `factory` + `audit_log` are deployed.

## The 6 RWA functions

1. **Issue** — deploy a compliant asset token
2. **Onboard** — KYC + whitelist + OFAC screening
3. **Enforce transfer compliance** — jurisdiction rules, lockups, holder caps
4. **Distribute payout** — coupon/dividend in USDC or native
5. **Revalue (NAV)** — from a price/yield oracle
6. **Mature/redeem** — return principal + burn

Plus cross-cutting **audit trail & reporting**.

## Tech stack

FastAPI · Pydantic v2 · SQLAlchemy 2.0 async + asyncpg + Alembic · web3.py (EVM) ·
Anthropic (AI) · APScheduler (jobs) · Postgres.

## Roadmap

- **Now:** EVM multi-chain backend (testnet), USDC/ETH payouts, AI agent.
- **Next:** MCP server (other agents connect), Telegram + WhatsApp control channels.
- **Later:** Solana adapter, frontend.

See `docs/memory/` for the living decision log.
