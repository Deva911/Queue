"""Business profile and opening hours."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st  # noqa: E402

from whatsapp_manager.models import WEEKDAY_NAMES, BusinessStatus  # noqa: E402
from whatsapp_manager.services.business_service import (  # noqa: E402
    BusinessInput,
    list_hours,
    set_hours,
    update_business,
    validate_hours,
)
from whatsapp_manager.services import conversation_service as chat  # noqa: E402
from whatsapp_manager.services.auth_service import Permission  # noqa: E402
from whatsapp_manager.ui import actor, can, flash, page_setup, select_business, show_error  # noqa: E402

conn = page_setup("Business Profile")
business = select_business(conn, Permission.EDIT_BUSINESS)
if not business:
    st.stop()
bid = business["id"]
me = actor(conn).label
statuses = [s.value for s in BusinessStatus]

st.subheader("Profile")
with st.form("profile"):
    name = st.text_input("Business name *", value=business["name"])
    category = st.text_input("Category", value=business["category"] or "")
    address = st.text_input("Address", value=business["address"] or "")
    email = st.text_input("Contact email", value=business["contact_email"] or "")
    tz = st.text_input("Time zone *", value=business["timezone"], help="For example Asia/Kolkata")
    logo = st.text_input("Logo URL or file path", value=business["logo_url"] or "")
    payment = st.text_area("Payment information shown to customers (menu option 5)",
                           value=business["payment_info"] or "",
                           help="Plain text only. Never ask customers for card details in chat.")
    status = st.selectbox("Status", statuses, index=statuses.index(business["status"]),
                          help="When inactive, the assistant tells customers it isn't taking messages.")
    if st.form_submit_button("Save profile"):
        try:
            update_business(conn, bid, BusinessInput(name, category, address, email, tz, logo, payment, status),
                            actor=me)
        except Exception as exc:  # noqa: BLE001 - shown without a stack trace
            show_error(exc)
        else:
            flash("Profile saved.")
            st.rerun()

st.subheader("Opening hours")
st.caption(f"Times are in {business['timezone']}. The bot offers request times inside these hours. "
           "This is not a live calendar: staff still confirm every request.")
hours = {h["weekday"]: h for h in list_hours(conn, bid)}
with st.form("hours"):
    rows = []
    for day, label in enumerate(WEEKDAY_NAMES):
        h = hours.get(day, {"opens_at": "09:00", "closes_at": "17:00", "is_closed": 1})
        c1, c2, c3, c4 = st.columns([2, 1, 2, 2])
        c1.markdown(f"**{label}**")
        closed = c2.checkbox("Closed", value=bool(h["is_closed"]), key=f"closed_{day}")
        opens = c3.text_input("Opens", value=h["opens_at"] or "09:00", key=f"opens_{day}")
        closes = c4.text_input("Closes", value=h["closes_at"] or "17:00", key=f"closes_{day}")
        rows.append((day, opens, closes, closed))
    if st.form_submit_button("Save hours"):
        try:
            for day, opens, closes, closed in rows:  # check every day first so nothing is half-saved
                validate_hours(opens, closes, closed, label=WEEKDAY_NAMES[day])
            for day, opens, closes, closed in rows:
                set_hours(conn, bid, day, opens, closes, closed, actor=me)
        except Exception as exc:  # noqa: BLE001
            show_error(exc)
        else:
            flash("Opening hours saved.")
            st.rerun()

if can(conn, bid, Permission.DELETE_OLD_MESSAGES):
    st.subheader("Data retention")
    st.caption("Chat messages hold customers' personal details. Delete the ones you no longer need.")
    with st.form("retention"):
        days = st.number_input("Delete chat messages older than (days)", min_value=1, max_value=3650,
                               value=chat.DEFAULT_MESSAGE_RETENTION_DAYS, step=1)
        if st.form_submit_button("Delete old messages"):
            try:
                deleted = chat.delete_old_messages(conn, bid, int(days), actor=me)
            except Exception as exc:  # noqa: BLE001
                show_error(exc)
            else:
                flash(f"Deleted {deleted} messages older than {int(days)} days.")
                st.rerun()
