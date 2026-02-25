import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "lamina.db")

SCHEMA = """
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
"""


class Database:
    """Thin wrapper around aiosqlite with fetchone/fetchall helpers."""

    def __init__(self, conn: aiosqlite.Connection):
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


async def get_db() -> Database:
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA foreign_keys=ON")
    return Database(conn)


async def init_db():
    db = await get_db()
    try:
        await db.executescript(SCHEMA)
        await db.commit()
    finally:
        await db.close()
