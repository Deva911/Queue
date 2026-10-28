"""Phase 1 clean-up: closed requests, repeat leads, database settings, message retention."""

from datetime import timedelta

import pytest

from whatsapp_manager import repositories as repo
from whatsapp_manager.database import SCHEMA_VERSION, connect
from whatsapp_manager.models import AppointmentStatus, ValidationError
from whatsapp_manager.services import appointment_service as appts
from whatsapp_manager.services import conversation_service as chat

from .conftest import NOW
from .test_conversation_flow import book


def test_cannot_reschedule_a_request_that_is_already_closed(conn, clinic, say):
    bid = clinic["id"]
    book(say, bid)
    original = appts.list_requests(conn, bid)[0]
    appts.staff_set_status(conn, bid, original["id"], AppointmentStatus.DECLINED)
    later = appts.find_open_slots(conn, bid, clinic["checkup"], NOW)[3]
    with pytest.raises(ValidationError, match="already closed"):
        appts.create_request(conn, bid, original["customer_id"], clinic["checkup"], later.start_at, NOW,
                             reschedule_of=original["id"])


def test_same_customer_booking_same_service_twice_keeps_one_lead(conn, clinic, say):
    bid = clinic["id"]
    book(say, bid, slot="1")
    book(say, bid, slot="2")
    leads = repo.list_leads(conn, bid)
    assert len(leads) == 1
    assert len(appts.list_requests(conn, bid)) == 2  # both requests are still saved


def test_closed_lead_is_not_reused(conn, clinic, say):
    bid = clinic["id"]
    book(say, bid, slot="1")
    chat.set_lead_status(conn, bid, repo.list_leads(conn, bid)[0]["id"], "CLOSED")
    book(say, bid, slot="2")
    assert len(repo.list_leads(conn, bid)) == 2


def test_database_records_its_schema_version(tmp_path):
    c = connect(tmp_path / "app.db")
    assert c.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
    assert c.execute("PRAGMA journal_mode").fetchone()[0] == "wal"  # several browser tabs at once
    c.close()


def test_old_messages_are_deleted_after_the_retention_period(conn, clinic, salon, say):
    bid = clinic["id"]
    say(bid, "hi")
    say(salon["id"], "hi")
    old = (NOW - timedelta(days=40)).isoformat(timespec="seconds")
    conn.execute("UPDATE messages SET created_at = ?", (old,))  # both businesses' chats are 40 days old
    conn.commit()
    say(bid, "hi", customer="+91 90000 00009")  # a fresh chat
    deleted = chat.delete_old_messages(conn, bid, older_than_days=30, now=NOW)
    assert deleted == 2  # the old "hi" and the bot's reply
    remaining = [m for c in chat.list_conversations(conn, bid) for m in chat.list_messages(conn, bid, c["id"])]
    assert len(remaining) == 2
    salon_convo = chat.list_conversations(conn, salon["id"])[0]
    assert len(chat.list_messages(conn, salon["id"], salon_convo["id"])) == 2  # other business untouched
    assert repo.list_audit(conn, bid)[0]["event_type"] == "MESSAGES_DELETED"
