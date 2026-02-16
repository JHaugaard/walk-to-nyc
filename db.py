import sqlite3
from config import DB_PATH

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('walker', 'admin')),
    token_hash TEXT NOT NULL UNIQUE,
    route_origin_address TEXT,
    route_dest_address TEXT,
    route_total_miles REAL CHECK (route_total_miles > 0),
    seed_miles REAL NOT NULL DEFAULT 0 CHECK (seed_miles >= 0),
    emoji_descriptor TEXT,
    setup_complete INTEGER NOT NULL DEFAULT 0 CHECK (setup_complete IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (datetime('now', '-5 hours'))
);

CREATE TABLE IF NOT EXISTS daily_entry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    miles REAL NOT NULL CHECK (miles >= 0),
    created_at TEXT NOT NULL DEFAULT (datetime('now', '-5 hours')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', '-5 hours')),
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_entry_user_date
    ON daily_entry(user_id, date);

CREATE TABLE IF NOT EXISTS waypoint (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    mile_marker REAL NOT NULL CHECK (mile_marker > 0),
    display_order INTEGER NOT NULL,
    selected INTEGER NOT NULL DEFAULT 1 CHECK (selected IN (0, 1)),
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_waypoint_user_selected
    ON waypoint(user_id, selected);

CREATE VIEW IF NOT EXISTS user_progress AS
SELECT
    u.id AS user_id,
    u.name,
    u.emoji_descriptor,
    u.route_origin_address,
    u.route_total_miles,
    u.seed_miles,
    COALESCE(SUM(de.miles), 0) AS logged_miles,
    u.seed_miles + COALESCE(SUM(de.miles), 0) AS total_miles,
    CASE
        WHEN u.route_total_miles > 0
        THEN ROUND((u.seed_miles + COALESCE(SUM(de.miles), 0)) / u.route_total_miles * 100, 1)
        ELSE 0
    END AS percent_complete,
    COALESCE(COUNT(CASE WHEN de.miles > 0 THEN 1 END), 0) AS days_active,
    MAX(de.date) AS last_entry_date
FROM user u
LEFT JOIN daily_entry de ON u.id = de.user_id
WHERE u.role = 'walker'
GROUP BY u.id;

CREATE VIEW IF NOT EXISTS waypoints_passed AS
SELECT
    w.user_id,
    w.name,
    w.mile_marker,
    w.display_order,
    CASE
        WHEN (u.seed_miles + COALESCE(logged.total, 0)) >= w.mile_marker THEN 1
        ELSE 0
    END AS passed
FROM waypoint w
JOIN user u ON w.user_id = u.id
LEFT JOIN (
    SELECT user_id, SUM(miles) AS total
    FROM daily_entry
    GROUP BY user_id
) logged ON w.user_id = logged.user_id
WHERE w.selected = 1
ORDER BY w.user_id, w.display_order;

CREATE VIEW IF NOT EXISTS recent_entries AS
SELECT
    id,
    user_id,
    date,
    miles,
    CASE
        WHEN date >= date('now', '-5 hours', '-7 days') THEN 1
        ELSE 0
    END AS editable
FROM daily_entry
ORDER BY date DESC;
"""


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_schema():
    conn = get_db()
    conn.executescript(SCHEMA_SQL)
    conn.close()
