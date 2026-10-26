"""CSV export of one business's leads and appointment requests."""

from __future__ import annotations

import csv
import io
import sqlite3

from .. import repositories as repo

LEAD_COLUMNS = ["id", "created_at", "external_customer_key", "name", "service_name", "enquiry", "status"]
APPOINTMENT_COLUMNS = ["id", "created_at", "external_customer_key", "customer_name", "service_name",
                       "requested_start_at", "status", "staff_note", "reschedule_of"]


def _safe(value) -> str:
    """Stop spreadsheet apps treating customer text like '=SUM(...)' as a formula."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def _to_csv(rows: list[dict], columns: list[str]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns)
    for row in rows:
        writer.writerow([_safe(row.get(col)) for col in columns])
    return buffer.getvalue()


def leads_csv(conn: sqlite3.Connection, business_id: str) -> str:
    return _to_csv(repo.list_leads(conn, business_id), LEAD_COLUMNS)


def appointments_csv(conn: sqlite3.Connection, business_id: str) -> str:
    return _to_csv(repo.list_appointments(conn, business_id), APPOINTMENT_COLUMNS)
