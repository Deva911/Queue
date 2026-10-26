"""Each Streamlit page loads without errors against a fresh demo database."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["app.py", "pages/0_Home.py", "pages/1_Business_Profile.py", "pages/2_Services.py", "pages/3_Chat_Simulator.py",
         "pages/4_Leads_Appointments.py"]


@pytest.fixture(autouse=True)
def temp_database(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'ui.db').as_posix()}")


@pytest.mark.parametrize("page", PAGES)
def test_page_loads(page):
    at = AppTest.from_file(str(ROOT / page), default_timeout=30).run()
    assert not at.exception, at.exception
    assert any("Local simulator" in i.value for i in at.info)


def test_chat_page_replies_to_a_typed_message():
    at = AppTest.from_file(str(ROOT / "pages/3_Chat_Simulator.py"), default_timeout=30).run()
    at.chat_input[0].set_value("hi").run()
    assert not at.exception
    assert any("Welcome to" in t.value for t in at.text)
    labels = [b.label for b in at.button]
    assert "1. Book an appointment" in labels and "6. Talk to a person" in labels


def test_sign_up_creates_business():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    at.text_input[0].set_value("Test Yoga Studio")
    at.button[0].click().run()
    assert not at.exception
    assert any("Created Test Yoga Studio" in s.value for s in at.success)
