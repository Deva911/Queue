# WhatsApp Manager

A WhatsApp assistant for small service businesses. Customers message the business on WhatsApp, pick from a numbered menu (book, services, reschedule, cancel, payment info, talk to a person), and staff manage leads and appointment requests from a dashboard.

## Status

**Phase 1 (local simulator) is built.** It runs on your own computer with Streamlit and SQLite. It does not send real WhatsApp messages, touch a real calendar or take payments. Appointment requests stay **PENDING** until a staff member decides. Use made-up data only.

See [`docs/PHASE1_REVIEW.md`](docs/PHASE1_REVIEW.md) for what was checked, the test results and known limits.

## Run it (Windows PowerShell)

On Deva's laptop the `python` command opens the Microsoft Store, so create the virtual environment with `py`. Inside the activated environment `python` works normally.

```powershell
cd C:\Users\Devagopu\Queue
py -3.14 -m venv .venv          # or py -3.12 if a package refuses to install on 3.14
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

If activation is blocked ("running scripts is disabled"), run this once and try again:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Streamlit prints a local address (usually http://localhost:8501). On first start the app creates `data/whatsapp_manager.db` with two demo businesses. Delete that file to start from scratch.

The first time you open it, the app asks you to create the **platform admin** account (that's you). After that everyone signs in with email and password.

## Who can do what

| | Platform admin | Owner | Staff |
|---|---|---|---|
| Create businesses | ✓ | | |
| Business profile, hours, services | every business | own business | |
| Team (add or remove owners and staff) | every business | own business | |
| Audit log, CSV export, delete old messages | every business | own business | |
| Appointment requests, handoff inbox, leads, chat simulator | every business | own business | own business |

Passwords are stored as salted scrypt hashes. Five wrong passwords lock the account for 15 minutes. Every page checks the signed-in person's role when it loads and again before it saves anything; hiding a menu item is never the only check. Roles come from the `memberships` table, re-read on every page load, so removing someone takes effect at once. Moving to Supabase Auth later replaces only the sign-in part (`services/auth_service.py`: `authenticate` and the password helpers); the roles and checks stay.

Refreshing the browser tab signs you out (Streamlit keeps sign-in per tab). That's fine for a local prototype.

Run the tests:

```powershell
python -m pytest -q
```

## What you can do

| Page | What it does |
|---|---|
| Home | See pending requests and chats waiting for a person; platform admin creates businesses; change your password |
| Business profile | Name, contact details, time zone, logo, payment info, opening hours, active/inactive |
| Services | Add, edit, activate and deactivate services (prices stored as whole cents) |
| Chat simulator | Chat as a customer. Type numbers or the words HELP, MENU, BACK, HUMAN, or tap the option buttons |
| Leads and appointments | Confirm, decline or cancel requests; reply to handed-over chats and hand them back; lead status; audit log; CSV export |
| Team | Add owners and staff to a business, or remove them |

The business picker in the sidebar is a demo convenience, **not a login**. Real logins and per-business access come with Supabase in Phase 2.

## Phases

1. Local simulator: Python, Streamlit, SQLite, pytest. No real WhatsApp, calendar, payment or Supabase calls. **(this code)**
2. Supabase database and logins
3. Meta WhatsApp Cloud API
4. Calendar integration
5. Stripe payments

## Code layout

```
app.py                          Streamlit entry point (page navigation)
pages/                          One file per screen; no SQL or business rules in here
src/whatsapp_manager/
  config.py                     Reads .env (only DATABASE_URL in Phase 1)
  database.py                   SQLite schema; every business-owned table has business_id
  models.py                     Status values, conversation states, error types
  repositories.py               All SQL; every query takes business_id
  services/bot.py               The menu bot as a plain function (no database, no Streamlit)
  services/conversation_service.py  Runs a chat message end to end; human handoff
  services/appointment_service.py   Open times, PENDING requests, staff decisions
  services/business_service.py      Sign-up, profile, hours, services, price parsing
  services/export_service.py        CSV export
  integrations/                 Fake WhatsApp, calendar and payment adapters (no network)
  seed.py                       Demo businesses
tests/                          pytest suite (network is blocked during tests)
docs/specs/                     BRD, SRS, design and MVP README from the spec handoff
```

## Other files in this repo

| Path | What it is |
|---|---|
| `landing-page/index.html` | Marketing landing page (open it in a browser) |
| `docs/whatsapp-manager-plan-v2.md` | Phase 1 build plan |
| `docs/whatsapp-manager-audit.md` | Setup audit of the development machine |
| `docs/PROJECT_TRACKER.md` | Project tracker: stages, tasks and status |
| `docs/QUEUE_SETUP_GUIDE.md` | Guide from local code to a live WhatsApp bot (Supabase, Meta, Render) |
| `prototypes/tax-leads/` | Earlier tax-lead bot prototype: plan, structure diagram and screenshots |

## Secrets

Never commit `.env` or any keys, tokens or passwords. `.env`, `.venv/`, `data/` and `*.db` are in `.gitignore`. Phase 1 needs no secrets at all.
