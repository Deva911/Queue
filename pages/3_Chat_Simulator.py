"""Chat as a customer would on WhatsApp. Type a number or tap an option."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st  # noqa: E402

from whatsapp_manager import repositories as repo  # noqa: E402
from whatsapp_manager.models import ConversationStatus, Sender  # noqa: E402
from whatsapp_manager.services import conversation_service as chat  # noqa: E402
from whatsapp_manager.ui import page_setup, select_business, show_error  # noqa: E402

conn = page_setup("Chat Simulator")
business = select_business(conn)
if not business:
    st.stop()
bid = business["id"]

st.caption("You are the customer. Nothing is sent to WhatsApp: messages are saved to the local database only.")
c1, c2 = st.columns([3, 1])
customer_key = c1.text_input("Customer phone number (made up)",
                             value=st.session_state.get("customer_key", "+91 90000 00001"))
st.session_state["customer_key"] = customer_key
if c2.button("Start over", help="Close this chat and start a fresh one for this number"):
    try:
        chat.close_for_customer(conn, bid, customer_key)
    except Exception as exc:  # noqa: BLE001
        show_error(exc)
    else:
        st.rerun()


def send(text: str) -> None:
    try:
        chat.handle_inbound(conn, bid, customer_key, text)
    except Exception as exc:  # noqa: BLE001
        show_error(exc)


pending_text = st.session_state.pop("tapped_option", None)
typed = st.chat_input("Type a message, e.g. Hi, 1, MENU, HELP, BACK or HUMAN")
if pending_text:
    send(pending_text)
if typed:
    send(typed)

customer = repo.get_customer_by_key(conn, bid, customer_key.strip()) if customer_key.strip() else None
conversation = repo.get_open_conversation(conn, bid, customer["id"]) if customer else None

if not conversation:
    st.write("Say **Hi** to start the chat.")
    st.stop()

if conversation["status"] == ConversationStatus.PENDING_HANDOFF:
    st.warning("Waiting for a person. The automated assistant is paused for this chat.", icon="🙋")
elif conversation["status"] == ConversationStatus.HUMAN_ACTIVE:
    st.warning("A staff member is handling this chat. The automated assistant is paused.", icon="🧑‍💼")

for m in chat.list_messages(conn, bid, conversation["id"]):
    role = "user" if m["sender"] == Sender.CUSTOMER else "assistant"
    avatar = {"CUSTOMER": "🙂", "BOT": "🤖", "STAFF": "🧑‍💼"}[m["sender"]]
    with st.chat_message(role, avatar=avatar):
        if m["sender"] == Sender.STAFF:
            st.caption("Staff")
        st.text(m["body"])

options = chat.current_options(conn, bid, conversation["id"])
if options:
    st.caption("Tap an option (same as typing its number):")
    cols = st.columns(min(len(options), 3))
    for i, (value, label) in enumerate(options):
        if cols[i % len(cols)].button(f"{value}. {label}" if value.isdigit() else label, key=f"opt_{i}_{value}",
                                      use_container_width=True):
            st.session_state["tapped_option"] = value
            st.rerun()
