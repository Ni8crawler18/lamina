import os
import re
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")
USE_POSTGRES = DATABASE_URL.startswith("postgres")
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "lamina.db")


def _convert_placeholders(sql: str) -> str:
    """Convert SQLite ? placeholders to PostgreSQL $1, $2, ... format."""
    counter = [0]
    def replacer(match):
        counter[0] += 1
        return f'${counter[0]}'
    return re.sub(r'\?', replacer, sql)


def _convert_sql_for_pg(sql: str) -> str:
    """Convert SQLite-specific SQL to PostgreSQL."""
    sql = _convert_placeholders(sql)
    sql = sql.replace("datetime('now')", "NOW()::TEXT")
    return sql


# ─── PostgreSQL Schema ──────────────────────────────────

PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS assets (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    symbol TEXT NOT NULL,
    token_id TEXT,
    topic_id TEXT,
    asset_type TEXT NOT NULL DEFAULT 'bond',
    total_supply INTEGER NOT NULL,
    decimals INTEGER NOT NULL DEFAULT 2,
    coupon_rate REAL DEFAULT 0.0,
    maturity_date TEXT,
    nav REAL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'active',
    jurisdiction TEXT NOT NULL DEFAULT 'US',
    investor_type TEXT NOT NULL DEFAULT 'accredited',
    created_at TEXT NOT NULL DEFAULT (NOW()::TEXT)
);

CREATE TABLE IF NOT EXISTS holders (
    id SERIAL PRIMARY KEY,
    account_id TEXT NOT NULL,
    private_key TEXT,
    asset_id INTEGER NOT NULL REFERENCES assets(id),
    balance INTEGER NOT NULL DEFAULT 0,
    kyc_status TEXT NOT NULL DEFAULT 'pending',
    jurisdiction TEXT DEFAULT 'US',
    investor_type TEXT DEFAULT 'accredited',
    whitelisted INTEGER NOT NULL DEFAULT 0,
    token_associated INTEGER NOT NULL DEFAULT 0,
    kyc_granted INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (NOW()::TEXT),
    name TEXT,
    ofac_status TEXT DEFAULT 'pending',
    ofac_screened_at TEXT,
    UNIQUE(account_id, asset_id)
);

CREATE TABLE IF NOT EXISTS scheduled_events (
    id SERIAL PRIMARY KEY,
    asset_id INTEGER NOT NULL REFERENCES assets(id),
    event_type TEXT NOT NULL,
    scheduled_at TEXT NOT NULL,
    executed_at TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    tx_hash TEXT,
    details TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    asset_id INTEGER,
    action TEXT NOT NULL,
    agent TEXT NOT NULL,
    details TEXT,
    hcs_sequence_number INTEGER,
    hcs_timestamp TEXT,
    created_at TEXT NOT NULL DEFAULT (NOW()::TEXT)
);

CREATE TABLE IF NOT EXISTS reports (
    id SERIAL PRIMARY KEY,
    asset_id INTEGER NOT NULL REFERENCES assets(id),
    report_type TEXT NOT NULL,
    period TEXT,
    file_path TEXT,
    generated_at TEXT NOT NULL DEFAULT (NOW()::TEXT)
);

CREATE TABLE IF NOT EXISTS screening_results (
    id SERIAL PRIMARY KEY,
    holder_account_id TEXT,
    holder_name TEXT,
    asset_id INTEGER,
    is_match INTEGER NOT NULL DEFAULT 0,
    score REAL DEFAULT 0,
    match_type TEXT,
    matched_name TEXT,
    matched_program TEXT,
    action_taken TEXT NOT NULL DEFAULT 'clear',
    screened_at TEXT NOT NULL DEFAULT (NOW()::TEXT)
);
"""

# ─── SQLite Schema ──────────────────────────────────────

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    symbol TEXT NOT NULL,
    token_id TEXT,
    topic_id TEXT,
    asset_type TEXT NOT NULL DEFAULT 'bond',
    total_supply INTEGER NOT NULL,
    decimals INTEGER NOT NULL DEFAULT 2,
    coupon_rate REAL DEFAULT 0.0,
    maturity_date TEXT,
    nav REAL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'active',
    jurisdiction TEXT NOT NULL DEFAULT 'US',
    investor_type TEXT NOT NULL DEFAULT 'accredited',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS holders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL,
    private_key TEXT,
    asset_id INTEGER NOT NULL,
    balance INTEGER NOT NULL DEFAULT 0,
    kyc_status TEXT NOT NULL DEFAULT 'pending',
    jurisdiction TEXT DEFAULT 'US',
    investor_type TEXT DEFAULT 'accredited',
    whitelisted INTEGER NOT NULL DEFAULT 0,
    token_associated INTEGER NOT NULL DEFAULT 0,
    kyc_granted INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    name TEXT,
    ofac_status TEXT DEFAULT 'pending',
    ofac_screened_at TEXT,
    FOREIGN KEY (asset_id) REFERENCES assets(id),
    UNIQUE(account_id, asset_id)
);

CREATE TABLE IF NOT EXISTS scheduled_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    scheduled_at TEXT NOT NULL,
    executed_at TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    tx_hash TEXT,
    details TEXT,
    FOREIGN KEY (asset_id) REFERENCES assets(id)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER,
    action TEXT NOT NULL,
    agent TEXT NOT NULL,
    details TEXT,
    hcs_sequence_number INTEGER,
    hcs_timestamp TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL,
    report_type TEXT NOT NULL,
    period TEXT,
    file_path TEXT,
    generated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (asset_id) REFERENCES assets(id)
);

CREATE TABLE IF NOT EXISTS screening_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    holder_account_id TEXT,
    holder_name TEXT,
    asset_id INTEGER,
    is_match INTEGER NOT NULL DEFAULT 0,
    score REAL DEFAULT 0,
    match_type TEXT,
    matched_name TEXT,
    matched_program TEXT,
    action_taken TEXT NOT NULL DEFAULT 'clear',
    screened_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


# ─── PostgreSQL Database Class ──────────────────────────

_pg_pool = None


async def _init_pg_pool():
    global _pg_pool
    if _pg_pool is None:
        import asyncpg
        _pg_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    return _pg_pool


class PgDatabase:
    """asyncpg wrapper with SQLite-compatible interface."""

    def __init__(self, conn):
        self._conn = conn
        self._lastrowid = None

    async def execute(self, sql: str, params=None):
        sql = _convert_sql_for_pg(sql)
        args = tuple(params) if params else ()
        is_insert = sql.strip().upper().startswith("INSERT")
        if is_insert and "RETURNING" not in sql.upper():
            sql = sql.rstrip().rstrip(";") + " RETURNING id"
            try:
                row = await self._conn.fetchrow(sql, *args)
                if row:
                    self._lastrowid = row["id"]
                return self
            except Exception:
                sql = sql.rsplit(" RETURNING id", 1)[0]
                await self._conn.execute(sql, *args)
                return self
        await self._conn.execute(sql, *args)
        return self

    async def execute_fetchone(self, sql: str, params=None):
        sql = _convert_sql_for_pg(sql)
        args = tuple(params) if params else ()
        return await self._conn.fetchrow(sql, *args)

    async def execute_fetchall(self, sql: str, params=None):
        sql = _convert_sql_for_pg(sql)
        args = tuple(params) if params else ()
        return await self._conn.fetch(sql, *args)

    async def executescript(self, sql: str):
        await self._conn.execute(sql)

    async def commit(self):
        pass  # asyncpg auto-commits

    async def close(self):
        global _pg_pool
        if _pg_pool:
            await _pg_pool.release(self._conn)

    @property
    def lastrowid(self):
        return self._lastrowid


# ─── SQLite Database Class ──────────────────────────────

class SqliteDatabase:
    """Thin wrapper around aiosqlite."""

    def __init__(self, conn):
        self._conn = conn

    async def execute(self, sql: str, params=None):
        if params:
            return await self._conn.execute(sql, params)
        return await self._conn.execute(sql)

    async def execute_fetchone(self, sql: str, params=None):
        cursor = await self.execute(sql, params)
        return await cursor.fetchone()

    async def execute_fetchall(self, sql: str, params=None):
        cursor = await self.execute(sql, params)
        return await cursor.fetchall()

    async def executescript(self, sql: str):
        return await self._conn.executescript(sql)

    async def commit(self):
        return await self._conn.commit()

    async def close(self):
        return await self._conn.close()

    @property
    def lastrowid(self):
        return self._conn._conn.cursor().lastrowid if hasattr(self._conn, '_conn') else None


# ─── Public API ─────────────────────────────────────────

async def get_db():
    if USE_POSTGRES:
        pool = await _init_pg_pool()
        conn = await pool.acquire()
        return PgDatabase(conn)
    else:
        import aiosqlite
        conn = await aiosqlite.connect(DB_PATH)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA foreign_keys=ON")
        return SqliteDatabase(conn)


async def init_db():
    if USE_POSTGRES:
        pool = await _init_pg_pool()
        async with pool.acquire() as conn:
            await conn.execute(PG_SCHEMA)
        logger.info("PostgreSQL database initialized")
    else:
        db = await get_db()
        try:
            await db.executescript(SQLITE_SCHEMA)
            await db.commit()
            for col, typedef in [
                ("name", "TEXT"),
                ("ofac_status", "TEXT DEFAULT 'pending'"),
                ("ofac_screened_at", "TEXT"),
            ]:
                try:
                    await db.execute(f"ALTER TABLE holders ADD COLUMN {col} {typedef}")
                    await db.commit()
                except Exception:
                    pass
        finally:
            await db.close()
        logger.info("SQLite database initialized")
