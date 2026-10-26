# Plan: Local Streamlit prototype (no external services)

**Goal:** a small app that runs on your own computer. Someone fills in an enquiry the way a client would on WhatsApp, the lead is saved to a file on your computer, and you can look at every saved lead.
**Not included:** WhatsApp, Meta, Supabase, payments, or any internet service.

## How it will look

The app has two pages, chosen from the sidebar.

**Page 1: New enquiry.** One question at a time, in the same order as the WhatsApp flow in `design.md`:

1. Choose a service (Personal tax return, Self-employed, Small business, Tax consultation, Other enquiry).
2. "Is this your first time working with us?" Yes / No. (Skipped for "Other enquiry".)
3. Name.
4. Email, with a "Skip" option.
5. "Would you like the consultant to contact you?" Yes / No.
6. Thank-you screen with the general checklist for the chosen service, and a "Start a new enquiry" button.

If an answer isn't valid (for example an email without an `@`), the same question stays on screen with a short explanation. A "Start over" button is always visible.

**Page 2: Saved leads.** Counts at the top (total leads, wants follow-up). Below that, a table with name, email, service, first-time client, follow-up and date, which you can filter by service.

## Files I'll create

| File | What it does, in plain words |
|---|---|
| `app.py` | The Streamlit screens: the two pages above. The only file that knows about Streamlit. |
| `services.json` | The service menu and each service's checklist, as plain data. To change wording you edit this file, not the code. |
| `services.py` | Reads `services.json` and gives back the menu and the checklist for a service. |
| `validation.py` | Small checks: "is this a sensible name?", "is this a valid email?", "did they type skip?". |
| `lead_store.py` | Saves a lead to the file and reads all leads back. |
| `data/leads.json` | Created automatically the first time a lead is saved. Not shared or uploaded. |
| `tests/` | Automatic checks (listed below). |
| `requirements.txt` | The two packages to install: `streamlit` and `pytest`. |
| `README.md` | Step-by-step instructions to install, run the app and run the tests. |

Each Python file stays short, with comments explaining *why* as well as *what*.

## How local saving works

Each lead is stored as one entry in a JSON file, `data/leads.json`. JSON is a plain text format you can open in any text editor, so you can see exactly what was saved. One saved lead looks like:

```json
{
  "id": "3f2c…",
  "created_at": "2026-10-24T10:15:00",
  "name": "Jane Doe",
  "email": null,
  "service": "personal_tax_return",
  "first_time_client": true,
  "wants_follow_up": true,
  "status": "new"
}
```

Saving reads the file, adds the new lead, and writes the whole file back. That's fine for one person on one computer. When you move to Supabase later, only `lead_store.py` changes; the screens and checks stay the same.

*Alternative:* SQLite, a small database built into Python. It's closer to Supabase, but it's harder to look inside as a beginner. I recommend JSON for now.

## Tests

The tests run with one command (`pytest`) and don't open the app.

- **`test_validation.py`:** real names are accepted; empty input, numbers and emails are rejected as names; good and bad emails; "skip" works; long numbers that look like a SIN are refused so they're never saved.
- **`test_services.py`:** the menu has the 5 services in order; each service returns its own checklist and never another service's; "Other enquiry" has no checklist; an unknown service doesn't crash the app.
- **`test_lead_store.py`:** a saved lead can be read back exactly; several leads are all kept; a skipped email is saved as empty; reading before anything is saved gives an empty list. These tests use a throwaway folder, so they never touch your real `data/leads.json`.
- **`test_app.py`:** one test that clicks through the whole enquiry using Streamlit's built-in test tool, then checks that one lead was saved and the right checklist was shown.

## What I'll reuse from what's already built

Kept, but simplified:
- The service menu and draft checklists (`services.json`).
- The name, email, skip and SIN checks (`validation.py`), cut down to the parts this prototype needs.

Set aside, and not part of this prototype:
- The FastAPI webhook, the WhatsApp parser and sender, the database schema, and the duplicate-message handling.

These stay in the earlier zip for later phases. Nothing has been pushed anywhere.

## Things you might want to decide

1. **JSON file or SQLite** for saving. I recommend JSON.
2. **Status changes:** should the Saved leads page let you change a lead's status (New → Contacted…) and add notes now? You didn't ask for this, so I've left it out; it's a small addition later.
3. **Checklist wording:** it's still a draft until the consultant reviews it.
