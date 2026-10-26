# WhatsApp Manager SaaS: revised Phase 1 plan

25 Oct 2026. This replaces section 6 of `whatsapp-manager-audit.md`. The rest of the audit (machine findings) still stands.

**Caveat:** your BRD.md, SRS.md, design.md and README.md were uploaded to the project chat but could not reach my laptop session, and they are not in `C:\Users\Devagopu\Queue`. This plan is based on a summary of them. Once the files are in the Queue folder I will read them in full and re-check this plan before writing any code.

## What the docs say Phase 1 is

A **local simulator only**: Python, Streamlit, SQLite, pytest. No real WhatsApp, calendar, payment or Supabase calls.

- Business profile, services with prices in cents, business hours
- Numbered WhatsApp-style menu: book, services, reschedule, cancel, payment info, talk to a person; plus the words HELP, MENU, BACK, HUMAN
- Leads, and appointment requests that stay **PENDING** until staff accept them
- Human handoff that pauses the bot for that conversation
- Staff dashboard, audit log, CSV export
- Tests that prove one business can never see another business's data

Later phases: Supabase (2), Meta WhatsApp (3), calendar (4), Stripe (5).

## Revised minimal plan

**Step 0: setup.** You run the commands at the bottom.

**Step 1: skeleton.** In `C:\Users\Devagopu\Queue`: `.gitignore` (blocks `.env`, `.venv`, `*.db`), `.env.example` with names only, `requirements.txt`, and the layout from the docs:

```
app.py                      Streamlit entry: chat simulator
pages/                      Dashboard, Services, Hours, Handoff inbox, Audit log
src/whatsapp_manager/
  config.py                 reads .env (no secrets needed in Phase 1)
  database.py               SQLite connection + schema creation
  models.py                 Business, Service, Hours, Customer, Lead, Appointment, Conversation, AuditEvent
  repositories/             all SQL lives here, every query takes business_id
  services/                 menu/bot logic, booking, handoff, CSV export
  integrations/             stub WhatsApp, Calendar, Payments (fakes only)
tests/
```

**Step 2: database and repositories.** SQLite tables, each with `business_id`. Money as whole cents (integers). All SQL kept in `repositories/` so Phase 2 can swap SQLite for Supabase without touching the bot or screens.

**Step 3: bot logic.** A plain function: (business, conversation state, incoming text) to (reply text, next state). Handles the numbered menu and HELP / MENU / BACK / HUMAN. No Streamlit or database code inside it, so it is easy to test.

**Step 4: booking.** Show open slots from business hours minus existing appointments; save as PENDING; staff accept or decline from the dashboard; reschedule and cancel.

**Step 5: handoff.** HUMAN (or menu option) sets the conversation to human mode; the bot stays silent; staff reply from the inbox page and can hand it back.

**Step 6: dashboard, audit log, CSV export.** Every staff action writes an audit event.

**Step 7: tests.** Menu commands, booking rules, PENDING flow, handoff pausing the bot, and tenant isolation. Each step gets its own commit.

## Remaining conflicts and notes

1. **`python` vs `py`.** The README's `python ...` commands fail on this laptop. Fix: create the virtual environment with `py`, activate it, and then `python` works normally inside it. I would add a one-line Windows note to the README (only with your OK, since it is your file).
2. **Python 3.14 is very new.** Streamlit should install on it, but if any package refuses, fall back to Python 3.12/3.13 (`winget install Python.Python.3.12`).
3. **My earlier Supabase/FastAPI plan is dropped for Phase 1.** No Supabase CLI, Docker or login is needed until Phase 2.
4. **The restaurant ordering platform** on your Desktop is not used in Phase 1. Its WhatsApp webhook code becomes a useful reference in Phase 3. It stays untouched.
5. **The old tax-lead Queue bot** (also Streamlit) overlaps a lot with Phase 1: a consulting firm is just one business type here. Its old `design.md` in Downloads is superseded by your new design.md.
6. **Not yet checked:** conflicts *inside* the four new docs (I have only seen a summary). I will list any after reading them.

## Commands to run now (PowerShell)

1. Save BRD.md, SRS.md, design.md and README.md into `C:\Users\Devagopu\Queue`. Then check they are there:

```powershell
Get-ChildItem C:\Users\Devagopu\Queue
```

2. Set your Git name and email (once per computer):

```powershell
git config --global user.name "Deva"
git config --global user.email "YOUR_EMAIL_HERE"
```

## Commands for after you approve the plan

I can run these for you, or you can:

```powershell
cd C:\Users\Devagopu\Queue
git init
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install streamlit pytest python-dotenv
```

If activation is blocked with a "running scripts is disabled" error, run this once and try again:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
