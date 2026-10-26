"""End to end through the database: chat -> PENDING request -> staff decision, and human handoff."""

from datetime import datetime, timedelta

import pytest

from whatsapp_manager import repositories as repo
from whatsapp_manager.models import AppointmentStatus, ConversationStatus, State, ValidationError
from whatsapp_manager.services import appointment_service as appts
from whatsapp_manager.services import conversation_service as chat
from whatsapp_manager.services.business_service import BusinessInput, get_business, set_hours, update_business

from .conftest import NOW


def book(say, bid, customer="+91 90000 00001", slot="1", name="Asha"):
    say(bid, "hi", customer)
    say(bid, "1", customer)
    say(bid, "1", customer)  # Check-up
    say(bid, slot, customer)
    return say(bid, name, customer)


def test_booking_is_saved_as_pending_with_a_lead(conn, clinic, say):
    result = book(say, clinic["id"])
    assert result.state == State.COMPLETED
    (request,) = appts.list_requests(conn, clinic["id"])
    assert request["status"] == AppointmentStatus.PENDING
    assert request["service_id"] == clinic["checkup"]
    assert request["requested_start_at"] == "2026-10-26T10:00:00+05:30"  # first slot after 09:30 local
    assert request["customer_name"] == "Asha"
    (lead,) = repo.list_leads(conn, clinic["id"])
    assert (lead["status"], lead["name"], lead["service_id"]) == ("NEW", "Asha", clinic["checkup"])
    assert "APPOINTMENT_REQUESTED" in [e["event_type"] for e in repo.list_audit(conn, clinic["id"])]


def test_simulator_never_claims_a_calendar_booking(conn, clinic, say):
    texts = [say(clinic["id"], t).reply for t in ["hi", "1", "1", "1", "Asha"]]
    for text in texts:
        lowered = text.lower()
        assert "calendar" not in lowered
        assert "booked" not in lowered
        assert "confirmed" not in lowered.replace("not a confirmed booking", "")


def test_conversation_state_and_messages_persist(conn, clinic, say):
    result = say(clinic["id"], "hi")
    say(clinic["id"], "1")
    conversation = repo.get_conversation(conn, clinic["id"], result.conversation_id)
    assert conversation["state"] == State.BOOKING_SERVICE
    senders = [m["sender"] for m in repo.list_messages(conn, clinic["id"], result.conversation_id)]
    assert senders == ["CUSTOMER", "BOT", "CUSTOMER", "BOT"]


def test_slot_offered_to_two_customers_cannot_be_double_requested(conn, clinic, say):
    for customer in ("+1", "+2"):  # both see 10:00 as the first option
        say(clinic["id"], "hi", customer)
        say(clinic["id"], "1", customer)
        say(clinic["id"], "1", customer)
        say(clinic["id"], "1", customer)
    assert say(clinic["id"], "Ann", "+1").state == State.COMPLETED
    second = say(clinic["id"], "Ben", "+2")
    assert "just requested by someone else" in second.reply
    assert second.state == State.BOOKING_SERVICE
    assert len(appts.list_requests(conn, clinic["id"])) == 1
    assert len(repo.list_leads(conn, clinic["id"])) == 1  # failed attempt left nothing behind


def test_open_slots_respect_hours_closed_days_and_existing_requests(conn, clinic):
    bid = clinic["id"]
    slots = appts.find_open_slots(conn, bid, clinic["filling"], NOW, limit=100)
    starts = [datetime.fromisoformat(s.start_at) for s in slots]
    assert all(s.weekday() < 5 for s in starts)  # Sat and Sun closed by default
    assert all(9 <= s.hour and s + timedelta(minutes=60) <= s.replace(hour=17, minute=0) for s in starts)
    assert starts[0].isoformat() == "2026-10-26T10:00:00+05:30"  # 09:00 is already past at 09:30

    set_hours(conn, bid, 0, None, None, is_closed=True)  # close Mondays
    starts = [datetime.fromisoformat(s.start_at) for s in appts.find_open_slots(conn, bid, clinic["filling"], NOW)]
    assert all(s.weekday() != 0 for s in starts)


def test_customer_can_reschedule_and_staff_confirming_replaces_original(conn, clinic, say):
    bid = clinic["id"]
    book(say, bid)
    say(bid, "3")
    say(bid, "1")
    say(bid, "1")  # first open time for the move
    original, moved = sorted(appts.list_requests(conn, bid), key=lambda a: a["reschedule_of"] or "")
    assert moved["reschedule_of"] == original["id"]
    assert original["status"] == moved["status"] == AppointmentStatus.PENDING  # nothing changes until staff act

    appts.staff_set_status(conn, bid, moved["id"], AppointmentStatus.CONFIRMED, "See you then")
    assert repo.get_appointment(conn, bid, moved["id"])["status"] == AppointmentStatus.CONFIRMED
    assert repo.get_appointment(conn, bid, original["id"])["status"] == AppointmentStatus.CANCELLED


def test_customer_can_cancel(conn, clinic, say):
    bid = clinic["id"]
    book(say, bid)
    say(bid, "4")
    say(bid, "1")
    reply = say(bid, "1")
    assert "has been cancelled" in reply.reply
    assert appts.list_requests(conn, bid)[0]["status"] == AppointmentStatus.CANCELLED
    assert "you don't have any open appointment requests" in say(bid, "4").reply.lower()


def test_staff_decisions_follow_allowed_transitions_and_notify_customer(conn, clinic, say):
    bid = clinic["id"]
    result = book(say, bid)
    (request,) = appts.list_requests(conn, bid)
    appts.staff_set_status(conn, bid, request["id"], AppointmentStatus.DECLINED, "Fully booked")
    with pytest.raises(ValidationError, match="Can't change a DECLINED"):
        appts.staff_set_status(conn, bid, request["id"], AppointmentStatus.CONFIRMED)
    last = repo.list_messages(conn, bid, result.conversation_id)[-1]
    assert last["sender"] == "STAFF" and "could not be accepted" in last["body"] and "Fully booked" in last["body"]
    audit = repo.list_audit(conn, bid)[0]
    assert audit["event_type"] == "APPOINTMENT_DECLINED" and audit["actor"] == "staff (demo)"


def test_handoff_pauses_bot_until_staff_hands_back(conn, clinic, say):
    bid = clinic["id"]
    say(bid, "hi")
    result = say(bid, "HUMAN")
    assert result.status == ConversationStatus.PENDING_HANDOFF
    assert [c["id"] for c in chat.list_conversations(conn, bid, [ConversationStatus.PENDING_HANDOFF])] == \
        [result.conversation_id]

    quiet = say(bid, "hello? anyone?")
    assert quiet.reply is None  # bot stays silent
    assert chat.current_options(conn, bid, result.conversation_id) == []

    with pytest.raises(ValidationError):
        chat.staff_reply(conn, bid, result.conversation_id, "")
    chat.staff_reply(conn, bid, result.conversation_id, "Hi, this is Priya. How can I help?")
    assert repo.get_conversation(conn, bid, result.conversation_id)["status"] == ConversationStatus.HUMAN_ACTIVE
    assert say(bid, "2").reply is None  # still a person's chat; "2" is not treated as a menu choice

    chat.return_to_bot(conn, bid, result.conversation_id, "Answered question about parking")
    assert say(bid, "2").state == State.SERVICE_LIST

    events = [e["event_type"] for e in repo.list_audit(conn, bid)]
    for expected in ("HANDOFF_REQUESTED", "HANDOFF_ACCEPTED", "STAFF_REPLIED", "HANDOFF_RETURNED_TO_BOT"):
        assert expected in events
    bodies = [m["body"] for m in repo.list_messages(conn, bid, result.conversation_id)]
    assert "hello? anyone?" in bodies  # the customer's messages are still saved for staff


def test_staff_cannot_reply_over_the_bot(conn, clinic, say):
    result = say(clinic["id"], "hi")
    with pytest.raises(ValidationError, match="Take over"):
        chat.staff_reply(conn, clinic["id"], result.conversation_id, "hello")


def test_inactive_business_does_not_take_requests(conn, clinic, say):
    business = get_business(conn, clinic["id"])
    update_business(conn, clinic["id"], BusinessInput(business["name"], timezone=business["timezone"],
                                                      status="INACTIVE"))
    reply = say(clinic["id"], "1")
    assert "not taking messages" in reply.reply
    assert appts.list_requests(conn, clinic["id"]) == []


@pytest.mark.parametrize("text", ["", "   ", "x" * 501])
def test_bad_messages_are_rejected_without_changing_state(conn, clinic, say, text):
    say(clinic["id"], "hi")
    with pytest.raises(ValidationError):
        say(clinic["id"], text)
    assert say(clinic["id"], "2").state == State.SERVICE_LIST


def test_start_over_closes_chat(conn, clinic, say):
    first = say(clinic["id"], "hi")
    chat.close_for_customer(conn, clinic["id"], "+91 90000 00001")
    second = say(clinic["id"], "hi")
    assert second.conversation_id != first.conversation_id
    assert "Welcome" in second.reply


def test_rescheduling_is_not_blocked_by_the_request_being_moved(conn, clinic, say):
    bid = clinic["id"]
    for text in ["hi", "1", "2", "1", "Asha"]:  # 60-minute Filling at 10:00 (list is sorted: Check-up, Filling)
        say(bid, text)
    (request,) = appts.list_requests(conn, bid)
    assert request["service_id"] == clinic["filling"]
    others = [s.start_at for s in appts.find_open_slots(conn, bid, clinic["filling"], NOW)]
    mine = [s.start_at for s in appts.find_open_slots(conn, bid, clinic["filling"], NOW, exclude_id=request["id"])]
    assert "2026-10-26T10:00:00+05:30" not in others
    assert "2026-10-26T10:00:00+05:30" in mine
