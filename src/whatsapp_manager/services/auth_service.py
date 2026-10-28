"""Sign-in (authentication) and who may do what (authorization).

Three kinds of people sign in to the dashboard:
  - platform admin: runs the platform; creates businesses and their first owner; can act in any business
  - OWNER: runs one business; profile, services, hours and the team, plus everything staff can do
  - STAFF: handles requests, chats and leads for the businesses they belong to

Access comes only from the `memberships` table (and the admin flag), re-read on every page load, so
removing someone or changing their role takes effect at once. Pages call `require()` before showing
or doing anything; hiding a menu item is never the only check.

Swapping to Supabase Auth later replaces `authenticate()` and the password helpers. The roles,
permissions and `require()` stay the same.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import StrEnum

from .. import repositories as repo
from ..models import AuthError, Role, ValidationError

MIN_PASSWORD_LENGTH = 10
MAX_FAILED_LOGINS = 5
LOCKOUT = timedelta(minutes=15)
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SCRYPT = {"n": 2**14, "r": 8, "p": 1}
WRONG_LOGIN = "Email or password is wrong."  # same message whether the email exists or not


class Permission(StrEnum):
    VIEW_DASHBOARD = "VIEW_DASHBOARD"
    USE_SIMULATOR = "USE_SIMULATOR"
    HANDLE_REQUESTS = "HANDLE_REQUESTS"  # appointments, handoff inbox, leads
    EDIT_BUSINESS = "EDIT_BUSINESS"  # profile and opening hours
    EDIT_SERVICES = "EDIT_SERVICES"
    MANAGE_TEAM = "MANAGE_TEAM"
    VIEW_AUDIT = "VIEW_AUDIT"
    EXPORT_DATA = "EXPORT_DATA"
    DELETE_OLD_MESSAGES = "DELETE_OLD_MESSAGES"


STAFF_PERMISSIONS = frozenset({Permission.VIEW_DASHBOARD, Permission.USE_SIMULATOR, Permission.HANDLE_REQUESTS})
ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    Role.STAFF: STAFF_PERMISSIONS,
    Role.OWNER: frozenset(Permission),
}


@dataclass(frozen=True)
class Actor:
    """The signed-in person, as loaded from the database for this page load."""
    user_id: str
    email: str
    display_name: str
    is_platform_admin: bool
    roles: dict[str, str] = field(default_factory=dict)  # business_id -> OWNER / STAFF

    @property
    def label(self) -> str:
        """How this person appears in the audit log."""
        return f"{self.display_name} <{self.email}>"

    def role_in(self, business_id: str) -> str | None:
        return self.roles.get(business_id)

    def can(self, business_id: str, permission: Permission) -> bool:
        if self.is_platform_admin:
            return True
        role = self.roles.get(business_id)
        return role is not None and permission in ROLE_PERMISSIONS[role]


def require(actor: Actor | None, business_id: str, permission: Permission) -> None:
    if actor is None:
        raise AuthError("Please sign in.")
    if not actor.can(business_id, permission):
        raise AuthError("You don't have access to do that for this business.")


def require_platform_admin(actor: Actor | None) -> None:
    if actor is None or not actor.is_platform_admin:
        raise AuthError("Only a platform admin can do that.")


# ---------- passwords ----------

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return f"scrypt${_SCRYPT['n']}${_SCRYPT['r']}${_SCRYPT['p']}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
    except ValueError:
        return False
    if scheme != "scrypt":
        return False
    actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p))
    return hmac.compare_digest(actual, bytes.fromhex(digest))


def _check_new_password(password: str) -> None:
    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise ValidationError(f"Passwords must be at least {MIN_PASSWORD_LENGTH} characters.")


def _clean_email(email: str) -> str:
    email = (email or "").strip().lower()
    if not _EMAIL.match(email) or len(email) > 254:
        raise ValidationError("Please enter a valid email address.")
    return email


# ---------- signing in ----------

def _now(now: datetime | None) -> datetime:
    return now or datetime.now(timezone.utc)


def load_actor(conn: sqlite3.Connection, user_id: str | None) -> Actor | None:
    """Fresh from the database on every page load. A disabled or deleted user is signed out."""
    user = repo.get_user(conn, user_id) if user_id else None
    if user is None or user["status"] != "ACTIVE":
        return None
    roles = {m["business_id"]: m["role"] for m in repo.list_memberships_for_user(conn, user["id"])}
    return Actor(user["id"], user["email"], user["display_name"], bool(user["is_platform_admin"]), roles)


def authenticate(conn: sqlite3.Connection, email: str, password: str, now: datetime | None = None) -> Actor:
    now = _now(now)
    user = repo.get_user_by_email(conn, (email or "").strip().lower())
    if user is None:
        verify_password(password or "", hash_password("timing-equaliser"))  # don't reveal which emails exist
        raise AuthError(WRONG_LOGIN)
    if user["locked_until"] and datetime.fromisoformat(user["locked_until"]) > now:
        raise AuthError("Too many wrong passwords. Try again in 15 minutes.")
    if user["status"] != "ACTIVE" or not verify_password(password or "", user["password_hash"]):
        with conn:
            failed = user["failed_logins"] + 1
            locked = (now + LOCKOUT).isoformat(timespec="seconds") if failed >= MAX_FAILED_LOGINS else None
            repo.update_user(conn, user["id"], {"failed_logins": 0 if locked else failed, "locked_until": locked})
        raise AuthError(WRONG_LOGIN)
    with conn:
        repo.update_user(conn, user["id"], {"failed_logins": 0, "locked_until": None})
    return load_actor(conn, user["id"])


def needs_first_admin(conn: sqlite3.Connection) -> bool:
    return repo.count_users(conn) == 0


def create_first_admin(conn: sqlite3.Connection, email: str, display_name: str, password: str) -> str:
    """Only works while there are no users at all: the first person to set up the app becomes the admin."""
    email, display_name = _clean_email(email), (display_name or "").strip()
    if not display_name:
        raise ValidationError("Please enter your name.")
    _check_new_password(password)
    with conn:
        if not needs_first_admin(conn):
            raise AuthError("The platform admin has already been set up. Please sign in.")
        return repo.insert_user(conn, email=email, display_name=display_name, password_hash=hash_password(password),
                                is_platform_admin=True)


def change_password(conn: sqlite3.Connection, actor: Actor, current: str, new: str) -> None:
    user = repo.get_user(conn, actor.user_id)
    if user is None or not verify_password(current or "", user["password_hash"]):
        raise AuthError("Your current password is wrong.")
    _check_new_password(new)
    with conn:
        repo.update_user(conn, actor.user_id, {"password_hash": hash_password(new)})


# ---------- the team ----------

def add_member(conn: sqlite3.Connection, actor: Actor, business_id: str, email: str, display_name: str,
               role: str, temporary_password: str | None = None) -> str:
    """Give someone access to a business. New people get the temporary password to sign in with.

    Owners can add staff and other owners; only a platform admin can add the first owner.
    """
    require(actor, business_id, Permission.MANAGE_TEAM)
    if role not in {r.value for r in Role}:
        raise ValidationError("Role must be OWNER or STAFF.")
    email, display_name = _clean_email(email), (display_name or "").strip()
    with conn:
        user = repo.get_user_by_email(conn, email)
        if user is None:
            if not display_name:
                raise ValidationError("Please enter their name.")
            _check_new_password(temporary_password)
            user_id = repo.insert_user(conn, email=email, display_name=display_name,
                                       password_hash=hash_password(temporary_password), is_platform_admin=False)
        else:
            user_id = user["id"]
        repo.upsert_membership(conn, user_id, business_id, role)
        repo.insert_audit(conn, business_id, actor=actor.label, event_type="MEMBER_ADDED", entity_type="user",
                          entity_id=user_id, details={"email": email, "role": role})
    return user_id


def remove_member(conn: sqlite3.Connection, actor: Actor, business_id: str, user_id: str) -> None:
    require(actor, business_id, Permission.MANAGE_TEAM)
    members = repo.list_members(conn, business_id)
    target = next((m for m in members if m["user_id"] == user_id), None)
    if target is None:
        raise ValidationError("That person isn't on this team.")
    owners = [m for m in members if m["role"] == Role.OWNER]
    if target["role"] == Role.OWNER and len(owners) == 1:
        raise ValidationError("A business needs at least one owner. Add another owner first.")
    with conn:
        repo.delete_membership(conn, user_id, business_id)
        repo.insert_audit(conn, business_id, actor=actor.label, event_type="MEMBER_REMOVED", entity_type="user",
                          entity_id=user_id, details={"email": target["email"], "role": target["role"]})


def visible_businesses(conn: sqlite3.Connection, actor: Actor) -> list[dict]:
    """The businesses this person may open: all of them for a platform admin, their own otherwise."""
    return [b for b in repo.list_businesses(conn) if actor.is_platform_admin or b["id"] in actor.roles]
