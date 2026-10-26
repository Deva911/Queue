"""WhatsApp Manager, Phase 1 local simulator.

Run with:  streamlit run app.py
"""

import streamlit as st

pages = [
    st.Page("pages/0_Home.py", title="Home", icon="🏠", default=True),
    st.Page("pages/1_Business_Profile.py", title="Business profile", icon="🏪"),
    st.Page("pages/2_Services.py", title="Services", icon="🧾"),
    st.Page("pages/3_Chat_Simulator.py", title="Chat simulator", icon="💬"),
    st.Page("pages/4_Leads_Appointments.py", title="Leads and appointments", icon="📋"),
]
st.navigation(pages).run()
