import pytest

from whatsapp_manager import repositories as repo
from whatsapp_manager.database import connect
from whatsapp_manager.models import ValidationError
from whatsapp_manager.services.business_service import (
    BusinessInput,
    create_business,
    get_business,
    list_hours,
    set_hours,
    update_business,
)


def test_business_persists_after_restart(tmp_path):
    db = tmp_path / "app.db"
    first = connect(db)
    bid = create_business(first, BusinessInput(name="Brightsmile", category="Clinic", timezone="Asia/Kolkata"))
    first.close()

    second = connect(db)  # simulates restarting the app
    business = get_business(second, bid)
    assert business["name"] == "Brightsmile"
    assert business["status"] == "ACTIVE"
    second.close()


def test_sign_up_sets_default_hours_and_audit(conn):
    bid = create_business(conn, BusinessInput(name="Shop"))
    hours = list_hours(conn, bid)
    assert len(hours) == 7
    assert [h["is_closed"] for h in hours] == [0, 0, 0, 0, 0, 1, 1]
    assert hours[0]["opens_at"] == "09:00"
    assert repo.list_audit(conn, bid)[0]["event_type"] == "BUSINESS_CREATED"


@pytest.mark.parametrize("data, message", [
    (BusinessInput(name="   "), "Business name is required"),
    (BusinessInput(name="X", timezone="Mars/Olympus"), "not a recognised time zone"),
    (BusinessInput(name="X", contact_email="not-an-email"), "email"),
    (BusinessInput(name="X" * 201), "200 characters"),
    (BusinessInput(name="X", status="DELETED"), "Status"),
])
def test_bad_business_input_is_rejected(conn, data, message):
    with pytest.raises(ValidationError, match=message):
        create_business(conn, data)
    assert repo.list_businesses(conn) == []


def test_update_profile(conn):
    bid = create_business(conn, BusinessInput(name="Old"))
    update_business(conn, bid, BusinessInput(name="New name", contact_email="a@b.co", timezone="America/Toronto"))
    business = get_business(conn, bid)
    assert (business["name"], business["contact_email"], business["timezone"]) == ("New name", "a@b.co",
                                                                                 "America/Toronto")


def test_hours_validation(conn):
    bid = create_business(conn, BusinessInput(name="Shop"))
    with pytest.raises(ValidationError, match="after opening"):
        set_hours(conn, bid, 0, "17:00", "09:00", is_closed=False)
    with pytest.raises(ValidationError, match="time like"):
        set_hours(conn, bid, 0, "9am", "17:00", is_closed=False)
    set_hours(conn, bid, 6, "10:00", "13:00", is_closed=False)
    sunday = list_hours(conn, bid)[6]
    assert (sunday["opens_at"], sunday["closes_at"], sunday["is_closed"]) == ("10:00", "13:00", 0)
    set_hours(conn, bid, 6, "bad", "worse", is_closed=True)  # times ignored for a closed day
    assert list_hours(conn, bid)[6]["is_closed"] == 1
