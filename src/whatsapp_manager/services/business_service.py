"""Business sign-up, profile, opening hours and the service catalogue."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import time
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .. import repositories as repo
from ..models import (
    MAX_DESCRIPTION_LENGTH,
    MAX_TEXT_FIELD_LENGTH,
    BusinessStatus,
    NotFoundError,
    ValidationError,
)

OWNER = "owner (demo)"
DEFAULT_TIMEZONE = "Asia/Kolkata"
DEFAULT_CURRENCY = "INR"
DEFAULT_HOURS = {d: ("09:00", "17:00") for d in range(5)}  # Mon-Fri 9-5, weekends closed
DEFAULT_PAYMENT_INFO = "Payment is taken at the appointment. We accept cash, UPI and cards."
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_CURRENCY = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True)
class BusinessInput:
    name: str
    category: str | None = None
    address: str | None = None
    contact_email: str | None = None
    timezone: str = DEFAULT_TIMEZONE
    logo_url: str | None = None
    payment_info: str | None = None
    status: str = BusinessStatus.ACTIVE


@dataclass(frozen=True)
class ServiceInput:
    name: str
    description: str | None = None
    price: str | None = None  # what the owner typed, e.g. "450" or "450.50"
    currency: str | None = DEFAULT_CURRENCY
    duration_minutes: int | None = None


# ---------- validation helpers ----------

def _clean(value: str | None, field: str, *, required: bool = False,
           max_len: int = MAX_TEXT_FIELD_LENGTH) -> str | None:
    value = (value or "").strip()
    if not value:
        if required:
            raise ValidationError(f"{field} is required.")
        return None
    if len(value) > max_len:
        raise ValidationError(f"{field} must be {max_len} characters or fewer.")
    return value


def validate_timezone(name: str) -> str:
    name = (name or "").strip()
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValidationError(f"'{name}' is not a recognised time zone (example: Asia/Kolkata).") from None
    return name


def parse_price(text: str | None) -> int | None:
    """Turn what the owner typed ("450", "450.5") into whole minor units (45050). Blank means no price."""
    text = (text or "").strip().replace(",", "")
    if not text:
        return None
    try:
        amount = Decimal(text)
    except InvalidOperation:
        raise ValidationError("Price must be a number, for example 450 or 450.50.") from None
    if not amount.is_finite() or amount < 0:
        raise ValidationError("Price must be zero or more.")
    if amount != amount.quantize(Decimal("0.01")):
        raise ValidationError("Price can have at most two decimal places.")
    return int(amount * 100)


def format_price(price_minor: int | None, currency: str | None) -> str:
    if price_minor is None:
        return "Price on request"
    return f"{currency} {Decimal(price_minor) / 100:,.2f}"


def _business_fields(data: BusinessInput) -> dict:
    email = _clean(data.contact_email, "Contact email")
    if email and not _EMAIL.match(email):
        raise ValidationError("Contact email doesn't look like an email address.")
    if data.status not in {s.value for s in BusinessStatus}:
        raise ValidationError("Status must be ACTIVE or INACTIVE.")
    return {
        "name": _clean(data.name, "Business name", required=True),
        "category": _clean(data.category, "Category"),
        "address": _clean(data.address, "Address"),
        "contact_email": email,
        "timezone": validate_timezone(data.timezone),
        "logo_url": _clean(data.logo_url, "Logo URL"),
        "payment_info": _clean(data.payment_info, "Payment information", max_len=MAX_DESCRIPTION_LENGTH),
        "status": str(data.status),
    }


def _service_fields(data: ServiceInput) -> dict:
    price_minor = parse_price(data.price)
    currency = (data.currency or "").strip().upper() or None
    if price_minor is not None:
        if not currency or not _CURRENCY.match(currency):
            raise ValidationError("Currency must be a 3-letter code such as INR or USD when a price is set.")
    else:
        currency = None
    duration = data.duration_minutes
    if duration is not None and (not isinstance(duration, int) or duration <= 0):
        raise ValidationError("Duration must be a whole number of minutes greater than zero.")
    return {
        "name": _clean(data.name, "Service name", required=True),
        "description": _clean(data.description, "Description", max_len=MAX_DESCRIPTION_LENGTH),
        "price_minor": price_minor,
        "currency": currency,
        "duration_minutes": duration,
    }


# ---------- businesses ----------

def create_business(conn: sqlite3.Connection, data: BusinessInput, actor: str = OWNER) -> str:
    """Business sign-up. Also sets default opening hours so the bot can offer times straight away."""
    fields = _business_fields(data)
    if not fields["payment_info"]:
        fields["payment_info"] = DEFAULT_PAYMENT_INFO
    with conn:
        business_id = repo.insert_business(
            conn, name=fields["name"], category=fields["category"], address=fields["address"],
            contact_email=fields["contact_email"], timezone_name=fields["timezone"],
            logo_url=fields["logo_url"], payment_info=fields["payment_info"], status=fields["status"],
        )
        for weekday in range(7):
            opens, closes = DEFAULT_HOURS.get(weekday, (None, None))
            repo.upsert_hours(conn, business_id, weekday, opens, closes, is_closed=opens is None)
        repo.insert_audit(conn, business_id, actor=actor, event_type="BUSINESS_CREATED",
                          entity_type="business", entity_id=business_id, details={"name": fields["name"]})
    return business_id


def get_business(conn: sqlite3.Connection, business_id: str) -> dict:
    business = repo.get_business(conn, business_id)
    if business is None:
        raise NotFoundError("Business not found.")
    return business


def update_business(conn: sqlite3.Connection, business_id: str, data: BusinessInput, actor: str = OWNER) -> None:
    get_business(conn, business_id)
    fields = _business_fields(data)
    with conn:
        repo.update_business(conn, business_id, fields)
        repo.insert_audit(conn, business_id, actor=actor, event_type="BUSINESS_UPDATED",
                          entity_type="business", entity_id=business_id)


# ---------- hours ----------

def _parse_hhmm(value: str, label: str) -> time:
    try:
        return time.fromisoformat(value.strip())
    except (ValueError, AttributeError):
        raise ValidationError(f"{label} must be a time like 09:00.") from None


def validate_hours(opens_at: str | None, closes_at: str | None, is_closed: bool,
                   label: str = "") -> tuple[str | None, str | None]:
    """Return cleaned ("HH:MM", "HH:MM"), or (None, None) for a closed day."""
    if is_closed:
        return None, None
    prefix = f"{label}: " if label else ""
    opens = _parse_hhmm(opens_at or "", f"{prefix}Opening time")
    closes = _parse_hhmm(closes_at or "", f"{prefix}Closing time")
    if closes <= opens:
        raise ValidationError(f"{prefix}Closing time must be after opening time.")
    return opens.strftime("%H:%M"), closes.strftime("%H:%M")


def set_hours(conn: sqlite3.Connection, business_id: str, weekday: int, opens_at: str | None,
              closes_at: str | None, is_closed: bool, actor: str = OWNER) -> None:
    get_business(conn, business_id)
    if not 0 <= weekday <= 6:
        raise ValidationError("Weekday must be 0 (Monday) to 6 (Sunday).")
    opens_at, closes_at = validate_hours(opens_at, closes_at, is_closed)
    with conn:
        repo.upsert_hours(conn, business_id, weekday, opens_at, closes_at, is_closed)
        repo.insert_audit(conn, business_id, actor=actor, event_type="HOURS_UPDATED", entity_type="business_hours",
                          entity_id=str(weekday),
                          details={"opens_at": opens_at, "closes_at": closes_at, "is_closed": is_closed})


def list_hours(conn: sqlite3.Connection, business_id: str) -> list[dict]:
    return repo.list_hours(conn, business_id)


# ---------- services ----------

def add_service(conn: sqlite3.Connection, business_id: str, data: ServiceInput, actor: str = OWNER) -> str:
    get_business(conn, business_id)
    fields = _service_fields(data)
    with conn:
        service_id = repo.insert_service(conn, business_id, **fields)
        repo.insert_audit(conn, business_id, actor=actor, event_type="SERVICE_CREATED", entity_type="service",
                          entity_id=service_id, details={"name": fields["name"]})
    return service_id


def get_service(conn: sqlite3.Connection, business_id: str, service_id: str) -> dict:
    service = repo.get_service(conn, business_id, service_id)
    if service is None:
        raise NotFoundError("Service not found for this business.")
    return service


def update_service(conn: sqlite3.Connection, business_id: str, service_id: str, data: ServiceInput,
                   actor: str = OWNER) -> None:
    get_service(conn, business_id, service_id)
    fields = _service_fields(data)
    with conn:
        repo.update_service(conn, business_id, service_id, fields)
        repo.insert_audit(conn, business_id, actor=actor, event_type="SERVICE_UPDATED", entity_type="service",
                          entity_id=service_id)


def set_service_active(conn: sqlite3.Connection, business_id: str, service_id: str, active: bool,
                       actor: str = OWNER) -> None:
    get_service(conn, business_id, service_id)
    with conn:
        repo.update_service(conn, business_id, service_id, {"is_active": int(active)})
        repo.insert_audit(conn, business_id, actor=actor,
                          event_type="SERVICE_ACTIVATED" if active else "SERVICE_DEACTIVATED",
                          entity_type="service", entity_id=service_id)


def list_services(conn: sqlite3.Connection, business_id: str, *, active_only: bool = False) -> list[dict]:
    return repo.list_services(conn, business_id, active_only=active_only)
