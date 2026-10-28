"""WhatsApp Manager, Phase 1 local simulator.

Run with:  streamlit run app.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import streamlit as st  # noqa: E402

from whatsapp_manager.ui import current_actor, get_conn  # noqa: E402

# Menu items are trimmed to the person's role for tidiness only. Each page checks the role itself.
actor = current_actor(get_conn())
owner_somewhere = actor is not None and (actor.is_platform_admin or "OWNER" in actor.roles.values())
pages = [
    st.Page("pages/0_Home.py", title="Home", icon="🏠", default=True),
    *([st.Page("pages/1_Business_Profile.py", title="Business profile", icon="🏪"),
       st.Page("pages/2_Services.py", title="Services", icon="🧾")] if owner_somewhere else []),
    st.Page("pages/3_Chat_Simulator.py", title="Chat simulator", icon="💬"),
    st.Page("pages/4_Leads_Appointments.py", title="Leads and appointments", icon="📋"),
    *([st.Page("pages/5_Team.py", title="Team", icon="👥")] if owner_somewhere else []),
]
st.navigation(pages if actor else pages[:1]).run()
