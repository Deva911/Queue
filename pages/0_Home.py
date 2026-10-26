"""Home: business sign-up and an overview of the selected business."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st  # noqa: E402

from whatsapp_manager import repositories as repo  # noqa: E402
from whatsapp_manager.models import AppointmentStatus, ConversationStatus  # noqa: E402
from whatsapp_manager.services.business_service import BusinessInput, create_business  # noqa: E402
from whatsapp_manager.ui import flash, page_setup, select_business, show_error, switch_business  # noqa: E402

conn = page_setup("WhatsApp Manager")
business = select_business(conn)

st.write("Set up a business, try the customer chat, and handle requests as staff. "
         "Use the pages in the sidebar:")
st.markdown(
    "1. **Business Profile**: name, contact details, time zone, opening hours, payment info\n"
    "2. **Services**: what customers can book, with prices and durations\n"
    "3. **Chat Simulator**: chat as a customer would on WhatsApp\n"
    "4. **Leads and Appointments**: confirm or decline requests, reply to handed-over chats, audit log, CSV export"
)

if business:
    bid = business["id"]
    st.subheader(f"Today at {business['name']}")
    pending = repo.list_appointments(conn, bid, statuses=[AppointmentStatus.PENDING])
    handoffs = repo.list_conversations(conn, bid, [ConversationStatus.PENDING_HANDOFF])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active services", len(repo.list_services(conn, bid, active_only=True)))
    c2.metric("Requests waiting for staff", len(pending))
    c3.metric("Chats waiting for a person", len(handoffs))
    c4.metric("Leads", len(repo.list_leads(conn, bid)))

st.divider()
st.subheader("Sign up a new business")
with st.form("signup", clear_on_submit=True):
    name = st.text_input("Business name *")
    category = st.selectbox("Category", ["Clinic", "Salon", "Consulting", "Fitness", "Tutoring", "Other"])
    email = st.text_input("Contact email")
    tz = st.text_input("Time zone *", value="Asia/Kolkata", help="For example Asia/Kolkata or America/Toronto")
    submitted = st.form_submit_button("Create business")
if submitted:
    try:
        new_id = create_business(conn, BusinessInput(name=name, category=category, contact_email=email, timezone=tz))
    except Exception as exc:  # noqa: BLE001 - shown to the user without a stack trace
        show_error(exc)
    else:
        switch_business(new_id)
        flash(f"Created {name.strip()}. Default hours are Mon to Fri, 09:00 to 17:00. "
                   "Add services next on the Services page.")
        st.rerun()
