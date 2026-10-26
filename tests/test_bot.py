"""The bot is a plain function, so these tests need no database."""

import pytest

from whatsapp_manager.models import Slot, State
from whatsapp_manager.services import bot

SLOTS = [Slot("2026-10-27T10:00:00+05:30", "Tue 27 Oct, 10:00"), Slot("2026-10-27T10:30:00+05:30", "Tue 27 Oct, 10:30")]


def make_ctx(**overrides):
    values = dict(
        business_name="Test Clinic",
        services=[bot.ServiceOption("s1", "Check-up", "Quick exam", 80000, "INR", 30),
                  bot.ServiceOption("s2", "Filling", None, None, None, None)],
        payment_info="Pay at the desk.",
        find_slots=lambda service_id, moving=None: list(SLOTS),
        appointments=[bot.AppointmentOption("a1", "s1", "Check-up", "Wed 28 Oct, 11:00", "PENDING")],
    )
    values.update(overrides)
    return bot.BotContext(**values)


def run(ctx, messages, state=State.MAIN_MENU, data=None):
    data = data or {}
    reply = None
    for text in messages:
        reply = bot.handle(ctx, state, data, text)
        state, data = reply.state, reply.data
    return reply


def test_first_message_greets_with_numbered_menu():
    reply = run(make_ctx(), ["hi"])
    assert reply.state == State.MAIN_MENU
    assert "Welcome to Test Clinic" in reply.text
    for number, label in bot.MAIN_MENU_OPTIONS:
        assert f"{number}. {label}" in reply.text
    assert [v for v, _ in reply.options] == ["1", "2", "3", "4", "5", "6"]


def test_services_and_prices():
    reply = run(make_ctx(), ["hi", "2"])
    assert reply.state == State.SERVICE_LIST
    assert "Check-up: INR 800.00, 30 min" in reply.text
    assert "Filling: Price on request" in reply.text
    assert run(make_ctx(), ["hi", "2", "0"]).state == State.MAIN_MENU


@pytest.mark.parametrize("text", ["7", "0", "abc", "1 2", "-1", "book"])
def test_invalid_menu_input_keeps_state(text):
    reply = run(make_ctx(), ["hi", text])
    assert reply.state == State.MAIN_MENU
    assert reply.text.startswith("Sorry, I didn't understand")
    assert reply.actions == []


def test_number_variants_are_accepted():
    assert run(make_ctx(), ["hi", " 2. "]).state == State.SERVICE_LIST


def test_booking_flow_creates_pending_request_and_lead():
    reply = run(make_ctx(), ["hi", "1", "1", "2", "Asha"])
    assert reply.state == State.COMPLETED
    create, lead = reply.actions
    assert create == bot.CreateAppointment("s1", SLOTS[1].start_at, customer_name="Asha")
    assert lead.service_id == "s1"
    assert "PENDING" in reply.text and "not a confirmed booking" in reply.text
    assert "confirmed" not in reply.text.replace("not a confirmed booking", "")


def test_booking_skips_name_when_already_known():
    reply = run(make_ctx(customer_name="Ravi"), ["hi", "1", "1", "1"])
    assert reply.state == State.COMPLETED
    assert reply.actions[0].customer_name == "Ravi"


def test_name_step_validates_and_allows_skip():
    reply = run(make_ctx(), ["hi", "1", "1", "1", "12345"])
    assert reply.state == State.BOOKING_NAME and reply.actions == []
    reply = run(make_ctx(), ["hi", "1", "1", "1", "x" * 81])
    assert reply.state == State.BOOKING_NAME
    reply = run(make_ctx(), ["hi", "1", "1", "1", "skip"])
    assert reply.state == State.COMPLETED and reply.actions[0].customer_name is None


def test_invalid_time_choice_keeps_offered_times():
    reply = run(make_ctx(), ["hi", "1", "1", "9"])
    assert reply.state == State.BOOKING_TIME
    assert "Tue 27 Oct, 10:00" in reply.text


def test_back_steps_back_one_level():
    assert run(make_ctx(), ["hi", "1", "1", "BACK"]).state == State.BOOKING_SERVICE
    assert run(make_ctx(), ["hi", "1", "BACK"]).state == State.MAIN_MENU
    assert run(make_ctx(), ["hi", "1", "1", "1", "back"]).state == State.BOOKING_TIME


def test_menu_and_help_work_everywhere():
    assert run(make_ctx(), ["hi", "1", "1", "MENU"]).state == State.MAIN_MENU
    reply = run(make_ctx(), ["hi", "1", "1", "help"])
    assert reply.state == State.BOOKING_TIME and "MENU" in reply.text and "HUMAN" in reply.text


@pytest.mark.parametrize("path", [[], ["2"], ["1"], ["1", "1"], ["1", "1", "1"], ["3"], ["4"], ["4", "1"], ["5"]])
def test_human_is_available_from_every_state(path):
    reply = run(make_ctx(), ["hi", *path, "HUMAN"])
    assert reply.state == State.PENDING_HANDOFF
    assert isinstance(reply.actions[0], bot.RequestHandoff)


def test_menu_option_6_hands_off():
    reply = run(make_ctx(), ["hi", "6"])
    assert reply.state == State.PENDING_HANDOFF and "paused" in reply.text


def test_payment_info_is_labelled_demo():
    reply = run(make_ctx(), ["hi", "5"])
    assert "Pay at the desk." in reply.text and "Demo only" in reply.text and "card details" in reply.text


def test_reschedule_creates_new_request_linked_to_original():
    reply = run(make_ctx(), ["hi", "3", "1", "2"])
    assert reply.state == State.COMPLETED
    assert reply.actions == [bot.CreateAppointment("s1", SLOTS[1].start_at, reschedule_of="a1")]
    assert "stays in place until our team confirms" in reply.text


def test_cancel_asks_for_confirmation():
    assert run(make_ctx(), ["hi", "4", "1", "2"]).actions == []
    reply = run(make_ctx(), ["hi", "4", "1", "1"])
    assert reply.actions == [bot.CancelAppointment("a1")]


def test_reschedule_and_cancel_without_requests():
    for option in ("3", "4"):
        reply = run(make_ctx(appointments=[]), ["hi", option])
        assert reply.state == State.MAIN_MENU and "don't have any open appointment requests" in reply.text


def test_no_services_and_no_slots_are_explained():
    reply = run(make_ctx(services=[]), ["hi", "1"])
    assert reply.state == State.MAIN_MENU and "no services available" in reply.text
    reply = run(make_ctx(find_slots=lambda *_: []), ["hi", "1", "1"])
    assert reply.state == State.BOOKING_SERVICE and "no open times" in reply.text


def test_number_after_completion_is_a_menu_choice():
    reply = run(make_ctx(), ["hi", "1", "1", "1", "skip", "4"])
    assert reply.state == State.CANCEL_SELECT
