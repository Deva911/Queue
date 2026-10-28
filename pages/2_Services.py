"""Service catalogue: add, edit, switch on and off."""

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st  # noqa: E402

from whatsapp_manager.services.business_service import (  # noqa: E402
    DEFAULT_CURRENCY,
    ServiceInput,
    add_service,
    format_price,
    list_services,
    set_service_active,
    update_service,
)
from whatsapp_manager.services.auth_service import Permission  # noqa: E402
from whatsapp_manager.ui import actor, flash, page_setup, select_business, show_error  # noqa: E402

conn = page_setup("Services")
business = select_business(conn, Permission.EDIT_SERVICES)
if not business:
    st.stop()
bid = business["id"]


def _price_text(price_minor):
    return "" if price_minor is None else f"{Decimal(price_minor) / 100:.2f}"


def service_form(key: str, service: dict | None = None):
    service = service or {}
    with st.form(key):
        name = st.text_input("Service name *", value=service.get("name", ""))
        description = st.text_area("Description", value=service.get("description") or "")
        c1, c2, c3 = st.columns(3)
        price = c1.text_input("Price (blank = price on request)", value=_price_text(service.get("price_minor")))
        currency = c2.text_input("Currency", value=service.get("currency") or DEFAULT_CURRENCY, max_chars=3)
        duration = c3.number_input("Duration (minutes, 0 = not set)", min_value=0, max_value=600, step=5,
                                   value=int(service.get("duration_minutes") or 0))
        submitted = st.form_submit_button("Save service" if service else "Add service")
    if submitted:
        return ServiceInput(name, description, price, currency, int(duration) or None)
    return None


st.subheader("Add a service")
new = service_form("add_service")
if new:
    try:
        add_service(conn, bid, new, actor=actor(conn).label)
    except Exception as exc:  # noqa: BLE001
        show_error(exc)
    else:
        flash(f"Added {new.name.strip()}.")
        st.rerun()

st.subheader("Your services")
services = list_services(conn, bid)
if not services:
    st.write("No services yet.")
for s in services:
    label = "Active" if s["is_active"] else "Inactive (hidden from customers)"
    with st.expander(f"{s['name']} · {format_price(s['price_minor'], s['currency'])} · {label}"):
        edited = service_form(f"edit_{s['id']}", s)
        if edited:
            try:
                update_service(conn, bid, s["id"], edited, actor=actor(conn).label)
            except Exception as exc:  # noqa: BLE001
                show_error(exc)
            else:
                flash(f"Saved {edited.name.strip()}.")
                st.rerun()
        toggle = "Deactivate" if s["is_active"] else "Activate"
        if st.button(toggle, key=f"toggle_{s['id']}"):
            set_service_active(conn, bid, s["id"], not s["is_active"], actor=actor(conn).label)
            flash(f"{s['name']} is now {'inactive' if s['is_active'] else 'active'}.")
            st.rerun()
