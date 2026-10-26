"""Demo data: two made-up businesses so the simulator works on first start.

Run on its own with:  python -m whatsapp_manager.seed   (from the src folder)
"""

from __future__ import annotations

import sqlite3

from . import repositories as repo
from .services.business_service import BusinessInput, ServiceInput, add_service, create_business, set_hours

DEMO_ACTOR = "demo seed"


def seed_demo(conn: sqlite3.Connection) -> list[str]:
    """Add the demo businesses if the database has no businesses yet. Returns their ids."""
    if repo.list_businesses(conn):
        return []
    dental = create_business(conn, BusinessInput(
        name="Brightsmile Dental (demo)", category="Clinic", address="12 MG Road, Bengaluru",
        contact_email="hello@brightsmile.example", timezone="Asia/Kolkata",
        payment_info="Pay at the clinic after your visit. We accept cash, UPI and cards.",
    ), actor=DEMO_ACTOR)
    for name, desc, price, minutes in [
        ("Check-up and cleaning", "Exam, scale and polish", "800", 30),
        ("Tooth filling", "Composite filling, one tooth", "1500", 60),
        ("Teeth whitening", None, "6000", 60),
    ]:
        add_service(conn, dental, ServiceInput(name, desc, price, "INR", minutes), actor=DEMO_ACTOR)
    set_hours(conn, dental, 5, "10:00", "14:00", is_closed=False, actor=DEMO_ACTOR)  # Saturday mornings

    barber = create_business(conn, BusinessInput(
        name="Northside Barbers (demo)", category="Salon", timezone="Asia/Kolkata",
        payment_info="Pay in the shop. Cash or UPI.",
    ), actor=DEMO_ACTOR)
    for name, price, minutes in [("Haircut", "350", 30), ("Beard trim", "200", 15), ("Haircut and beard", "500", 45)]:
        add_service(conn, barber, ServiceInput(name, None, price, "INR", minutes), actor=DEMO_ACTOR)
    return [dental, barber]


if __name__ == "__main__":
    from .config import get_settings
    from .database import connect

    created = seed_demo(connect(get_settings().database_path))
    print(f"Added {len(created)} demo businesses." if created else "Database already has businesses; nothing added.")
