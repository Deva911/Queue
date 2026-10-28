"""SQLite connection and schema.

Every business-owned table has a business_id. Child tables point at their parent with a
composite (business_id, id) foreign key, so the database itself refuses, for example, an
appointment for business A that uses a service belonging to business B.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS businesses (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL CHECK (length(trim(name)) > 0),
    category      TEXT,
    address       TEXT,
    contact_email TEXT,
    timezone      TEXT NOT NULL,
    logo_url      TEXT,
    payment_info  TEXT,
    status        TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'INACTIVE')),
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS services (
    id               TEXT PRIMARY KEY,
    business_id      TEXT NOT NULL REFERENCES businesses(id),
    name             TEXT NOT NULL CHECK (length(trim(name)) > 0),
    description      TEXT,
    price_minor      INTEGER CHECK (price_minor IS NULL OR price_minor >= 0),
    currency         TEXT,
    duration_minutes INTEGER CHECK (duration_minutes IS NULL OR duration_minutes > 0),
    is_active        INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL,
    CHECK (price_minor IS NULL OR currency IS NOT NULL),
    UNIQUE (business_id, id)
);

CREATE TABLE IF NOT EXISTS business_hours (
    business_id TEXT NOT NULL REFERENCES businesses(id),
    weekday     INTEGER NOT NULL CHECK (weekday BETWEEN 0 AND 6),
    opens_at    TEXT,
    closes_at   TEXT,
    is_closed   INTEGER NOT NULL DEFAULT 0 CHECK (is_closed IN (0, 1)),
    PRIMARY KEY (business_id, weekday)
);

CREATE TABLE IF NOT EXISTS customers (
    id                    TEXT PRIMARY KEY,
    business_id           TEXT NOT NULL REFERENCES businesses(id),
    external_customer_key TEXT NOT NULL,
    display_name          TEXT,
    consent_status        TEXT NOT NULL DEFAULT 'UNKNOWN',
    created_at            TEXT NOT NULL,
    updated_at            TEXT NOT NULL,
    UNIQUE (business_id, external_customer_key),
    UNIQUE (business_id, id)
);

CREATE TABLE IF NOT EXISTS conversations (
    id              TEXT PRIMARY KEY,
    business_id     TEXT NOT NULL,
    customer_id     TEXT NOT NULL,
    state           TEXT NOT NULL,
    status          TEXT NOT NULL,
    context_json    TEXT NOT NULL DEFAULT '{}',
    last_message_at TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    FOREIGN KEY (business_id, customer_id) REFERENCES customers(business_id, id),
    UNIQUE (business_id, id)
);

CREATE TABLE IF NOT EXISTS messages (
    id              TEXT PRIMARY KEY,
    business_id     TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    direction       TEXT NOT NULL CHECK (direction IN ('INBOUND', 'OUTBOUND')),
    sender          TEXT NOT NULL CHECK (sender IN ('CUSTOMER', 'BOT', 'STAFF')),
    body            TEXT NOT NULL,
    delivery_status TEXT NOT NULL DEFAULT 'SIMULATED',
    created_at      TEXT NOT NULL,
    FOREIGN KEY (business_id, conversation_id) REFERENCES conversations(business_id, id)
);

CREATE TABLE IF NOT EXISTS leads (
    id          TEXT PRIMARY KEY,
    business_id TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    service_id  TEXT,
    name        TEXT,
    enquiry     TEXT NOT NULL,
    status      TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    FOREIGN KEY (business_id, customer_id) REFERENCES customers(business_id, id),
    FOREIGN KEY (business_id, service_id) REFERENCES services(business_id, id)
);

CREATE TABLE IF NOT EXISTS appointment_requests (
    id                 TEXT PRIMARY KEY,
    business_id        TEXT NOT NULL,
    customer_id        TEXT NOT NULL,
    service_id         TEXT NOT NULL,
    requested_start_at TEXT NOT NULL,
    notes              TEXT,
    reschedule_of      TEXT,
    status             TEXT NOT NULL DEFAULT 'PENDING',
    staff_note         TEXT,
    created_at         TEXT NOT NULL,
    updated_at         TEXT NOT NULL,
    FOREIGN KEY (business_id, customer_id) REFERENCES customers(business_id, id),
    FOREIGN KEY (business_id, service_id) REFERENCES services(business_id, id)
);

CREATE TABLE IF NOT EXISTS audit_events (
    id           TEXT PRIMARY KEY,
    business_id  TEXT NOT NULL REFERENCES businesses(id),
    actor        TEXT NOT NULL,
    event_type   TEXT NOT NULL,
    entity_type  TEXT NOT NULL,
    entity_id    TEXT,
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_services_business ON services(business_id);
CREATE INDEX IF NOT EXISTS idx_conversations_business ON conversations(business_id, status);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(business_id, conversation_id);
CREATE INDEX IF NOT EXISTS idx_leads_business ON leads(business_id);
CREATE INDEX IF NOT EXISTS idx_appointments_business ON appointment_requests(business_id, status);
CREATE INDEX IF NOT EXISTS idx_audit_business ON audit_events(business_id, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(business_id, created_at);
"""

# Bump when the schema changes, and add the upgrade step in connect(), so existing databases
# are upgraded in place instead of being thrown away.
SCHEMA_VERSION = 2


def connect(path: str | Path) -> sqlite3.Connection:
    """Open the database (creating the file and tables if needed)."""
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if str(path) != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL")  # readers don't block the writer (several browser tabs)
    conn.executescript(SCHEMA)
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    return conn
