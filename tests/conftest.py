import socket
from datetime import datetime, timezone

import pytest

from whatsapp_manager.database import connect
from whatsapp_manager.services.business_service import BusinessInput, ServiceInput, add_service, create_business

# Monday 26 Oct 2026, 09:30 in Asia/Kolkata.
NOW = datetime(2026, 10, 26, 4, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Phase 1 must never call Meta, a calendar or a payment provider. Any socket connect fails the test."""
    def refuse(*args, **kwargs):
        raise AssertionError("Network access attempted during tests")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


@pytest.fixture
def conn():
    c = connect(":memory:")
    yield c
    c.close()


@pytest.fixture
def clinic(conn):
    bid = create_business(conn, BusinessInput(name="Test Clinic", timezone="Asia/Kolkata",
                                              payment_info="Pay at the desk."))
    checkup = add_service(conn, bid, ServiceInput("Check-up", "Quick exam", "800", "INR", 30))
    filling = add_service(conn, bid, ServiceInput("Filling", None, "1500.50", "INR", 60))
    return {"id": bid, "checkup": checkup, "filling": filling}


@pytest.fixture
def salon(conn):
    bid = create_business(conn, BusinessInput(name="Test Salon", timezone="Asia/Kolkata"))
    haircut = add_service(conn, bid, ServiceInput("Haircut", None, "350", "INR", 30))
    return {"id": bid, "haircut": haircut}


@pytest.fixture
def say(conn):
    """say(business_id, text, customer="+911") -> ChatResult, using the fixed NOW."""
    from whatsapp_manager.services.conversation_service import handle_inbound

    def _say(business_id, text, customer="+91 90000 00001", now=NOW):
        return handle_inbound(conn, business_id, customer, text, now)
    return _say
