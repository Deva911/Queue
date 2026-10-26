"""One business must never see or change another business's records."""

import sqlite3

import pytest

from whatsapp_manager import repositories as repo
from whatsapp_manager.models import AppointmentStatus, NotFoundError, ValidationError
from whatsapp_manager.services import appointment_service as appts
from whatsapp_manager.services import conversation_service as chat
from whatsapp_manager.services import export_service
from whatsapp_manager.services.business_service import ServiceInput, set_service_active, update_service

from .conftest import NOW


@pytest.fixture
def both(conn, clinic, salon, say):
    """Same phone number chats to both businesses; each books once."""
    for bid in (clinic["id"], salon["id"]):
        for text in ["hi", "1", "1", "1", "Asha"]:
            say(bid, text)
    say(salon["id"], "HUMAN", "+44 7000 000000")
    return clinic, salon


def test_same_phone_number_is_a_separate_customer_per_business(conn, both):
    clinic, salon = both
    a = repo.get_customer_by_key(conn, clinic["id"], "+91 90000 00001")
    b = repo.get_customer_by_key(conn, salon["id"], "+91 90000 00001")
    assert a["id"] != b["id"]


def test_lists_only_return_own_records(conn, both):
    clinic, salon = both
    for lister in (repo.list_leads, repo.list_appointments, repo.list_conversations, repo.list_audit,
                   repo.list_services, repo.list_hours):
        clinic_rows, salon_rows = lister(conn, clinic["id"]), lister(conn, salon["id"])
        assert clinic_rows and salon_rows
        assert {r["business_id"] for r in clinic_rows} == {clinic["id"]}
        assert {r["business_id"] for r in salon_rows} == {salon["id"]}
    assert [c["external_customer_key"] for c in chat.list_conversations(conn, clinic["id"])] == ["+91 90000 00001"]


def test_service_from_another_business_cannot_be_booked(conn, both):
    clinic, salon = both
    customer = repo.get_customer_by_key(conn, clinic["id"], "+91 90000 00001")
    with pytest.raises(ValidationError, match="does not belong"):
        appts.create_request(conn, clinic["id"], customer["id"], salon["haircut"], "2026-10-27T10:00:00+05:30", NOW)
    # The database refuses it too, even if the service layer were bypassed.
    with pytest.raises(sqlite3.IntegrityError):
        repo.insert_appointment(conn, clinic["id"], customer["id"], service_id=salon["haircut"],
                                requested_start_at="2026-10-27T10:00:00+05:30", notes=None, reschedule_of=None,
                                status="PENDING")


def test_cannot_read_or_change_another_business_records(conn, both):
    clinic, salon = both
    salon_request = repo.list_appointments(conn, salon["id"])[0]
    salon_conversation = repo.list_conversations(conn, salon["id"])[0]
    salon_lead = repo.list_leads(conn, salon["id"])[0]

    assert repo.get_appointment(conn, clinic["id"], salon_request["id"]) is None
    assert repo.get_service(conn, clinic["id"], salon["haircut"]) is None
    with pytest.raises(NotFoundError):
        appts.staff_set_status(conn, clinic["id"], salon_request["id"], AppointmentStatus.CONFIRMED)
    with pytest.raises(NotFoundError):
        chat.take_over(conn, clinic["id"], salon_conversation["id"])
    with pytest.raises(NotFoundError):
        chat.staff_reply(conn, clinic["id"], salon_conversation["id"], "hi")
    with pytest.raises(NotFoundError):
        chat.set_lead_status(conn, clinic["id"], salon_lead["id"], "CLOSED")
    with pytest.raises(NotFoundError):
        set_service_active(conn, clinic["id"], salon["haircut"], False)
    with pytest.raises(NotFoundError):
        update_service(conn, clinic["id"], salon["haircut"], ServiceInput("Hijacked"))
    assert repo.list_messages(conn, clinic["id"], salon_conversation["id"]) == []

    assert repo.get_appointment(conn, salon["id"], salon_request["id"])["status"] == AppointmentStatus.PENDING
    assert repo.get_service(conn, salon["id"], salon["haircut"])["name"] == "Haircut"


def test_bookings_in_one_business_do_not_block_slots_in_another(conn, both):
    clinic, salon = both
    clinic_first = appts.find_open_slots(conn, clinic["id"], clinic["checkup"], NOW)[0]
    salon_first = appts.find_open_slots(conn, salon["id"], salon["haircut"], NOW)[0]
    assert clinic_first.start_at == salon_first.start_at == "2026-10-26T10:30:00+05:30"
    # Each business's own 10:00 request is what pushed its first open time to 10:30.


def test_csv_exports_only_contain_own_records(conn, both):
    clinic, salon = both
    clinic_leads = export_service.leads_csv(conn, clinic["id"])
    salon_leads = export_service.leads_csv(conn, salon["id"])
    assert "+44 7000 000000" in salon_leads and "+44 7000 000000" not in clinic_leads
    assert "Check-up" in export_service.appointments_csv(conn, clinic["id"])
    assert "Check-up" not in export_service.appointments_csv(conn, salon["id"])
    for row in clinic_leads.splitlines()[1:]:
        assert row.split(",")[0] in {lead["id"] for lead in repo.list_leads(conn, clinic["id"])}
