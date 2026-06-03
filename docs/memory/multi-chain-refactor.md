# Multi-chain refactor

## Why
The original backend (`server/`) was single-chain: `agents/lifecycle.py` and
`agents/compliance.py` imported `server.arbitrum.*` directly, so adding a chain meant
rewriting business logic. We're reshaping into a clean, professional, multi-chain
backend modeled on the `meru` codebase's conventions.

## Decisions (2026-06-03)
- **Scope v1:** EVM multi-chain (Robinhood live; Ethereum Sepolia, Polygon Amoy,
  Arbitrum Sepolia, Base Sepolia, Avalanche Fuji scaffolded). **Hedera** kept as a
  first-class non-EVM family (ports existing `server/hedera/`). **Solana** = phase 2.
- **DB:** Postgres only (drop SQLite), SQLAlchemy 2.0 async + Alembic.
- **Chain config:** per-chain TOML in `config/chains/`, loaded into `ChainRegistry`;
  `.env` holds secrets only.
- **Restructure:** full move to `backend/app/` (meru layout). The old `server/`
  stays runnable until `backend/` is verified — **do not break Robinhood or Hedera.**

## Key design
- `app/chains/base.py::ChainAdapter` — family-agnostic interface (opaque `*_ref`
  strings, not addresses). EVM and Hedera both implement it; Solana later.
- `app/chains/registry.py::ChainRegistry` — loads TOMLs, resolves adapter by family.
- Services depend on `ChainAdapter`, never on a chain SDK.

## Migration phases
0. Foundation (skeleton, config, registry, docs) — **done**
1. Chain adapters: EVM + Hedera — **done** (EVM live-verified write+read on Robinhood;
   Hedera conformance + live mirror-node read; `tests/test_chains.py` green)
2. Data layer: SQLAlchemy models (+`chain` column), repositories, Alembic — **done**
   (Postgres :5433, initial migration applied, CRUD round-trip verified)
3. Services: port `agents/` → `services/` + handlers + integrations — **done**
   (e2e issue→whitelist→purchase→coupon→maturity verified on Postgres + live Robinhood)
4. API + AI agent + scheduler + middleware — **done** (booted :8001, full HTTP e2e
   incl. AI chat + report download + on-chain audit readback)
5. Verify end-to-end on Postgres across Robinhood + ≥1 other

## Safety
- `server/` is the working reference; keep it running until `backend/` passes the
  same end-to-end tests on Robinhood **and** Hedera.
- Both `.env` files are gitignored; the Anthropic key surfaced in-session should be
  rotated.
