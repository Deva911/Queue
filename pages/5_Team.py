"""Team: who can sign in to this business, and as what. Owners and the platform admin only."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st  # noqa: E402

from whatsapp_manager import repositories as repo  # noqa: E402
from whatsapp_manager.models import Role  # noqa: E402
from whatsapp_manager.services import auth_service as auth  # noqa: E402
from whatsapp_manager.services.auth_service import Permission  # noqa: E402
from whatsapp_manager.ui import actor, flash, page_setup, select_business, show_error  # noqa: E402

conn = page_setup("Team")
business = select_business(conn, Permission.MANAGE_TEAM)
if not business:
    st.stop()
bid = business["id"]
me = actor(conn)

st.caption("Owners manage the profile, services, hours and team. Staff handle requests, chats and leads only.")
members = repo.list_members(conn, bid)
if not members:
    st.warning("Nobody can sign in to this business yet. Add its owner below.")
for m in members:
    c1, c2, c3 = st.columns([3, 1, 1])
    c1.write(f"**{m['display_name']}** · {m['email']}" + ("" if m["status"] == "ACTIVE" else " (disabled)"))
    c2.write(m["role"].title())
    if m["user_id"] != me.user_id and c3.button("Remove", key=f"remove_{m['user_id']}"):
        try:
            auth.remove_member(conn, me, bid, m["user_id"])
        except Exception as exc:  # noqa: BLE001
            show_error(exc)
        else:
            flash(f"Removed {m['email']} from {business['name']}.")
            st.rerun()

st.subheader("Add someone")
st.caption("If they already have an account, they get access with their existing password. "
           "Otherwise give them the temporary password and ask them to change it after signing in.")
with st.form("add_member", clear_on_submit=True):
    name = st.text_input("Name")
    email = st.text_input("Email")
    role = st.selectbox("Role", [Role.STAFF.value, Role.OWNER.value], format_func=str.title)
    password = st.text_input(f"Temporary password (at least {auth.MIN_PASSWORD_LENGTH} characters)",
                             type="password")
    submitted = st.form_submit_button("Add to team")
if submitted:
    try:
        auth.add_member(conn, me, bid, email, name, role, password)
    except Exception as exc:  # noqa: BLE001
        show_error(exc)
    else:
        flash(f"Added {email.strip()} as {role.title()}.")
        st.rerun()
