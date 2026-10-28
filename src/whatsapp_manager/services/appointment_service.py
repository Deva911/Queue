"""Appointment requests: open times, PENDING requests, and staff decisions.

Nothing here talks to a real calendar. "Open times" are the business's opening hours minus
requests that are already PENDING or CONFIRMED, and every new request is saved as PENDING
until a staff member decides.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from .. import repositories as repo
from ..models import (
    MAX_TEXT_FIELD_LENGTH,
    OPEN_APPOINTMENT_STATUSES,
    AppointmentStatus,
    NotFoundError,
    Sender,
    Direction,
    Slot,
    ValidationError,
)

STAFF = "staff (demo)"
DEFAULT_SLOT_MINUTES = 30
SLOT_DAYS_AHEAD = 7
MAX_SLOTS_OFFERED = 8

# Which staff decisions are allowed from each status.
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    AppointmentStatus.PENDING: {AppointmentStatus.CONFIRMED, AppointmentStatus.DECLINED, AppointmentStatus.CANCELLED},
    AppointmentStatus.CONFIRMED: {AppointmentStatus.CANCELLED},
    AppointmentStatus.DECLINED: set(),
    AppointmentStatus.CANCELLED: set(),
}


class SlotUnavailableError(ValidationError):
    """The requested time was taken (or became invalid) since it was offered."""


def slot_label(start: datetime) -> str:
    return start.strftime("%a %d %b, %H:%M")


def _duration(minutes: int | None) -> timedelta:
    return timedelta(minutes=minutes or DEFAULT_SLOT_MINUTES)


def _busy_intervals(conn: sqlite3.Connection, business_id: str, exclude_id: str | None = None):
    for appt in repo.list_appointments(conn, business_id, statuses=OPEN_APPOINTMENT_STATUSES):
        if appt["id"] == exclude_id:
            continue
        start = datetime.fromisoformat(appt["requested_start_at"])
        yield start, start + _duration(appt["duration_minutes"])


def find_open_slots(conn: sqlite3.Connection, business_id: str, service_id: str, now: datetime,
                    *, days: int = SLOT_DAYS_AHEAD, limit: int = MAX_SLOTS_OFFERED,
                    exclude_id: str | None = None) -> list[Slot]:
    """Times within opening hours over the next `days` days that don't overlap an open request.

    exclude_id: the request being rescheduled, so its own time doesn't block nearby times.
    """
    business = repo.get_business(conn, business_id)
    service = repo.get_service(conn, business_id, service_id)
    if business is None or service is None:
        raise NotFoundError("Service not found for this business.")
    tz = ZoneInfo(business["timezone"])
    local_now = now.astimezone(tz)
    length = _duration(service["duration_minutes"])
    hours = {h["weekday"]: h for h in repo.list_hours(conn, business_id)}
    busy = list(_busy_intervals(conn, business_id, exclude_id))

    slots: list[Slot] = []
    for offset in range(days):
        day: date = local_now.date() + timedelta(days=offset)
        h = hours.get(day.weekday())
        if not h or h["is_closed"] or not h["opens_at"] or not h["closes_at"]:
            continue
        start = datetime.combine(day, time.fromisoformat(h["opens_at"]), tz)
        close = datetime.combine(day, time.fromisoformat(h["closes_at"]), tz)
        while start + length <= close:
            end = start + length
            if start > local_now and not any(start < b_end and b_start < end for b_start, b_end in busy):
                slots.append(Slot(start_at=start.isoformat(), label=slot_label(start)))
                if len(slots) >= limit:
                    return slots
            start += length
    return slots


def _ensure_slot_still_open(conn: sqlite3.Connection, business_id: str, service: dict, start_at: str,
                            now: datetime, exclude_id: str | None = None) -> None:
    try:
        start = datetime.fromisoformat(start_at)
    except ValueError:
        raise SlotUnavailableError("That time is not valid.") from None
    if start.tzinfo is None or start <= now:
        raise SlotUnavailableError("That time is in the past.")
    end = start + _duration(service["duration_minutes"])
    if any(start < b_end and b_start < end for b_start, b_end in _busy_intervals(conn, business_id, exclude_id)):
        raise SlotUnavailableError("Sorry, that time was just requested by someone else.")


def create_request(conn: sqlite3.Connection, business_id: str, customer_id: str, service_id: str,
                   start_at: str, now: datetime, *, notes: str | None = None,
                   reschedule_of: str | None = None, actor: str = "customer") -> str:
    """Save a PENDING appointment request. Caller manages the transaction."""
    service = repo.get_service(conn, business_id, service_id)
    if service is None:
        raise ValidationError("That service does not belong to this business.")
    if not service["is_active"]:
        raise ValidationError("That service is not currently offered.")
    if repo.get_customer(conn, business_id, customer_id) is None:
        raise ValidationError("Unknown customer for this business.")
    if reschedule_of is not None:
        original = repo.get_appointment(conn, business_id, reschedule_of)
        if original is None or original["customer_id"] != customer_id:
            raise ValidationError("That appointment request was not found.")
        if original["status"] not in OPEN_APPOINTMENT_STATUSES:
            raise ValidationError("That appointment request is already closed.")
    if notes and len(notes) > MAX_TEXT_FIELD_LENGTH:
        raise ValidationError(f"Notes must be {MAX_TEXT_FIELD_LENGTH} characters or fewer.")
    _ensure_slot_still_open(conn, business_id, service, start_at, now, exclude_id=reschedule_of)
    appointment_id = repo.insert_appointment(
        conn, business_id, customer_id, service_id=service_id, requested_start_at=start_at, notes=notes,
        reschedule_of=reschedule_of, status=AppointmentStatus.PENDING,
    )
    repo.insert_audit(conn, business_id, actor=actor,
                      event_type="RESCHEDULE_REQUESTED" if reschedule_of else "APPOINTMENT_REQUESTED",
                      entity_type="appointment_request", entity_id=appointment_id,
                      details={"service_id": service_id, "requested_start_at": start_at,
                               "reschedule_of": reschedule_of})
    return appointment_id


def customer_cancel(conn: sqlite3.Connection, business_id: str, customer_id: str, appointment_id: str) -> None:
    """Customer cancels their own open request. Caller manages the transaction."""
    appt = repo.get_appointment(conn, business_id, appointment_id)
    if appt is None or appt["customer_id"] != customer_id:
        raise ValidationError("That appointment request was not found.")
    if appt["status"] not in OPEN_APPOINTMENT_STATUSES:
        raise ValidationError("That appointment request is already closed.")
    repo.update_appointment(conn, business_id, appointment_id, {"status": AppointmentStatus.CANCELLED})
    repo.insert_audit(conn, business_id, actor="customer", event_type="APPOINTMENT_CANCELLED_BY_CUSTOMER",
                      entity_type="appointment_request", entity_id=appointment_id,
                      details={"from": appt["status"]})


def _notify_customer(conn: sqlite3.Connection, business_id: str, customer_id: str, text: str) -> None:
    """Drop a simulated outbound message into the customer's open conversation, if any."""
    conversation = repo.get_open_conversation(conn, business_id, customer_id)
    if conversation:
        repo.insert_message(conn, business_id, conversation["id"], Direction.OUTBOUND, Sender.STAFF, text)


def staff_set_status(conn: sqlite3.Connection, business_id: str, appointment_id: str, new_status: str,
                     note: str | None = None, actor: str = STAFF) -> None:
    """Staff confirm, decline or cancel a request. This is a manual decision, not a calendar booking."""
    appt = repo.get_appointment(conn, business_id, appointment_id)
    if appt is None:
        raise NotFoundError("Appointment request not found for this business.")
    if new_status not in ALLOWED_TRANSITIONS.get(appt["status"], set()):
        raise ValidationError(f"Can't change a {appt['status']} request to {new_status}.")
    note = (note or "").strip() or None
    if note and len(note) > MAX_TEXT_FIELD_LENGTH:
        raise ValidationError(f"Notes must be {MAX_TEXT_FIELD_LENGTH} characters or fewer.")
    label = slot_label(datetime.fromisoformat(appt["requested_start_at"]))
    with conn:
        repo.update_appointment(conn, business_id, appointment_id, {"status": new_status, "staff_note": note})
        repo.insert_audit(conn, business_id, actor=actor, event_type=f"APPOINTMENT_{new_status}",
                          entity_type="appointment_request", entity_id=appointment_id,
                          details={"from": appt["status"], "to": new_status, "note": note})
        # Confirming a reschedule request closes the original one.
        if new_status == AppointmentStatus.CONFIRMED and appt["reschedule_of"]:
            original = repo.get_appointment(conn, business_id, appt["reschedule_of"])
            if original and original["status"] in OPEN_APPOINTMENT_STATUSES:
                repo.update_appointment(conn, business_id, original["id"],
                                        {"status": AppointmentStatus.CANCELLED,
                                         "staff_note": "Replaced by rescheduled request"})
                repo.insert_audit(conn, business_id, actor=actor, event_type="APPOINTMENT_CANCELLED",
                                  entity_type="appointment_request", entity_id=original["id"],
                                  details={"reason": "rescheduled", "replaced_by": appointment_id})
        wording = {
            AppointmentStatus.CONFIRMED: "has been confirmed by our team",
            AppointmentStatus.DECLINED: "could not be accepted. Reply 1 to choose another time",
            AppointmentStatus.CANCELLED: "has been cancelled by our team",
        }[new_status]
        _notify_customer(conn, business_id, appt["customer_id"],
                         f"Update: your request for {appt['service_name']} on {label} {wording}."
                         + (f" Note: {note}" if note else ""))


def list_requests(conn: sqlite3.Connection, business_id: str, statuses=None) -> list[dict]:
    return repo.list_appointments(conn, business_id, statuses=statuses)
