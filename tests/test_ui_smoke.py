"""Each Streamlit page loads, and signs people in and keeps them to their role, against a fresh demo database."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from whatsapp_manager import repositories as repo
from whatsapp_manager.database import connect
from whatsapp_manager.seed import seed_demo
from whatsapp_manager.services import auth_service as auth

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["app.py", "pages/0_Home.py", "pages/1_Business_Profile.py", "pages/2_Services.py", "pages/3_Chat_Simulator.py",
         "pages/4_Leads_Appointments.py", "pages/5_Team.py"]
PASSWORD = "correct horse battery"


@pytest.fixture(autouse=True)
def db(tmp_path, monkeypatch):
    path = tmp_path / "ui.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{path.as_posix()}")
    conn = connect(path)
    seed_demo(conn)
    yield conn
    conn.close()


@pytest.fixture
def admin_id(db):
    return auth.create_first_admin(db, "deva@example.com", "Deva", PASSWORD)


@pytest.fixture
def staff_id(db, admin_id):
    business = repo.list_businesses(db)[0]
    return auth.add_member(db, auth.load_actor(db, admin_id), business["id"], "sam@example.com", "Sam", "STAFF",
                           PASSWORD)


def app(page: str, user_id: str | None = None) -> AppTest:
    at = AppTest.from_file(str(ROOT / page), default_timeout=30)
    if user_id:
        at.session_state["user_id"] = user_id
    return at.run()


@pytest.mark.parametrize("page", PAGES)
def test_page_loads_for_the_platform_admin(page, admin_id):
    at = app(page, admin_id)
    assert not at.exception, at.exception
    assert any("Local simulator" in i.value for i in at.info)


@pytest.mark.parametrize("page", PAGES)
def test_signed_out_visitor_only_sees_sign_in(page, admin_id):
    at = app(page)
    assert not at.exception, at.exception
    assert [s.value for s in at.subheader] == ["Sign in"]
    assert not at.info  # none of the page itself was shown


def test_first_visit_sets_up_the_platform_admin(db):
    at = app("app.py")
    assert [s.value for s in at.subheader] == ["Set up the platform admin"]
    at.text_input[0].set_value("Deva")
    at.text_input[1].set_value("deva@example.com")
    at.text_input[2].set_value(PASSWORD)
    at.button[0].click().run()
    assert not at.exception
    assert any("Signed in as **Deva**" in c.value for c in at.sidebar.caption)


def test_sign_in_with_email_and_password(admin_id):
    at = app("app.py")
    at.text_input[0].set_value("deva@example.com")
    at.text_input[1].set_value("wrong password")
    at.button[0].click().run()
    assert any("Email or password is wrong" in e.value for e in at.error)
    at.text_input[1].set_value(PASSWORD)
    at.button[0].click().run()
    assert at.session_state["user_id"] == admin_id


@pytest.mark.parametrize("page", ["pages/1_Business_Profile.py", "pages/2_Services.py", "pages/5_Team.py"])
def test_staff_are_stopped_on_owner_pages(page, staff_id):
    at = app(page, staff_id)
    assert not at.exception
    assert any("don't have access" in e.value for e in at.error)
    assert not at.button or all(b.label == "Sign out" for b in at.button)


def test_staff_see_only_their_business_and_no_audit_or_export(db, staff_id):
    at = app("pages/4_Leads_Appointments.py", staff_id)
    assert not at.exception
    assert at.sidebar.selectbox[0].options == [repo.list_businesses(db)[0]["name"]]
    infos = [i.value for i in at.info]
    assert "Only owners can see the audit log." in infos and "Only owners can export customer data." in infos


def test_chat_page_replies_to_a_typed_message(admin_id):
    at = app("pages/3_Chat_Simulator.py", admin_id)
    at.chat_input[0].set_value("hi").run()
    assert not at.exception
    assert any("Welcome to" in t.value for t in at.text)
    labels = [b.label for b in at.button]
    assert "1. Book an appointment" in labels and "6. Talk to a person" in labels


def test_admin_creates_business(admin_id):
    at = app("pages/0_Home.py", admin_id)
    at.text_input[0].set_value("Test Yoga Studio")
    next(b for b in at.button if b.label == "Create business").click().run()
    assert not at.exception
    assert any("Created Test Yoga Studio" in s.value for s in at.success)


def test_staff_cannot_create_a_business(staff_id):
    at = app("pages/0_Home.py", staff_id)
    assert "Create business" not in [b.label for b in at.button]


def test_owner_adds_staff_on_the_team_page(db, admin_id):
    at = app("pages/5_Team.py", admin_id)
    for i, value in enumerate(["Priya", "priya@example.com"]):
        at.text_input[i].set_value(value)
    at.text_input[2].set_value(PASSWORD)
    next(b for b in at.button if b.label == "Add to team").click().run()
    assert not at.exception
    assert any("Added priya@example.com as Staff" in s.value for s in at.success)
    assert auth.authenticate(db, "priya@example.com", PASSWORD)
