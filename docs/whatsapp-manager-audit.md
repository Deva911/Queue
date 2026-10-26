# WhatsApp Manager SaaS: setup audit and plan

Audited on 24 Oct 2026, on LAPTOP-8MOTIDJQ. Nothing was changed, created in your project, committed, or connected. No secret values were opened or printed (for `.env.example` I only listed variable names).

## 1. The short version

- `C:\Users\Devagopu\Queue` is **completely empty** and is **not a Git repository**. There is nothing to break yet.
- **BRD.md and SRS.md do not exist anywhere** I searched (Desktop, Documents, Downloads, OneDrive, home folder).
- The only product `design.md` is for the **old single-consultant tax-lead bot**, and it explicitly rules out most of what the new SaaS needs.
- **Supabase CLI is not installed**, there is no Supabase project config, and you are not logged in to it.
- The `python` command is broken (it opens the Microsoft Store). Use `py` instead.
- You already have a strong head start: `Desktop\whatsapp-ordering-platform` is a working **multi-tenant WhatsApp backend** (restaurants) with tests. Its core is almost exactly what the new SaaS needs.

## 2. What is on this machine

| Item | Status |
|---|---|
| `C:\Users\Devagopu\Queue` | Empty folder, no Git |
| Git | Installed (2.55). **Global name/email not set.** |
| GitHub CLI | Installed, logged in as Deva911 |
| Python | `py` launcher works: Python **3.14** (default) and Anaconda 3.9. `python` command opens the Store. |
| Python packages (3.14, installed globally) | fastapi, uvicorn, SQLAlchemy, alembic, psycopg, pydantic-settings, httpx, cryptography, pytest, ruff, python-dotenv, PyJWT, firebase_admin. **No** supabase, stripe or Google Calendar libraries. |
| Node / npm | Installed (Node 24, npm 11) |
| Supabase CLI | **Not installed** (not on PATH, not via Scoop or npm) |
| Supabase login | **No** (no access-token file) |
| Supabase project config (`supabase/config.toml`) | **None anywhere** |
| Docker | **Not installed** (only needed if you want Supabase running locally) |

## 3. Documents found

| File | What it is |
|---|---|
| `Downloads\queue\design.md` (23 Oct) | Design for "WhatsApp Lead Generation for Tax Consultants": one consultant, no AI, no payments, no scheduling, no multi-tenant onboarding. Stack: Meta Cloud API, FastAPI, Supabase, Streamlit. |
| `Downloads\queue\whatsapp-tax-leads.zip`, `tax-leads-prototype.zip` | The earlier Queue code bundles (not unzipped). |
| `Desktop\Apps\DESIGN.md` and `Downloads\Files\DESIGN.md` | Identical **visual style guide** ("High-Performance Minimalism": colours, Lexend font). Useful for the dashboard look, not a product spec. |
| `Desktop\whatsapp-ordering-platform\CLAUDE.md`, `docs\PLAN.md` | Rules and phase plan for the restaurant ordering platform. |

## 4. Integrations: configured vs merely installed

| Integration | Installed? | Configured? |
|---|---|---|
| WhatsApp (Meta Cloud API) | Code exists in the ordering platform, plus a **simulator** that fakes WhatsApp | Not in Queue. No `.env` file exists in the ordering platform either (only `.env.example`). |
| Supabase | Not installed locally. Claude has a Supabase connector, but that is not your project config. | **No** |
| Calendar (Google/Outlook) | No libraries | **No** |
| Payments (Stripe etc.) | No libraries. Ordering platform lists Stripe as a future phase. | **No** |
| Firebase | `firebase_admin` library installed | Not used by any of these projects; looks unrelated |
| Claude / OpenAI | Optional in ordering platform | Key names only in `.env.example` |
| GitHub | gh logged in | Yes, at account level |

Nothing in this list is live-connected, which matches your "no real APIs yet" rule.

## 5. Conflicts and gaps

1. **Missing requirements.** No BRD or SRS, so booking rules, payment rules, handoff rules and pricing for businesses are not written down anywhere.
2. **Old design vs new product.** The tax-lead `design.md` lists as non-goals: payments, appointment scheduling, multi-tenant self-service onboarding and calendar integrations. Those are now the core of the SaaS. The good news: it already planned a `business_id` column, so the tax-consultant flow can become **one business type** inside the new SaaS (the "consulting firm" template).
3. **Database choice.** The ordering platform uses its own Postgres in Docker plus Alembic migrations. Queue's design and your new stack use **Supabase**. Docker isn't installed, so the ordering platform's database tests can't currently run on this laptop either. Pick one: I recommend Supabase (hosted), which needs no Docker.
4. **Restaurant-specific code.** The ordering platform's tables use `restaurant_id` and menus/orders. The new SaaS needs `business_id`, services, staff, appointments and handoff. Copying it whole would drag in restaurant logic.
5. **Dashboard tech.** Old Queue used Streamlit; the ordering platform uses plain HTML pages served by FastAPI. A multi-business SaaS needs proper staff logins, which Supabase Auth gives you.
6. **Python.** Packages are installed globally into Python 3.14. Each project should have its own virtual environment so versions don't clash.
7. **Git identity.** Global user name and email are not set, so a new repo in Queue can't commit until you set them.
8. **Two other WhatsApp projects.** `Desktop\whatsapp-ordering-bot` (Node) is a separate project; its CLAUDE.md says not to touch it. I left it alone.

## 6. Proposed minimal plan

Goal of the first version: one fake clinic can be set up, a customer "chats" through the simulator, books an appointment, and staff can take over the chat. No real WhatsApp, calendar or payment calls.

**Step 0: setup (you run the commands in section 7).**

**Step 1: write short BRD.md, SRS.md and DESIGN.md in Queue.** One page each, based on your message, the tax-lead design and the style guide. You approve them before any code.

**Step 2: project skeleton in Queue.** Git repo, `.gitignore` (blocks `.env`), virtual environment, FastAPI app, `/healthz`, pytest, `.env.example` with names only.

**Step 3: Supabase database (migrations in `supabase/migrations`).** Tables: businesses, staff, services, business_hours, whatsapp_connections (token encrypted), customers, conversations (mode: bot or human), messages (deduplicated by WhatsApp message id), appointments, payments (status only). Every table has `business_id`, protected by Supabase row-level security.

**Step 4: reuse the proven WhatsApp core.** Copy (not move) the ordering platform's webhook signature check, message deduplication, tenant routing by phone number id, outbound sender with WhatsApp limits, encrypted tokens and the **simulator**, renaming restaurant to business. The ordering platform stays untouched.

**Step 5: booking bot.** A pure function (state + message + business config) to (replies + next state), like the ordering flow. Flow: greet, pick service, pick day, pick time slot, confirm. Slots come from business hours minus existing appointments.

**Step 6: human handoff.** Customer types "agent" or the bot gets stuck, then conversation switches to human mode, the bot goes quiet, and staff reply from a simple inbox page.

**Step 7: fake adapters for calendar and payments.** A `CalendarProvider` and `PaymentProvider` interface with fake versions only. Real Google Calendar and Stripe come later, after you approve.

**Step 8: tests for every step** (signature, dedupe, tenant isolation, booking slots, handoff), no live calls.

Later, not in the first version: self-service sign-up and billing for businesses, real Meta/Calendar/Stripe connections, reminders via WhatsApp templates, multiple languages.

## 7. Exact next commands (PowerShell)

Set your Git identity (once per computer):

```powershell
git config --global user.name "Deva"
git config --global user.email "YOUR_EMAIL_HERE"
```

Check Python through the launcher (use `py`, not `python`):

```powershell
py -3.14 --version
```

Supabase CLI, easiest way (uses Node, which you already have; first run downloads it):

```powershell
npx supabase --version
```

Or install it permanently with Scoop:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
Invoke-RestMethod -Uri https://get.scoop.sh | Invoke-Expression
scoop bucket add supabase https://github.com/supabase/scoop-bucket.git
scoop install supabase
supabase --version
```

Then create a free **development** project at https://supabase.com/dashboard (no Docker needed), and log the CLI in. It opens your browser; never paste keys into chat:

```powershell
npx supabase login
```

Only if you later want Supabase running on your laptop: install Docker Desktop. Not needed for the plan above.
