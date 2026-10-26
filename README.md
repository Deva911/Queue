# WhatsApp Manager

A WhatsApp assistant for small service businesses. Customers message the business on WhatsApp, pick from a numbered menu (book, services, reschedule, cancel, payment info, talk to a person), and staff manage leads and appointment requests from a dashboard.

## Status

**Planning and design stage. The MVP code is not in this repo yet.** It will be built on Deva's laptop (in `C:\Users\Devagopu\Queue`) and pushed here once Phase 1 is working.

## Phases

1. Local simulator: Python, Streamlit, SQLite, pytest. No real WhatsApp, calendar, payment or Supabase calls.
2. Supabase database
3. Meta WhatsApp Cloud API
4. Calendar integration
5. Stripe payments

## What's in this repo

| Path | What it is |
|---|---|
| `landing-page/index.html` | Marketing landing page (open it in a browser) |
| `docs/whatsapp-manager-plan-v2.md` | Revised Phase 1 build plan |
| `docs/whatsapp-manager-audit.md` | Setup audit of the development machine |
| `docs/PROJECT_TRACKER.md` | Project tracker: stages, tasks and status |
| `docs/QUEUE_SETUP_GUIDE.md` | Guide from local code to a live WhatsApp bot (Supabase, Meta, Render) |
| `prototypes/tax-leads/` | Earlier tax-lead bot prototype: plan, structure diagram and screenshots |

## Secrets

Never commit `.env` or any keys, tokens or passwords. See `docs/QUEUE_SETUP_GUIDE.md` for where they go.
