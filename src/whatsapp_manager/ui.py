"""Shared Streamlit helpers: database connection, sign-in gate, demo banner and the business selector."""

from __future__ import annotations

import sqlite3

import streamlit as st

from .config import get_settings
from .database import connect
from .models import AuthError, NotFoundError, ValidationError
from .seed import seed_demo
from .services import auth_service as auth
from .services.auth_service import Actor, Permission

DEMO_BANNER = ("**Local simulator.** No real WhatsApp messages, calendar bookings or payments. "
               "Use made-up data only.")


def get_conn() -> sqlite3.Connection:
    """One connection per script run (SQLite connections shouldn't be shared across Streamlit threads)."""
    conn = connect(get_settings().database_path)
    seed_demo(conn)
    return conn


def page_setup(title: str) -> sqlite3.Connection:
    """Every page starts here. Nobody gets past this line without signing in."""
    st.set_page_config(page_title=f"{title} · WhatsApp Manager", page_icon="💬", layout="wide")
    conn = get_conn()
    actor = current_actor(conn)
    if actor is None:
        sign_in_page(conn)
        st.stop()
    st.title(title)
    st.info(DEMO_BANNER, icon="🧪")
    message = st.session_state.pop("flash", None)
    if message:
        st.success(message)
    kind = "platform admin" if actor.is_platform_admin else actor.email
    st.sidebar.caption(f"Signed in as **{actor.display_name}** ({kind})")
    if st.sidebar.button("Sign out"):
        st.session_state.clear()
        st.rerun()
    return conn


def current_actor(conn: sqlite3.Connection) -> Actor | None:
    """Re-read from the database on every page load, so role changes and removals apply at once."""
    actor = auth.load_actor(conn, st.session_state.get("user_id"))
    if actor is None:
        st.session_state.pop("user_id", None)
    return actor


def actor(conn: sqlite3.Connection) -> Actor:
    found = current_actor(conn)
    if found is None:  # page_setup already stopped signed-out visitors
        st.stop()
    return found


def sign_in_page(conn: sqlite3.Connection) -> None:
    st.title("WhatsApp Manager")
    if auth.needs_first_admin(conn):
        st.subheader("Set up the platform admin")
        st.caption("No accounts exist yet. The account you create here can create businesses and add their owners.")
        with st.form("first_admin"):
            name = st.text_input("Your name")
            email = st.text_input("Email")
            password = st.text_input(f"Password (at least {auth.MIN_PASSWORD_LENGTH} characters)", type="password")
            submitted = st.form_submit_button("Create admin account")
        if submitted:
            try:
                st.session_state["user_id"] = auth.create_first_admin(conn, email, name, password)
            except Exception as exc:  # noqa: BLE001
                show_error(exc)
            else:
                st.rerun()
        return
    st.subheader("Sign in")
    with st.form("sign_in"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")
    if submitted:
        try:
            st.session_state["user_id"] = auth.authenticate(conn, email, password).user_id
        except Exception as exc:  # noqa: BLE001
            show_error(exc)
        else:
            st.rerun()


def flash(message: str) -> None:
    """Show a success message after the next rerun."""
    st.session_state["flash"] = message


def switch_business(business_id: str) -> None:
    """Make the sidebar picker select this business on the next rerun."""
    st.session_state["pending_business_id"] = business_id


def _remember_picker() -> None:
    st.session_state["business_id"] = st.session_state["business_picker"]


def select_business(conn: sqlite3.Connection, permission: Permission = Permission.VIEW_DASHBOARD) -> dict | None:
    """Sidebar picker, limited to the businesses this person belongs to (all of them for a platform admin).

    Stops the page if the person's role in the chosen business doesn't allow `permission`.
    """
    who = actor(conn)
    businesses = auth.visible_businesses(conn, who)
    if not businesses:
        st.sidebar.warning("No businesses yet. A platform admin can create one on the Home page."
                           if who.is_platform_admin else "You haven't been added to a business yet.")
        return None
    ids = [b["id"] for b in businesses]
    names = {b["id"]: b["name"] for b in businesses}
    # Streamlit forgets widget values when you change page, so the choice is also kept in "business_id".
    wanted = st.session_state.pop("pending_business_id", None) or st.session_state.get("business_id")
    if wanted in ids:
        st.session_state["business_picker"] = wanted
    if st.session_state.get("business_picker") not in ids:
        st.session_state["business_picker"] = ids[0]
    chosen = st.sidebar.selectbox("Business", ids, format_func=names.get,
                                  key="business_picker", on_change=_remember_picker)
    st.session_state["business_id"] = chosen
    role = "Platform admin" if who.is_platform_admin else who.role_in(chosen).title()
    st.sidebar.caption(f"Your role here: {role}")
    try:
        auth.require(who, chosen, permission)
    except AuthError as exc:
        st.error(f"{exc} Ask an owner of this business if you need it.")
        st.stop()
    return next(b for b in businesses if b["id"] == chosen)


def can(conn: sqlite3.Connection, business_id: str, permission: Permission) -> bool:
    return actor(conn).can(business_id, permission)


def show_error(exc: Exception) -> None:
    if isinstance(exc, (ValidationError, NotFoundError)):
        st.error(str(exc))
    else:
        st.error("Something went wrong and nothing was saved. Please try again.")
