"""Staff dashboard: appointment requests, handoff inbox, leads, audit log and CSV export."""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st  # noqa: E402

from whatsapp_manager import repositories as repo  # noqa: E402
from whatsapp_manager.models import AppointmentStatus, ConversationStatus, LeadStatus  # noqa: E402
from whatsapp_manager.services import appointment_service as appts  # noqa: E402
from whatsapp_manager.services import conversation_service as chat  # noqa: E402
from whatsapp_manager.services import export_service  # noqa: E402
from whatsapp_manager.services.auth_service import Permission  # noqa: E402
from whatsapp_manager.ui import actor, can, flash, page_setup, select_business, show_error  # noqa: E402

conn = page_setup("Leads and Appointments")
business = select_business(conn, Permission.HANDLE_REQUESTS)
if not business:
    st.stop()
bid = business["id"]
me = actor(conn).label


def when(iso: str) -> str:
    return appts.slot_label(datetime.fromisoformat(iso))


waiting = repo.list_conversations(conn, bid, [ConversationStatus.PENDING_HANDOFF, ConversationStatus.HUMAN_ACTIVE])
pending = appts.list_requests(conn, bid, [AppointmentStatus.PENDING])
tab_appts, tab_inbox, tab_leads, tab_audit, tab_export = st.tabs([
    f"Appointment requests ({len(pending)} pending)", f"Handoff inbox ({len(waiting)})", "Leads", "Audit log",
    "Export CSV",
])

with tab_appts:
    st.caption("Confirming here records the team's decision. It does not book anything in a real calendar.")
    show = st.multiselect("Show", [s.value for s in AppointmentStatus], default=[AppointmentStatus.PENDING,
                                                                                  AppointmentStatus.CONFIRMED])
    requests = appts.list_requests(conn, bid, show)
    if not requests:
        st.write("Nothing to show.")
    for a in requests:
        who = a["customer_name"] or a["external_customer_key"]
        title = f"{when(a['requested_start_at'])} · {a['service_name']} · {who}"
        with st.container(border=True):
            st.markdown(f"**{title}**  \nStatus: **{a['status']}**"
                        + ("  \nReschedule of an earlier request" if a["reschedule_of"] else "")
                        + (f"  \nStaff note: {a['staff_note']}" if a["staff_note"] else ""))
            allowed = appts.ALLOWED_TRANSITIONS.get(a["status"], set())
            choices = [s for s in (AppointmentStatus.CONFIRMED, AppointmentStatus.DECLINED,
                                   AppointmentStatus.CANCELLED) if s in allowed]
            if choices:
                c1, c2, c3 = st.columns([2, 3, 1])
                new_status = c1.selectbox("Change to", choices, key=f"status_{a['id']}")
                note = c2.text_input("Note (optional, sent to the customer)", key=f"note_{a['id']}")
                if c3.button("Apply", key=f"apply_{a['id']}"):
                    try:
                        appts.staff_set_status(conn, bid, a["id"], new_status, note, actor=me)
                    except Exception as exc:  # noqa: BLE001
                        show_error(exc)
                    else:
                        flash(f"Request marked {new_status}.")
                        st.rerun()

with tab_inbox:
    st.caption("Chats where the customer asked for a person. The bot stays silent until you hand the chat back.")
    if not waiting:
        st.write("No chats are waiting for a person.")
    for conv in waiting:
        who = conv["display_name"] or conv["external_customer_key"]
        with st.expander(f"{who} · {conv['status']}", expanded=True):
            with st.container(height=260):
                for m in chat.list_messages(conn, bid, conv["id"]):
                    st.text(f"{m['sender'].title()}: {m['body']}")
            if conv["status"] == ConversationStatus.PENDING_HANDOFF:
                if st.button("Take over", key=f"take_{conv['id']}"):
                    chat.take_over(conn, bid, conv["id"], actor=me)
                    st.rerun()
            with st.form(f"reply_{conv['id']}", clear_on_submit=True):
                reply = st.text_input("Reply to customer")
                if st.form_submit_button("Send reply"):
                    try:
                        chat.staff_reply(conn, bid, conv["id"], reply, actor=me)
                    except Exception as exc:  # noqa: BLE001
                        show_error(exc)
                    else:
                        st.rerun()
            with st.form(f"return_{conv['id']}"):
                resolution = st.text_input("Resolution note (internal)")
                if st.form_submit_button("Hand back to the bot"):
                    chat.return_to_bot(conn, bid, conv["id"], resolution, actor=me)
                    flash("Chat handed back to the automated assistant.")
                    st.rerun()

with tab_leads:
    leads = repo.list_leads(conn, bid)
    if not leads:
        st.write("No leads yet. They appear when a customer requests an appointment or asks for a person.")
    statuses = [s.value for s in LeadStatus]
    for lead in leads:
        c1, c2, c3 = st.columns([4, 2, 1])
        c1.markdown(f"**{lead['name'] or lead['external_customer_key']}** · {lead['enquiry']}  \n"
                    f"{lead['created_at'][:16].replace('T', ' ')} UTC")
        new = c2.selectbox("Status", statuses, index=statuses.index(lead["status"]), key=f"lead_{lead['id']}",
                           label_visibility="collapsed")
        if c3.button("Save", key=f"lead_save_{lead['id']}") and new != lead["status"]:
            chat.set_lead_status(conn, bid, lead["id"], new, actor=me)
            flash("Lead updated.")
            st.rerun()

with tab_audit:
    if not can(conn, bid, Permission.VIEW_AUDIT):
        st.info("Only owners can see the audit log.")
    else:
        events = repo.list_audit(conn, bid)
        st.dataframe(
            [{"When (UTC)": e["created_at"][:19].replace("T", " "), "Who": e["actor"], "What": e["event_type"],
              "Record": f"{e['entity_type']} {str(e['entity_id'])[:8]}",
              "Details": json.dumps(json.loads(e["details_json"]))} for e in events],
            use_container_width=True, hide_index=True,
        )

with tab_export:
    if not can(conn, bid, Permission.EXPORT_DATA):
        st.info("Only owners can export customer data.")
    else:
        st.caption(f"Only {business['name']}'s records are included.")
        st.download_button("Download leads CSV", export_service.leads_csv(conn, bid), file_name="leads.csv",
                           mime="text/csv")
        st.download_button("Download appointment requests CSV", export_service.appointments_csv(conn, bid),
                           file_name="appointment_requests.csv", mime="text/csv")
