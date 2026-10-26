import pytest

from whatsapp_manager import repositories as repo
from whatsapp_manager.models import ValidationError
from whatsapp_manager.services.business_service import (
    ServiceInput,
    add_service,
    format_price,
    list_services,
    parse_price,
    set_service_active,
    update_service,
)


@pytest.mark.parametrize("text, cents", [("450", 45000), ("450.5", 45050), ("1,500.25", 150025), ("0", 0),
                                         ("", None), ("  ", None)])
def test_price_is_stored_as_whole_cents(text, cents):
    assert parse_price(text) == cents


@pytest.mark.parametrize("text", ["-1", "abc", "1.234", "NaN", "Infinity"])
def test_bad_prices_are_rejected(text):
    with pytest.raises(ValidationError):
        parse_price(text)


def test_format_price():
    assert format_price(150050, "INR") == "INR 1,500.50"
    assert format_price(None, None) == "Price on request"


def test_add_edit_and_deactivate_service(conn, clinic):
    bid = clinic["id"]
    sid = add_service(conn, bid, ServiceInput("Whitening", "Bright", "6000", "inr", 60))
    service = repo.get_service(conn, bid, sid)
    assert (service["price_minor"], service["currency"], service["is_active"]) == (600000, "INR", 1)

    update_service(conn, bid, sid, ServiceInput("Whitening plus", None, "", None, None))
    service = repo.get_service(conn, bid, sid)
    assert (service["name"], service["price_minor"], service["currency"]) == ("Whitening plus", None, None)

    set_service_active(conn, bid, sid, False)
    assert sid not in [s["id"] for s in list_services(conn, bid, active_only=True)]
    assert sid in [s["id"] for s in list_services(conn, bid)]
    events = [e["event_type"] for e in repo.list_audit(conn, bid)]
    assert "SERVICE_DEACTIVATED" in events and "SERVICE_UPDATED" in events


@pytest.mark.parametrize("data, message", [
    (ServiceInput(""), "Service name is required"),
    (ServiceInput("X", price="10", currency=""), "Currency"),
    (ServiceInput("X", price="10", currency="RUPEES"), "Currency"),
    (ServiceInput("X", duration_minutes=0), "Duration"),
    (ServiceInput("X", duration_minutes=-5), "Duration"),
])
def test_bad_service_input_is_rejected(conn, clinic, data, message):
    with pytest.raises(ValidationError, match=message):
        add_service(conn, clinic["id"], data)


def test_database_refuses_negative_price_even_if_validation_is_bypassed(conn, clinic):
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        repo.insert_service(conn, clinic["id"], name="X", description=None, price_minor=-1, currency="INR",
                            duration_minutes=None)


def test_inactive_service_is_not_offered_in_chat(conn, clinic, say):
    set_service_active(conn, clinic["id"], clinic["filling"], False)
    reply = say(clinic["id"], "2").reply
    assert "Check-up" in reply and "Filling" not in reply
    reply = say(clinic["id"], "1").reply
    assert "Filling" not in reply
