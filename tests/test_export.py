import csv
import io

from whatsapp_manager.services import export_service


def test_csv_has_headers_and_rows(conn, clinic, say):
    for text in ["hi", "1", "1", "1", "Asha"]:
        say(clinic["id"], text)
    rows = list(csv.DictReader(io.StringIO(export_service.appointments_csv(conn, clinic["id"]))))
    assert len(rows) == 1
    assert rows[0]["status"] == "PENDING" and rows[0]["customer_name"] == "Asha"


def test_customer_text_cannot_become_a_spreadsheet_formula(conn, clinic, say):
    for text in ["hi", "1", "1", "1", "=HYPERLINK(evil)"]:
        say(clinic["id"], text)
    exported = export_service.leads_csv(conn, clinic["id"])
    assert "'=HYPERLINK(evil)" in exported
