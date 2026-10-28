"""All SQL lives here.

Every function that touches business-owned data takes a business_id and filters on it,
so the bot, services and screens never write SQL and can't forget the tenant filter.
Phase 2 can swap this module for a Supabase version without touching the layers above.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Iterable

Row = dict[str, Any]


def new_id() -> str:
    return str(uuid.uuid4())


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _one(cur: sqlite3.Cursor) -> Row | None:
    row = cur.fetchone()
    return dict(row) if row else None


def _all(cur: sqlite3.Cursor) -> list[Row]:
    return [dict(r) for r in cur.fetchall()]


def _update(conn: sqlite3.Connection, table: str, business_id: str, record_id: str,
            fields: dict[str, Any], id_column: str = "id") -> int:
    if not fields:
        return 0
    fields = {**fields, "updated_at": utc_now()}
    assignments = ", ".join(f"{name} = ?" for name in fields)  # names come from code, never users
    cur = conn.execute(
        f"UPDATE {table} SET {assignments} WHERE business_id = ? AND {id_column} = ?",
        [*fields.values(), business_id, record_id],
    )
    return cur.rowcount


# ---------- businesses ----------

def insert_business(conn: sqlite3.Connection, *, name: str, category: str | None, address: str | None,
                    contact_email: str | None, timezone_name: str, logo_url: str | None,
                    payment_info: str | None, status: str) -> str:
    business_id, now = new_id(), utc_now()
    conn.execute(
        "INSERT INTO businesses (id, name, category, address, contact_email, timezone, logo_url,"
        " payment_info, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (business_id, name, category, address, contact_email, timezone_name, logo_url,
         payment_info, status, now, now),
    )
    return business_id


def get_business(conn: sqlite3.Connection, business_id: str) -> Row | None:
    return _one(conn.execute("SELECT * FROM businesses WHERE id = ?", (business_id,)))


def list_businesses(conn: sqlite3.Connection) -> list[Row]:
    return _all(conn.execute("SELECT * FROM businesses ORDER BY name"))


def update_business(conn: sqlite3.Connection, business_id: str, fields: dict[str, Any]) -> int:
    if not fields:
        return 0
    fields = {**fields, "updated_at": utc_now()}
    assignments = ", ".join(f"{name} = ?" for name in fields)
    cur = conn.execute(f"UPDATE businesses SET {assignments} WHERE id = ?", [*fields.values(), business_id])
    return cur.rowcount


# ---------- business hours ----------

def upsert_hours(conn: sqlite3.Connection, business_id: str, weekday: int, opens_at: str | None,
                 closes_at: str | None, is_closed: bool) -> None:
    conn.execute(
        "INSERT INTO business_hours (business_id, weekday, opens_at, closes_at, is_closed)"
        " VALUES (?, ?, ?, ?, ?) ON CONFLICT (business_id, weekday) DO UPDATE SET"
        " opens_at = excluded.opens_at, closes_at = excluded.closes_at, is_closed = excluded.is_closed",
        (business_id, weekday, opens_at, closes_at, int(is_closed)),
    )


def list_hours(conn: sqlite3.Connection, business_id: str) -> list[Row]:
    return _all(conn.execute(
        "SELECT * FROM business_hours WHERE business_id = ? ORDER BY weekday", (business_id,)))


# ---------- services ----------

def insert_service(conn: sqlite3.Connection, business_id: str, *, name: str, description: str | None,
                   price_minor: int | None, currency: str | None, duration_minutes: int | None,
                   is_active: bool = True) -> str:
    service_id, now = new_id(), utc_now()
    conn.execute(
        "INSERT INTO services (id, business_id, name, description, price_minor, currency,"
        " duration_minutes, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (service_id, business_id, name, description, price_minor, currency, duration_minutes,
         int(is_active), now, now),
    )
    return service_id


def get_service(conn: sqlite3.Connection, business_id: str, service_id: str) -> Row | None:
    return _one(conn.execute(
        "SELECT * FROM services WHERE business_id = ? AND id = ?", (business_id, service_id)))


def list_services(conn: sqlite3.Connection, business_id: str, *, active_only: bool = False) -> list[Row]:
    sql = "SELECT * FROM services WHERE business_id = ?"
    if active_only:
        sql += " AND is_active = 1"
    return _all(conn.execute(sql + " ORDER BY name", (business_id,)))


def update_service(conn: sqlite3.Connection, business_id: str, service_id: str, fields: dict[str, Any]) -> int:
    return _update(conn, "services", business_id, service_id, fields)


# ---------- customers ----------

def get_customer_by_key(conn: sqlite3.Connection, business_id: str, key: str) -> Row | None:
    return _one(conn.execute(
        "SELECT * FROM customers WHERE business_id = ? AND external_customer_key = ?", (business_id, key)))


def get_customer(conn: sqlite3.Connection, business_id: str, customer_id: str) -> Row | None:
    return _one(conn.execute(
        "SELECT * FROM customers WHERE business_id = ? AND id = ?", (business_id, customer_id)))


def insert_customer(conn: sqlite3.Connection, business_id: str, key: str) -> str:
    customer_id, now = new_id(), utc_now()
    conn.execute(
        "INSERT INTO customers (id, business_id, external_customer_key, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (customer_id, business_id, key, now, now),
    )
    return customer_id


def update_customer(conn: sqlite3.Connection, business_id: str, customer_id: str, fields: dict[str, Any]) -> int:
    return _update(conn, "customers", business_id, customer_id, fields)


# ---------- conversations and messages ----------

def get_open_conversation(conn: sqlite3.Connection, business_id: str, customer_id: str) -> Row | None:
    return _one(conn.execute(
        "SELECT * FROM conversations WHERE business_id = ? AND customer_id = ? AND status != 'CLOSED'"
        " ORDER BY created_at DESC LIMIT 1",
        (business_id, customer_id),
    ))


def get_conversation(conn: sqlite3.Connection, business_id: str, conversation_id: str) -> Row | None:
    return _one(conn.execute(
        "SELECT * FROM conversations WHERE business_id = ? AND id = ?", (business_id, conversation_id)))


def insert_conversation(conn: sqlite3.Connection, business_id: str, customer_id: str, state: str,
                        status: str) -> str:
    conversation_id, now = new_id(), utc_now()
    conn.execute(
        "INSERT INTO conversations (id, business_id, customer_id, state, status, context_json,"
        " created_at, updated_at) VALUES (?, ?, ?, ?, ?, '{}', ?, ?)",
        (conversation_id, business_id, customer_id, state, status, now, now),
    )
    return conversation_id


def update_conversation(conn: sqlite3.Connection, business_id: str, conversation_id: str,
                        fields: dict[str, Any]) -> int:
    if "context" in fields:
        fields = {**fields}
        fields["context_json"] = json.dumps(fields.pop("context"))
    return _update(conn, "conversations", business_id, conversation_id, fields)


def list_conversations(conn: sqlite3.Connection, business_id: str,
                       statuses: Iterable[str] | None = None) -> list[Row]:
    sql = ("SELECT c.*, cu.external_customer_key, cu.display_name FROM conversations c"
           " JOIN customers cu ON cu.business_id = c.business_id AND cu.id = c.customer_id"
           " WHERE c.business_id = ?")
    params: list[Any] = [business_id]
    if statuses is not None:
        statuses = list(statuses)
        sql += f" AND c.status IN ({', '.join('?' for _ in statuses)})"
        params += statuses
    return _all(conn.execute(sql + " ORDER BY c.last_message_at DESC", params))


def insert_message(conn: sqlite3.Connection, business_id: str, conversation_id: str, direction: str,
                   sender: str, body: str) -> str:
    message_id, now = new_id(), utc_now()
    conn.execute(
        "INSERT INTO messages (id, business_id, conversation_id, direction, sender, body, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (message_id, business_id, conversation_id, direction, sender, body, now),
    )
    conn.execute(
        "UPDATE conversations SET last_message_at = ? WHERE business_id = ? AND id = ?",
        (now, business_id, conversation_id),
    )
    return message_id


def list_messages(conn: sqlite3.Connection, business_id: str, conversation_id: str) -> list[Row]:
    return _all(conn.execute(
        "SELECT * FROM messages WHERE business_id = ? AND conversation_id = ? ORDER BY created_at, rowid",
        (business_id, conversation_id),
    ))


# ---------- leads ----------

def insert_lead(conn: sqlite3.Connection, business_id: str, customer_id: str, *, service_id: str | None,
                name: str | None, enquiry: str, status: str) -> str:
    lead_id, now = new_id(), utc_now()
    conn.execute(
        "INSERT INTO leads (id, business_id, customer_id, service_id, name, enquiry, status, created_at,"
        " updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (lead_id, business_id, customer_id, service_id, name, enquiry, status, now, now),
    )
    return lead_id


def find_open_lead(conn: sqlite3.Connection, business_id: str, customer_id: str,
                   service_id: str | None) -> Row | None:
    """The customer's newest lead for this service (or for no service) that staff haven't closed."""
    return _one(conn.execute(
        "SELECT * FROM leads WHERE business_id = ? AND customer_id = ? AND service_id IS ?"
        " AND status IN ('NEW', 'IN_PROGRESS') ORDER BY created_at DESC, rowid DESC LIMIT 1",
        (business_id, customer_id, service_id),
    ))


def delete_messages_before(conn: sqlite3.Connection, business_id: str, cutoff: str) -> int:
    return conn.execute("DELETE FROM messages WHERE business_id = ? AND created_at < ?",
                        (business_id, cutoff)).rowcount


def get_lead(conn: sqlite3.Connection, business_id: str, lead_id: str) -> Row | None:
    return _one(conn.execute("SELECT * FROM leads WHERE business_id = ? AND id = ?", (business_id, lead_id)))


def list_leads(conn: sqlite3.Connection, business_id: str) -> list[Row]:
    return _all(conn.execute(
        "SELECT l.*, cu.external_customer_key, s.name AS service_name FROM leads l"
        " JOIN customers cu ON cu.business_id = l.business_id AND cu.id = l.customer_id"
        " LEFT JOIN services s ON s.business_id = l.business_id AND s.id = l.service_id"
        " WHERE l.business_id = ? ORDER BY l.created_at DESC, l.rowid DESC",
        (business_id,),
    ))


def update_lead(conn: sqlite3.Connection, business_id: str, lead_id: str, fields: dict[str, Any]) -> int:
    return _update(conn, "leads", business_id, lead_id, fields)


# ---------- appointment requests ----------

def insert_appointment(conn: sqlite3.Connection, business_id: str, customer_id: str, *, service_id: str,
                       requested_start_at: str, notes: str | None, reschedule_of: str | None,
                       status: str) -> str:
    appointment_id, now = new_id(), utc_now()
    conn.execute(
        "INSERT INTO appointment_requests (id, business_id, customer_id, service_id, requested_start_at,"
        " notes, reschedule_of, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (appointment_id, business_id, customer_id, service_id, requested_start_at, notes, reschedule_of,
         status, now, now),
    )
    return appointment_id


_APPOINTMENT_SELECT = (
    "SELECT a.*, s.name AS service_name, s.duration_minutes, cu.external_customer_key,"
    " cu.display_name AS customer_name FROM appointment_requests a"
    " JOIN services s ON s.business_id = a.business_id AND s.id = a.service_id"
    " JOIN customers cu ON cu.business_id = a.business_id AND cu.id = a.customer_id"
    " WHERE a.business_id = ?"
)


def get_appointment(conn: sqlite3.Connection, business_id: str, appointment_id: str) -> Row | None:
    return _one(conn.execute(_APPOINTMENT_SELECT + " AND a.id = ?", (business_id, appointment_id)))


def list_appointments(conn: sqlite3.Connection, business_id: str, *, statuses: Iterable[str] | None = None,
                      customer_id: str | None = None) -> list[Row]:
    sql, params = _APPOINTMENT_SELECT, [business_id]
    if statuses is not None:
        statuses = list(statuses)
        sql += f" AND a.status IN ({', '.join('?' for _ in statuses)})"
        params += statuses
    if customer_id is not None:
        sql += " AND a.customer_id = ?"
        params.append(customer_id)
    return _all(conn.execute(sql + " ORDER BY a.requested_start_at", params))


def update_appointment(conn: sqlite3.Connection, business_id: str, appointment_id: str,
                       fields: dict[str, Any]) -> int:
    return _update(conn, "appointment_requests", business_id, appointment_id, fields)


# ---------- audit ----------

def insert_audit(conn: sqlite3.Connection, business_id: str, *, actor: str, event_type: str,
                 entity_type: str, entity_id: str | None, details: dict[str, Any] | None = None) -> str:
    event_id = new_id()
    conn.execute(
        "INSERT INTO audit_events (id, business_id, actor, event_type, entity_type, entity_id, details_json,"
        " created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (event_id, business_id, actor, event_type, entity_type, entity_id, json.dumps(details or {}),
         utc_now()),
    )
    return event_id


def list_audit(conn: sqlite3.Connection, business_id: str, limit: int = 200) -> list[Row]:
    return _all(conn.execute(
        "SELECT * FROM audit_events WHERE business_id = ? ORDER BY created_at DESC, rowid DESC LIMIT ?",
        (business_id, limit),
    ))
