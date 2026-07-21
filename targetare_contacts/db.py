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

CREATE TABLE IF NOT EXISTS contact_cache (
    tax_id TEXT PRIMARY KEY,
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

CREATE TABLE IF NOT EXISTS lookup_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tax_id TEXT NOT NULL,
    emails_json TEXT,
    phones_json TEXT,
    lookup_status TEXT NOT NULL,
    error_message TEXT,
    remaining_requests INTEGER,
    queried_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_lookup_history_tax_id
ON lookup_history (tax_id, id DESC);
"""

CACHE_COLUMNS = (
    "primary_email",
    "secondary_email",
    "contact_email",
    "website_emails",
    "primary_phone",
    "secondary_phone",
    "contact_phones",
    "website_phones",
    "verified_phones",
    "lookup_status",
    "error_message",
    "remaining_requests",
    "queried_at",
)


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

    # Preserve results created by versions released before contact_cache existed.
    db.execute(
        """
        INSERT OR IGNORE INTO contact_cache (
            tax_id,
            primary_email,
            secondary_email,
            contact_email,
            website_emails,
            primary_phone,
            secondary_phone,
            contact_phones,
            website_phones,
            verified_phones,
            lookup_status,
            error_message,
            remaining_requests,
            queried_at
        )
        SELECT
            tax_id,
            primary_email,
            secondary_email,
            contact_email,
            website_emails,
            primary_phone,
            secondary_phone,
            contact_phones,
            website_phones,
            verified_phones,
            lookup_status,
            error_message,
            remaining_requests,
            queried_at
        FROM companies
        WHERE
            lookup_status <> 'not_queried'
            OR primary_email IS NOT NULL
            OR secondary_email IS NOT NULL
            OR contact_email IS NOT NULL
            OR website_emails IS NOT NULL
            OR primary_phone IS NOT NULL
            OR secondary_phone IS NOT NULL
            OR contact_phones IS NOT NULL
            OR website_phones IS NOT NULL
            OR verified_phones IS NOT NULL
        """
    )
    db.commit()
