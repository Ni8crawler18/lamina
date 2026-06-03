# Database (Postgres only)

SQLAlchemy 2.0 async + asyncpg + Alembic. No SQLite — the old dual wrapper is gone.

## Layout
- `app/database.py` — async engine, `async_sessionmaker`, `Base`, `get_session`
  (FastAPI dependency, commits/rolls back per request), `ping()`.
- `app/models/orm.py` — ORM tables. **`assets.chain`** (slug) is the multi-chain
  field; holders/events/audit/reports/screening join via `asset_id`.
- `app/repositories/` — one repository per aggregate; **all SQL lives here**, services
  never write inline queries.

## Multi-chain schema change vs old `server/`
- added `assets.chain` (indexed)
- renamed audit `hcs_sequence_number`/`hcs_timestamp` → `onchain_sequence`/`onchain_timestamp`
- int-flags → real Booleans (whitelisted, kyc_granted, token_associated, is_match)

## Local workflow
```bash
docker compose up -d                 # Postgres on host :5433
cd backend
alembic revision --autogenerate -m "msg"   # after editing app/models/orm.py
alembic upgrade head                 # apply
```
`DATABASE_URL` (async, `postgresql+asyncpg://…`) is read from `.env` by `app.config`
and injected into Alembic in `migrations/env.py` — it is NOT in `alembic.ini`.

## Gotchas
- Editing ORM models requires a new migration; don't hand-edit the DB.
- `get_session` auto-commits on success; repositories use `flush()` (not commit) so
  the request-scoped transaction stays in the service's control.
