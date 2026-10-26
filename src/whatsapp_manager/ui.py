"""Shared Streamlit helpers: database connection, demo banner and the business selector."""

from __future__ import annotations

import sqlite3

import streamlit as st

from . import repositories as repo
from .config import get_settings
from .database import connect
from .models import NotFoundError, ValidationError
from .seed import seed_demo

DEMO_BANNER = ("**Local simulator.** No real WhatsApp messages, calendar bookings or payments. "
               "Use made-up data only.")


def get_conn() -> sqlite3.Connection:
    """One connection per script run (SQLite connections shouldn't be shared across Streamlit threads)."""
    conn = connect(get_settings().database_path)
    seed_demo(conn)
    return conn


def page_setup(title: str) -> sqlite3.Connection:
    st.set_page_config(page_title=f"{title} · WhatsApp Manager", page_icon="💬", layout="wide")
    st.title(title)
    st.info(DEMO_BANNER, icon="🧪")
    message = st.session_state.pop("flash", None)
    if message:
        st.success(message)
    return get_conn()


def flash(message: str) -> None:
    """Show a success message after the next rerun."""
    st.session_state["flash"] = message


def switch_business(business_id: str) -> None:
    """Make the sidebar picker select this business on the next rerun."""
    st.session_state["pending_business_id"] = business_id


def _remember_picker() -> None:
    st.session_state["business_id"] = st.session_state["business_picker"]


def select_business(conn: sqlite3.Connection) -> dict | None:
    """Sidebar picker. This is a demo convenience, not a login: anyone running the app sees every business."""
    businesses = repo.list_businesses(conn)
    if not businesses:
        st.sidebar.warning("No businesses yet. Create one on the Home page.")
        return None
    ids = [b["id"] for b in businesses]
    names = {b["id"]: b["name"] for b in businesses}
    # Streamlit forgets widget values when you change page, so the choice is also kept in "business_id".
    wanted = st.session_state.pop("pending_business_id", None) or st.session_state.get("business_id")
    if wanted in ids:
        st.session_state["business_picker"] = wanted
    if st.session_state.get("business_picker") not in ids:
        st.session_state["business_picker"] = ids[0]
    chosen = st.sidebar.selectbox("Demo business (not a login)", ids, format_func=names.get,
                                  key="business_picker", on_change=_remember_picker)
    st.session_state["business_id"] = chosen
    st.sidebar.caption("Demo selector only. Real logins and per-business access arrive with Supabase in Phase 2.")
    return next(b for b in businesses if b["id"] == chosen)


def show_error(exc: Exception) -> None:
    if isinstance(exc, (ValidationError, NotFoundError)):
        st.error(str(exc))
    else:
        st.error("Something went wrong and nothing was saved. Please try again.")
