"""The menu bot as a plain function.

    handle(ctx, state, data, text) -> BotReply

No database or Streamlit code in here. Whatever the bot wants to happen (save a request,
hand over to staff) comes back as `actions`, which conversation_service carries out.
That keeps every menu rule easy to test.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ..models import MAX_NAME_LENGTH, Slot, State
from .business_service import format_price

MAIN_MENU_OPTIONS = (
    ("1", "Book an appointment"),
    ("2", "View services and prices"),
    ("3", "Reschedule an appointment"),
    ("4", "Cancel an appointment"),
    ("5", "Payment information"),
    ("6", "Talk to a person"),
)
COMMANDS_HINT = "Type MENU for the main menu, BACK to go back, HELP for help or HUMAN for a person."
AFTER_DONE = "Anything else? Reply MENU to see the options again."
PENDING_NOTE = "This is a request, not a confirmed booking. Our team will confirm it or suggest another time."

BACK_TO = {
    State.SERVICE_LIST: State.MAIN_MENU,
    State.BOOKING_SERVICE: State.MAIN_MENU,
    State.BOOKING_TIME: State.BOOKING_SERVICE,
    State.BOOKING_NAME: State.BOOKING_TIME,
    State.RESCHEDULE_SELECT: State.MAIN_MENU,
    State.RESCHEDULE_TIME: State.RESCHEDULE_SELECT,
    State.CANCEL_SELECT: State.MAIN_MENU,
    State.CANCEL_CONFIRM: State.CANCEL_SELECT,
    State.PAYMENT_INFO: State.MAIN_MENU,
    State.COMPLETED: State.MAIN_MENU,
    State.MAIN_MENU: State.MAIN_MENU,
}


# ---------- inputs ----------

@dataclass(frozen=True)
class ServiceOption:
    id: str
    name: str
    description: str | None = None
    price_minor: int | None = None
    currency: str | None = None
    duration_minutes: int | None = None


@dataclass(frozen=True)
class AppointmentOption:
    id: str
    service_id: str
    service_name: str
    start_label: str
    status: str


@dataclass
class BotContext:
    business_name: str
    services: list[ServiceOption]  # active services only
    payment_info: str
    find_slots: Callable[[str, str | None], list[Slot]]  # (service_id, request being moved) -> open times
    appointments: list[AppointmentOption] = field(default_factory=list)  # customer's open requests
    customer_name: str | None = None


# ---------- actions the caller must carry out ----------

@dataclass(frozen=True)
class CreateAppointment:
    service_id: str
    start_at: str
    customer_name: str | None = None
    reschedule_of: str | None = None


@dataclass(frozen=True)
class CancelAppointment:
    appointment_id: str


@dataclass(frozen=True)
class RecordLead:
    enquiry: str
    service_id: str | None = None


@dataclass(frozen=True)
class RequestHandoff:
    reason: str


Action = CreateAppointment | CancelAppointment | RecordLead | RequestHandoff


@dataclass
class BotReply:
    text: str
    state: State
    data: dict
    options: list[tuple[str, str]] = field(default_factory=list)  # (what to send, button label)
    actions: list[Action] = field(default_factory=list)


# ---------- rendering each state ----------

def _numbered(options: list[tuple[str, str]]) -> str:
    return "\n".join(f"{value}. {label}" for value, label in options)


def _service_line(s: ServiceOption) -> str:
    bits = [format_price(s.price_minor, s.currency)]
    if s.duration_minutes:
        bits.append(f"{s.duration_minutes} min")
    line = f"{s.name}: {', '.join(bits)}"
    return f"{line}\n   {s.description}" if s.description else line


def main_menu_text(intro: str | None = None) -> str:
    text = "How can we help? Reply with a number:\n" + _numbered(list(MAIN_MENU_OPTIONS))
    return f"{intro}\n\n{text}" if intro else text


def _main_menu(ctx: BotContext, data: dict, intro: str | None = None) -> BotReply:
    return BotReply(main_menu_text(intro), State.MAIN_MENU, _keep(data), list(MAIN_MENU_OPTIONS))


def _keep(data: dict, **changes) -> dict:
    """Carry forward only the keys that matter across turns."""
    kept = {k: v for k, v in data.items() if k in {"greeted", "name"}}
    kept.update(changes)
    return kept


def render(state: State, ctx: BotContext, data: dict, intro: str | None = None) -> BotReply:
    """The prompt for a state. Used on entry, for HELP, BACK, and after invalid input."""
    prefix = f"{intro}\n\n" if intro else ""

    if state == State.MAIN_MENU:
        return _main_menu(ctx, data, intro=intro)

    if state == State.SERVICE_LIST:
        if not ctx.services:
            body = "We don't have any services listed right now."
        else:
            body = "Our services:\n" + "\n".join(f"- {_service_line(s)}" for s in ctx.services)
        options = [("1", "Book an appointment"), ("0", "Back to menu")]
        return BotReply(f"{prefix}{body}\n\n{_numbered(options)}", state, data, options)

    if state == State.BOOKING_SERVICE:
        options = [(str(i), s.name) for i, s in enumerate(ctx.services, 1)]
        return BotReply(f"{prefix}Which service would you like to book? Reply with a number:\n{_numbered(options)}",
                        state, data, options + [("BACK", "Back")])

    if state in (State.BOOKING_TIME, State.RESCHEDULE_TIME):
        slots = data.get("slots", [])
        options = [(str(i), label) for i, (_, label) in enumerate(slots, 1)]
        what = data.get("service_name", "your appointment")
        return BotReply(f"{prefix}Which time would you like to request for {what}? Reply with a number:\n"
                        f"{_numbered(options)}", state, data, options + [("BACK", "Back")])

    if state == State.BOOKING_NAME:
        return BotReply(f"{prefix}What name should we put on the request? (or reply SKIP)", state, data,
                        [("SKIP", "Skip")])

    if state in (State.RESCHEDULE_SELECT, State.CANCEL_SELECT):
        verb = "reschedule" if state == State.RESCHEDULE_SELECT else "cancel"
        options = [(str(i), f"{a.service_name}, {a.start_label} ({a.status.lower()})")
                   for i, a in enumerate(ctx.appointments, 1)]
        return BotReply(f"{prefix}Which request would you like to {verb}? Reply with a number:\n{_numbered(options)}",
                        state, data, options + [("BACK", "Back")])

    if state == State.CANCEL_CONFIRM:
        options = [("1", "Yes, cancel it"), ("2", "No, keep it")]
        return BotReply(f"{prefix}Cancel {data.get('appointment_label', 'this request')}?\n{_numbered(options)}",
                        state, data, options)

    if state == State.PAYMENT_INFO:
        options = [("0", "Back to menu")]
        return BotReply(f"{prefix}{ctx.payment_info}\n\n(Demo only: no payments are taken in this simulator "
                        f"and we never ask for card details in chat.)\n\n{_numbered(options)}", state, data, options)

    if state == State.COMPLETED:
        options = list(MAIN_MENU_OPTIONS)
        return BotReply(f"{prefix}Anything else? Reply with a number:\n{_numbered(options)}", state, data, options)

    raise ValueError(f"Bot has no prompt for state {state}")


# ---------- handling input ----------

def _choice(text: str, count: int) -> int | None:
    """'2', ' 2 ' or '2.' -> 2 when 1 <= 2 <= count, else None."""
    cleaned = text.strip().rstrip(".)")
    if cleaned.isdigit():
        n = int(cleaned)
        if 1 <= n <= count:
            return n
    return None


def _invalid(state: State, ctx: BotContext, data: dict) -> BotReply:
    return render(state, ctx, data, intro="Sorry, I didn't understand that.")


def _handoff(data: dict, reason: str) -> BotReply:
    return BotReply(
        "Thanks. A member of our team will reply here as soon as they can. "
        "The automated assistant is paused until then.",
        State.PENDING_HANDOFF, _keep(data), [], [RequestHandoff(reason)],
    )


def _start_booking(ctx: BotContext, data: dict) -> BotReply:
    if not ctx.services:
        return render(State.MAIN_MENU, ctx, data,
                      intro="Sorry, there are no services available to book right now. Reply 6 to talk to a person.")
    return render(State.BOOKING_SERVICE, ctx, _keep(data))


def _offer_times(ctx: BotContext, data: dict, service: ServiceOption, state: State, back_state: State,
                 **extra) -> BotReply:
    slots = ctx.find_slots(service.id, extra.get("appointment_id"))
    if not slots:
        return render(back_state, ctx, data,
                      intro=f"Sorry, there are no open times for {service.name} in the next 7 days. "
                            "Reply HUMAN to ask our team directly.")
    new_data = _keep(data, service_id=service.id, service_name=service.name,
                     slots=[[s.start_at, s.label] for s in slots], **extra)
    return render(state, ctx, new_data)


def _finish_booking(ctx: BotContext, data: dict, name: str | None) -> BotReply:
    start_at, label = data["chosen_slot"]
    name = name or data.get("name") or ctx.customer_name
    action = CreateAppointment(data["service_id"], start_at, customer_name=name)
    lead = RecordLead(enquiry=f"Appointment request: {data['service_name']}", service_id=data["service_id"])
    text = (f"Thanks{', ' + name if name else ''}! Your request for {data['service_name']} on {label} "
            f"is saved as PENDING.\n{PENDING_NOTE}\n\n{AFTER_DONE}")
    return BotReply(text, State.COMPLETED, _keep(data, name=name) if name else _keep(data),
                    list(MAIN_MENU_OPTIONS), [action, lead])


def handle(ctx: BotContext, state: State | str, data: dict, text: str) -> BotReply:
    state = State(state)
    data = dict(data or {})
    raw = (text or "").strip()
    word = raw.upper()

    # Global commands, available from every state.
    if word in {"HUMAN", "AGENT", "PERSON"}:
        return _handoff(data, reason=f"Customer typed {word}")
    if word == "MENU":
        return _main_menu(ctx, data)
    if word == "HELP":
        return render(state, ctx, data, intro=f"Reply with the number of an option. {COMMANDS_HINT}")
    if word == "BACK":
        target = BACK_TO.get(state, State.MAIN_MENU)
        if target in (State.BOOKING_TIME, State.RESCHEDULE_TIME) and not data.get("slots"):
            target = State.MAIN_MENU
        if target in (State.RESCHEDULE_SELECT, State.CANCEL_SELECT) and not ctx.appointments:
            target = State.MAIN_MENU
        return render(target, ctx, data)

    if state == State.MAIN_MENU:
        if not data.get("greeted"):
            data["greeted"] = True
            if _choice(raw, len(MAIN_MENU_OPTIONS)) is None:
                return _main_menu(ctx, data, intro=f"Hi! Welcome to {ctx.business_name}.\n{COMMANDS_HINT}")
        n = _choice(raw, len(MAIN_MENU_OPTIONS))
        if n is None:
            return _invalid(state, ctx, data)
        if n == 1:
            return _start_booking(ctx, data)
        if n == 2:
            return render(State.SERVICE_LIST, ctx, _keep(data))
        if n in (3, 4):
            if not ctx.appointments:
                return render(State.MAIN_MENU, ctx, data,
                              intro="You don't have any open appointment requests with us.")
            return render(State.RESCHEDULE_SELECT if n == 3 else State.CANCEL_SELECT, ctx, _keep(data))
        if n == 5:
            return render(State.PAYMENT_INFO, ctx, _keep(data))
        return _handoff(data, reason="Customer chose 'Talk to a person'")

    if state == State.SERVICE_LIST:
        if raw.strip() == "0":
            return _main_menu(ctx, data)
        if _choice(raw, 1) == 1:
            return _start_booking(ctx, data)
        return _invalid(state, ctx, data)

    if state == State.PAYMENT_INFO:
        if raw.strip() == "0":
            return _main_menu(ctx, data)
        return _invalid(state, ctx, data)

    if state == State.BOOKING_SERVICE:
        n = _choice(raw, len(ctx.services))
        if n is None:
            return _invalid(state, ctx, data)
        return _offer_times(ctx, data, ctx.services[n - 1], State.BOOKING_TIME, State.BOOKING_SERVICE)

    if state == State.BOOKING_TIME:
        slots = data.get("slots", [])
        n = _choice(raw, len(slots))
        if n is None:
            return _invalid(state, ctx, data)
        data["chosen_slot"] = slots[n - 1]
        if data.get("name") or ctx.customer_name:
            return _finish_booking(ctx, data, None)
        return render(State.BOOKING_NAME, ctx, data)

    if state == State.BOOKING_NAME:
        if word == "SKIP":
            return _finish_booking(ctx, data, None)
        name = " ".join(raw.split())
        if not name or len(name) > MAX_NAME_LENGTH or not any(c.isalpha() for c in name):
            return render(state, ctx, data,
                          intro=f"Please send a name of up to {MAX_NAME_LENGTH} letters, or reply SKIP.")
        return _finish_booking(ctx, data, name)

    if state in (State.RESCHEDULE_SELECT, State.CANCEL_SELECT):
        n = _choice(raw, len(ctx.appointments))
        if n is None:
            return _invalid(state, ctx, data)
        appt = ctx.appointments[n - 1]
        if state == State.CANCEL_SELECT:
            return render(State.CANCEL_CONFIRM, ctx,
                          _keep(data, appointment_id=appt.id,
                                appointment_label=f"{appt.service_name} on {appt.start_label}"))
        service = next((s for s in ctx.services if s.id == appt.service_id), None)
        if service is None:
            return render(State.MAIN_MENU, ctx, data,
                          intro="That service is no longer offered online. Reply 6 to talk to a person.")
        return _offer_times(ctx, data, service, State.RESCHEDULE_TIME, State.RESCHEDULE_SELECT,
                            appointment_id=appt.id)

    if state == State.RESCHEDULE_TIME:
        slots = data.get("slots", [])
        n = _choice(raw, len(slots))
        if n is None:
            return _invalid(state, ctx, data)
        start_at, label = slots[n - 1]
        action = CreateAppointment(data["service_id"], start_at, reschedule_of=data["appointment_id"])
        return BotReply(f"Thanks! Your request to move {data['service_name']} to {label} is saved as PENDING. "
                        f"Your current time stays in place until our team confirms the change.\n\n{AFTER_DONE}",
                        State.COMPLETED, _keep(data), list(MAIN_MENU_OPTIONS), [action])

    if state == State.CANCEL_CONFIRM:
        n = _choice(raw, 2)
        if n == 1:
            return BotReply(f"Your request for {data['appointment_label']} has been cancelled. "
                            f"Our team can see the cancellation.\n\n{AFTER_DONE}",
                            State.COMPLETED, _keep(data), list(MAIN_MENU_OPTIONS),
                            [CancelAppointment(data["appointment_id"])])
        if n == 2:
            return _main_menu(ctx, data, intro="No problem, we've kept it.")
        return _invalid(state, ctx, data)

    if state == State.COMPLETED:
        # A number here is read as a main-menu choice, so "4" right after booking still means Cancel.
        if _choice(raw, len(MAIN_MENU_OPTIONS)) is not None:
            return handle(ctx, State.MAIN_MENU, {**data, "greeted": True}, raw)
        return _main_menu(ctx, data)

    # PENDING_HANDOFF and anything unexpected: stay quiet is decided by the caller; here, reset safely.
    return _main_menu(ctx, data)
