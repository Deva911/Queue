"""Status values, conversation states and small record types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class BusinessStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class Role(StrEnum):
    OWNER = "OWNER"
    STAFF = "STAFF"


class LeadStatus(StrEnum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    QUALIFIED = "QUALIFIED"
    CLOSED = "CLOSED"
    OPTED_OUT = "OPTED_OUT"


class ConversationStatus(StrEnum):
    BOT_ACTIVE = "BOT_ACTIVE"
    PENDING_HANDOFF = "PENDING_HANDOFF"
    HUMAN_ACTIVE = "HUMAN_ACTIVE"
    CLOSED = "CLOSED"


class AppointmentStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    DECLINED = "DECLINED"
    CANCELLED = "CANCELLED"


OPEN_APPOINTMENT_STATUSES = (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED)


class ConsentStatus(StrEnum):
    UNKNOWN = "UNKNOWN"
    OPTED_IN = "OPTED_IN"
    OPTED_OUT = "OPTED_OUT"


class State(StrEnum):
    """Where the customer is in the bot's menu."""

    MAIN_MENU = "MAIN_MENU"
    SERVICE_LIST = "SERVICE_LIST"
    BOOKING_SERVICE = "BOOKING_SERVICE"
    BOOKING_TIME = "BOOKING_TIME"
    BOOKING_NAME = "BOOKING_NAME"
    RESCHEDULE_SELECT = "RESCHEDULE_SELECT"
    RESCHEDULE_TIME = "RESCHEDULE_TIME"
    CANCEL_SELECT = "CANCEL_SELECT"
    CANCEL_CONFIRM = "CANCEL_CONFIRM"
    PAYMENT_INFO = "PAYMENT_INFO"
    PENDING_HANDOFF = "PENDING_HANDOFF"
    COMPLETED = "COMPLETED"


class Direction(StrEnum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


class Sender(StrEnum):
    CUSTOMER = "CUSTOMER"
    BOT = "BOT"
    STAFF = "STAFF"


# Weekday convention: 0 = Monday ... 6 = Sunday (same as Python's datetime.weekday()).
WEEKDAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

MAX_MESSAGE_LENGTH = 500
MAX_NAME_LENGTH = 80
MAX_TEXT_FIELD_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 1000


class ValidationError(ValueError):
    """Bad input from an owner, staff member or customer. The message is safe to show."""


class AuthError(ValidationError):
    """Sign-in failed, or the signed-in person isn't allowed to do this. The message is safe to show."""


class NotFoundError(LookupError):
    """The record does not exist for this business."""


@dataclass(frozen=True)
class Slot:
    start_at: str  # ISO 8601 with the business's UTC offset
    label: str  # e.g. "Tue 28 Oct, 10:30"
