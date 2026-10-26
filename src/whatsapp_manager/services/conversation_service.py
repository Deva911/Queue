"""Runs one inbound chat message end to end, and the staff side of human handoff.

Flow for a customer message:
  find/create customer + conversation -> save inbound message ->
  if a person has taken over, stay silent -> otherwise ask the bot ->
  carry out the bot's actions -> save the new state and the bot's reply.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .. import repositories as repo
from ..models import (
    MAX_MESSAGE_LENGTH,
    OPEN_APPOINTMENT_STATUSES,
    ConversationStatus,
    Direction,
    LeadStatus,
    NotFoundError,
    Sender,
    State,
    ValidationError,
)
from . import appointment_service, bot

STAFF = "staff (demo)"
MAX_CUSTOMER_KEY_LENGTH = 32


@dataclass
class ChatResult:
    conversation_id: str
    reply: str | None  # None means the bot stayed silent (a person is handling the chat)
    state: str
    status: str
    options: list[tuple[str, str]] = field(default_factory=list)


def _now(now: datetime | None) -> datetime:
    return now or datetime.now(timezone.utc)


def clean_customer_key(key: str) -> str:
    key = (key or "").strip()
    if not key or len(key) > MAX_CUSTOMER_KEY_LENGTH:
        raise ValidationError(f"Customer number must be 1 to {MAX_CUSTOMER_KEY_LENGTH} characters.")
    return key


def _build_context(conn: sqlite3.Connection, business: dict, customer: dict, now: datetime) -> bot.BotContext:
    business_id = business["id"]
    services = [
        bot.ServiceOption(s["id"], s["name"], s["description"], s["price_minor"], s["currency"],
                          s["duration_minutes"])
        for s in repo.list_services(conn, business_id, active_only=True)
    ]
    appointments = [
        bot.AppointmentOption(a["id"], a["service_id"], a["service_name"],
                              appointment_service.slot_label(datetime.fromisoformat(a["requested_start_at"])),
                              a["status"])
        for a in repo.list_appointments(conn, business_id, statuses=OPEN_APPOINTMENT_STATUSES,
                                        customer_id=customer["id"])
        if datetime.fromisoformat(a["requested_start_at"]) > now
    ]
    return bot.BotContext(
        business_name=business["name"],
        services=services,
        payment_info=business["payment_info"] or "Please ask our team about payment options.",
        find_slots=lambda service_id, moving=None: appointment_service.find_open_slots(
            conn, business_id, service_id, now, exclude_id=moving),
        appointments=appointments,
        customer_name=customer["display_name"],
    )


def _get_or_start(conn: sqlite3.Connection, business_id: str, customer_key: str) -> tuple[dict, dict]:
    customer = repo.get_customer_by_key(conn, business_id, customer_key)
    if customer is None:
        repo.insert_customer(conn, business_id, customer_key)
        customer = repo.get_customer_by_key(conn, business_id, customer_key)
    conversation = repo.get_open_conversation(conn, business_id, customer["id"])
    if conversation is None:
        conversation_id = repo.insert_conversation(conn, business_id, customer["id"], State.MAIN_MENU,
                                                   ConversationStatus.BOT_ACTIVE)
        conversation = repo.get_conversation(conn, business_id, conversation_id)
    return customer, conversation


def _apply(conn: sqlite3.Connection, business_id: str, customer: dict, conversation: dict,
           action: bot.Action, now: datetime) -> None:
    if isinstance(action, bot.CreateAppointment):
        if action.customer_name and action.customer_name != customer["display_name"]:
            repo.update_customer(conn, business_id, customer["id"], {"display_name": action.customer_name})
        appointment_service.create_request(conn, business_id, customer["id"], action.service_id,
                                           action.start_at, now, reschedule_of=action.reschedule_of)
    elif isinstance(action, bot.CancelAppointment):
        appointment_service.customer_cancel(conn, business_id, customer["id"], action.appointment_id)
    elif isinstance(action, bot.RecordLead):
        repo.insert_lead(conn, business_id, customer["id"], service_id=action.service_id,
                         name=repo.get_customer(conn, business_id, customer["id"])["display_name"],
                         enquiry=action.enquiry, status=LeadStatus.NEW)
    elif isinstance(action, bot.RequestHandoff):
        repo.update_conversation(conn, business_id, conversation["id"],
                                 {"status": ConversationStatus.PENDING_HANDOFF})
        repo.insert_lead(conn, business_id, customer["id"], service_id=None, name=customer["display_name"],
                         enquiry="Asked to talk to a person", status=LeadStatus.NEW)
        repo.insert_audit(conn, business_id, actor="customer", event_type="HANDOFF_REQUESTED",
                          entity_type="conversation", entity_id=conversation["id"],
                          details={"reason": action.reason})
    else:  # pragma: no cover - guards against a new action type being forgotten
        raise TypeError(f"Unknown bot action {action!r}")


def handle_inbound(conn: sqlite3.Connection, business_id: str, customer_key: str, text: str,
                   now: datetime | None = None) -> ChatResult:
    now = _now(now)
    business = repo.get_business(conn, business_id)
    if business is None:
        raise NotFoundError("Business not found.")
    customer_key = clean_customer_key(customer_key)
    text = (text or "").strip()
    if not text:
        raise ValidationError("Message is empty.")
    if len(text) > MAX_MESSAGE_LENGTH:
        raise ValidationError(f"Messages must be {MAX_MESSAGE_LENGTH} characters or fewer.")

    with conn:
        customer, conversation = _get_or_start(conn, business_id, customer_key)
        repo.insert_message(conn, business_id, conversation["id"], Direction.INBOUND, Sender.CUSTOMER, text)
        if conversation["status"] != ConversationStatus.BOT_ACTIVE:
            # A person is handling this chat: the bot stays silent.
            return ChatResult(conversation["id"], None, conversation["state"], conversation["status"])

        if business["status"] != "ACTIVE":
            reply = bot.BotReply(f"Sorry, {business['name']} is not taking messages through this assistant "
                                 "right now.", State(conversation["state"]), json.loads(conversation["context_json"]))
        else:
            ctx = _build_context(conn, business, customer, now)
            data = json.loads(conversation["context_json"])
            reply = bot.handle(ctx, conversation["state"], data, text)
            try:
                # Savepoint so a failed action leaves no half-written rows behind.
                conn.execute("SAVEPOINT bot_actions")
                for action in reply.actions:
                    _apply(conn, business_id, customer, conversation, action, now)
                conn.execute("RELEASE bot_actions")
            except appointment_service.SlotUnavailableError as exc:
                conn.execute("ROLLBACK TO bot_actions")
                conn.execute("RELEASE bot_actions")
                state = State.BOOKING_SERVICE if conversation["state"] != State.RESCHEDULE_TIME else State.MAIN_MENU
                reply = bot.render(state, ctx, {k: v for k, v in data.items() if k in {"greeted", "name"}},
                                   intro=f"{exc} Please pick again.")

        status = (ConversationStatus.PENDING_HANDOFF if reply.state == State.PENDING_HANDOFF
                  else ConversationStatus.BOT_ACTIVE)
        repo.update_conversation(conn, business_id, conversation["id"],
                                 {"state": reply.state, "status": status, "context": reply.data})
        repo.insert_message(conn, business_id, conversation["id"], Direction.OUTBOUND, Sender.BOT, reply.text)
    return ChatResult(conversation["id"], reply.text, reply.state, status, reply.options)


def current_options(conn: sqlite3.Connection, business_id: str, conversation_id: str,
                    now: datetime | None = None) -> list[tuple[str, str]]:
    """Buttons for the conversation's current state (empty while a person is handling it)."""
    conversation = repo.get_conversation(conn, business_id, conversation_id)
    if conversation is None or conversation["status"] != ConversationStatus.BOT_ACTIVE:
        return []
    business = repo.get_business(conn, business_id)
    customer = repo.get_customer(conn, business_id, conversation["customer_id"])
    state = State(conversation["state"])
    data = json.loads(conversation["context_json"])
    if state == State.MAIN_MENU and not data.get("greeted"):
        return list(bot.MAIN_MENU_OPTIONS)
    ctx = _build_context(conn, business, customer, _now(now))
    try:
        return bot.render(state, ctx, data).options
    except ValueError:
        return []


# ---------- staff side of handoff ----------

def _conversation(conn: sqlite3.Connection, business_id: str, conversation_id: str) -> dict:
    conversation = repo.get_conversation(conn, business_id, conversation_id)
    if conversation is None:
        raise NotFoundError("Conversation not found for this business.")
    return conversation


def take_over(conn: sqlite3.Connection, business_id: str, conversation_id: str, actor: str = STAFF) -> None:
    conversation = _conversation(conn, business_id, conversation_id)
    if conversation["status"] == ConversationStatus.HUMAN_ACTIVE:
        return
    with conn:
        repo.update_conversation(conn, business_id, conversation_id,
                                 {"status": ConversationStatus.HUMAN_ACTIVE, "state": State.PENDING_HANDOFF})
        repo.insert_audit(conn, business_id, actor=actor, event_type="HANDOFF_ACCEPTED",
                          entity_type="conversation", entity_id=conversation_id,
                          details={"from": conversation["status"]})


def staff_reply(conn: sqlite3.Connection, business_id: str, conversation_id: str, text: str,
                actor: str = STAFF) -> None:
    text = (text or "").strip()
    if not text:
        raise ValidationError("Reply is empty.")
    if len(text) > MAX_MESSAGE_LENGTH:
        raise ValidationError(f"Replies must be {MAX_MESSAGE_LENGTH} characters or fewer.")
    conversation = _conversation(conn, business_id, conversation_id)
    if conversation["status"] == ConversationStatus.BOT_ACTIVE:
        raise ValidationError("Take over the conversation before replying, so the bot doesn't talk over you.")
    if conversation["status"] == ConversationStatus.PENDING_HANDOFF:
        take_over(conn, business_id, conversation_id, actor)
    with conn:
        repo.insert_message(conn, business_id, conversation_id, Direction.OUTBOUND, Sender.STAFF, text)
        repo.insert_audit(conn, business_id, actor=actor, event_type="STAFF_REPLIED",
                          entity_type="conversation", entity_id=conversation_id)


def return_to_bot(conn: sqlite3.Connection, business_id: str, conversation_id: str,
                  resolution_note: str | None = None, actor: str = STAFF) -> None:
    conversation = _conversation(conn, business_id, conversation_id)
    if conversation["status"] == ConversationStatus.BOT_ACTIVE:
        return
    note = (resolution_note or "").strip() or None
    menu_text = bot.main_menu_text("You're back with our automated assistant.")
    with conn:
        repo.update_conversation(conn, business_id, conversation_id,
                                 {"status": ConversationStatus.BOT_ACTIVE, "state": State.MAIN_MENU,
                                  "context": {"greeted": True}})
        repo.insert_message(conn, business_id, conversation_id, Direction.OUTBOUND, Sender.BOT, menu_text)
        repo.insert_audit(conn, business_id, actor=actor, event_type="HANDOFF_RETURNED_TO_BOT",
                          entity_type="conversation", entity_id=conversation_id,
                          details={"resolution_note": note})


def close_for_customer(conn: sqlite3.Connection, business_id: str, customer_key: str,
                       actor: str = "simulator") -> None:
    """Simulator 'Start over': close the customer's open chat so the next message starts fresh."""
    customer = repo.get_customer_by_key(conn, business_id, clean_customer_key(customer_key))
    conversation = repo.get_open_conversation(conn, business_id, customer["id"]) if customer else None
    if conversation is None:
        return
    with conn:
        repo.update_conversation(conn, business_id, conversation["id"], {"status": ConversationStatus.CLOSED})
        repo.insert_audit(conn, business_id, actor=actor, event_type="CONVERSATION_CLOSED",
                          entity_type="conversation", entity_id=conversation["id"])


def list_conversations(conn: sqlite3.Connection, business_id: str, statuses=None) -> list[dict]:
    return repo.list_conversations(conn, business_id, statuses)


def list_messages(conn: sqlite3.Connection, business_id: str, conversation_id: str) -> list[dict]:
    return repo.list_messages(conn, business_id, conversation_id)


def set_lead_status(conn: sqlite3.Connection, business_id: str, lead_id: str, status: str,
                    actor: str = STAFF) -> None:
    if status not in {s.value for s in LeadStatus}:
        raise ValidationError("Unknown lead status.")
    lead = repo.get_lead(conn, business_id, lead_id)
    if lead is None:
        raise NotFoundError("Lead not found for this business.")
    with conn:
        repo.update_lead(conn, business_id, lead_id, {"status": status})
        repo.insert_audit(conn, business_id, actor=actor, event_type="LEAD_STATUS_CHANGED", entity_type="lead",
                          entity_id=lead_id, details={"from": lead["status"], "to": status})
