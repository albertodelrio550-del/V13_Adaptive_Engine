# ============================================================
# V13 Session Audit Database Initializer
# Build_ID: V13.2025.10.20.01
# Creates the SQLite schema for the telemetry audit system.
# ============================================================

import sqlite3, os, datetime

DB_PATH = "../logs/Session_Audit_Log.db"

if not os.path.exists("../logs"):
    os.makedirs("../logs")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.executescript("""
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE,
    commander_name TEXT,
    operator_handle TEXT,
    mode TEXT,
    start_time TEXT,
    end_time TEXT,
    profit_usd REAL DEFAULT 0,
    drawdown_usd REAL DEFAULT 0,
    status TEXT DEFAULT 'ACTIVE'
);

CREATE TABLE IF NOT EXISTS telemetry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    symbol TEXT,
    price REAL,
    volume REAL,
    spread REAL,
    latency_ms INTEGER,
    source TEXT,
    checksum TEXT
);

CREATE TABLE IF NOT EXISTS performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    profit_usd REAL,
    ladder_level TEXT,
    locked_profit REAL,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS risk_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    event_type TEXT,
    details TEXT,
    drawdown REAL,
    action_taken TEXT
);

CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    module TEXT,
    level TEXT,
    message TEXT
);
""")

conn.commit()
conn.close()

print(f"[OK] Audit database initialized at {DB_PATH}")
print("Tables: sessions | telemetry | performance | risk_events | system_logs")
