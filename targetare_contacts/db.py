from __future__ import annotations

import sqlite3

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    tax_id TEXT NOT NULL UNIQUE,
    original_address TEXT,
    source_row INTEGER NOT NULL,
    primary_email TEXT,
    secondary_email TEXT,
    contact_email TEXT,
    website_emails TEXT,
    primary_phone TEXT,
    secondary_phone TEXT,
    contact_phones TEXT,
    website_phones TEXT,
    verified_phones TEXT,
    lookup_status TEXT NOT NULL DEFAULT 'not_queried',
    error_message TEXT,
    remaining_requests INTEGER,
    queried_at TEXT
);
"""


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_error: BaseException | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = get_db()
    db.executescript(SCHEMA)
    db.commit()
