"""Sign-in and who may do what: platform admin, OWNER, STAFF."""

from datetime import timedelta

import pytest

from whatsapp_manager import repositories as repo
from whatsapp_manager.models import AuthError, ValidationError
from whatsapp_manager.services import auth_service as auth
from whatsapp_manager.services.auth_service import Permission as P

from .conftest import NOW

PASSWORD = "correct horse battery"


@pytest.fixture
def admin(conn):
    uid = auth.create_first_admin(conn, "deva@example.com", "Deva", PASSWORD)
    return auth.load_actor(conn, uid)


@pytest.fixture
def team(conn, admin, clinic, salon):
    """Clinic owner and clinic staff; the salon has its own owner."""
    owner = auth.add_member(conn, admin, clinic["id"], "owner@clinic.example", "Olivia", "OWNER", PASSWORD)
    staff = auth.add_member(conn, auth.load_actor(conn, owner), clinic["id"], "sam@clinic.example", "Sam", "STAFF",
                            PASSWORD)
    salon_owner = auth.add_member(conn, admin, salon["id"], "owner@salon.example", "Sal", "OWNER", PASSWORD)
    return {k: auth.load_actor(conn, v) for k, v in
            {"owner": owner, "staff": staff, "salon_owner": salon_owner}.items()}


def test_passwords_are_hashed_with_a_salt(conn, admin):
    stored = repo.get_user(conn, admin.user_id)["password_hash"]
    assert PASSWORD not in stored and stored.startswith("scrypt$")
    assert auth.hash_password(PASSWORD) != auth.hash_password(PASSWORD)
    assert auth.verify_password(PASSWORD, stored) and not auth.verify_password("wrong password!", stored)


def test_sign_in_with_right_and_wrong_password(conn, admin):
    assert auth.authenticate(conn, " DEVA@example.com ", PASSWORD, NOW).user_id == admin.user_id
    with pytest.raises(AuthError, match="Email or password is wrong"):
        auth.authenticate(conn, "deva@example.com", "not the password", NOW)
    with pytest.raises(AuthError, match="Email or password is wrong"):  # same message for unknown emails
        auth.authenticate(conn, "nobody@example.com", PASSWORD, NOW)


def test_account_locks_after_five_wrong_passwords(conn, admin):
    for _ in range(auth.MAX_FAILED_LOGINS):
        with pytest.raises(AuthError):
            auth.authenticate(conn, "deva@example.com", "not the password", NOW)
    with pytest.raises(AuthError, match="Too many wrong passwords"):
        auth.authenticate(conn, "deva@example.com", PASSWORD, NOW)  # even the right one, for now
    assert auth.authenticate(conn, "deva@example.com", PASSWORD, NOW + timedelta(minutes=16))


def test_only_the_very_first_user_can_make_themselves_admin(conn, admin):
    assert not auth.needs_first_admin(conn)
    with pytest.raises(AuthError):
        auth.create_first_admin(conn, "mallory@example.com", "Mallory", PASSWORD)


def test_short_passwords_are_refused(conn):
    with pytest.raises(ValidationError, match="at least 10"):
        auth.create_first_admin(conn, "deva@example.com", "Deva", "short")


def test_disabled_user_is_signed_out_and_cannot_sign_in(conn, team):
    repo.update_user(conn, team["staff"].user_id, {"status": "DISABLED"})
    assert auth.load_actor(conn, team["staff"].user_id) is None
    with pytest.raises(AuthError):
        auth.authenticate(conn, "sam@clinic.example", PASSWORD, NOW)


@pytest.mark.parametrize("permission, owner_ok, staff_ok", [
    (P.VIEW_DASHBOARD, True, True),
    (P.USE_SIMULATOR, True, True),
    (P.HANDLE_REQUESTS, True, True),
    (P.EDIT_BUSINESS, True, False),
    (P.EDIT_SERVICES, True, False),
    (P.MANAGE_TEAM, True, False),
    (P.VIEW_AUDIT, True, False),
    (P.EXPORT_DATA, True, False),
    (P.DELETE_OLD_MESSAGES, True, False),
])
def test_role_permissions_in_own_business(team, clinic, permission, owner_ok, staff_ok):
    assert team["owner"].can(clinic["id"], permission) is owner_ok
    assert team["staff"].can(clinic["id"], permission) is staff_ok


@pytest.mark.parametrize("permission", list(P))
def test_nobody_can_touch_another_business(team, salon, clinic, permission):
    assert not team["owner"].can(salon["id"], permission)
    assert not team["staff"].can(salon["id"], permission)
    assert not team["salon_owner"].can(clinic["id"], permission)
    with pytest.raises(AuthError):
        auth.require(team["owner"], salon["id"], permission)


def test_platform_admin_can_act_in_every_business(admin, clinic, salon):
    assert all(admin.can(b, p) for b in (clinic["id"], salon["id"]) for p in P)
    auth.require_platform_admin(admin)


def test_signed_out_visitor_can_do_nothing(clinic):
    with pytest.raises(AuthError, match="sign in"):
        auth.require(None, clinic["id"], P.VIEW_DASHBOARD)
    with pytest.raises(AuthError):
        auth.require_platform_admin(None)


def test_staff_cannot_add_people(conn, team, clinic):
    with pytest.raises(AuthError):
        auth.add_member(conn, team["staff"], clinic["id"], "eve@example.com", "Eve", "OWNER", PASSWORD)


def test_owner_cannot_add_people_to_another_business(conn, team, salon):
    with pytest.raises(AuthError):
        auth.add_member(conn, team["owner"], salon["id"], "eve@example.com", "Eve", "STAFF", PASSWORD)


def test_adding_an_existing_person_does_not_change_their_password(conn, team, salon):
    before = repo.get_user(conn, team["staff"].user_id)["password_hash"]
    auth.add_member(conn, team["salon_owner"], salon["id"], "sam@clinic.example", "", "STAFF", "attacker-chosen-pw")
    assert repo.get_user(conn, team["staff"].user_id)["password_hash"] == before
    assert auth.authenticate(conn, "sam@clinic.example", PASSWORD, NOW)


def test_visible_businesses(conn, admin, team, clinic, salon):
    assert {b["id"] for b in auth.visible_businesses(conn, admin)} == {clinic["id"], salon["id"]}
    assert [b["id"] for b in auth.visible_businesses(conn, team["staff"])] == [clinic["id"]]


def test_removing_someone_takes_effect_on_their_next_page_load(conn, team, clinic):
    auth.remove_member(conn, team["owner"], clinic["id"], team["staff"].user_id)
    reloaded = auth.load_actor(conn, team["staff"].user_id)
    assert not reloaded.can(clinic["id"], P.VIEW_DASHBOARD)
    assert repo.list_audit(conn, clinic["id"])[0]["event_type"] == "MEMBER_REMOVED"


def test_last_owner_cannot_be_removed(conn, team, clinic):
    with pytest.raises(ValidationError, match="at least one owner"):
        auth.remove_member(conn, team["owner"], clinic["id"], team["owner"].user_id)


def test_change_password(conn, team):
    with pytest.raises(AuthError):
        auth.change_password(conn, team["staff"], "wrong current pw", "a brand new password")
    auth.change_password(conn, team["staff"], PASSWORD, "a brand new password")
    assert auth.authenticate(conn, "sam@clinic.example", "a brand new password", NOW)
