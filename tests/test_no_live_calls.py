"""Phase 1 makes no network calls: the conftest blocks sockets for every test, and nothing imports an HTTP client."""

import ast
from pathlib import Path

from whatsapp_manager.integrations.calendar import FakeCalendar
from whatsapp_manager.integrations.payments import FakePayments
from whatsapp_manager.integrations.whatsapp import FakeWhatsAppSender

SRC = Path(__file__).resolve().parents[1] / "src"
NETWORK_MODULES = {"requests", "httpx", "urllib", "http", "aiohttp", "socket", "stripe", "supabase", "googleapiclient"}


def test_source_imports_no_network_libraries():
    offenders = []
    for path in SRC.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module]
            offenders += [f"{path.name}: {n}" for n in names if n.split(".")[0] in NETWORK_MODULES]
    assert offenders == []


def test_fake_integrations_never_claim_success():
    assert FakeCalendar().is_connected() is False
    assert FakePayments().is_connected() is False
    sender = FakeWhatsAppSender()
    assert sender.send_text("+1", "hi").startswith("simulated-")
    assert sender.sent == [("+1", "hi")]
