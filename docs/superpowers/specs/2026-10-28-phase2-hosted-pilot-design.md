# Phase 2 design: hosted pilot with a small API

28 Oct 2026. Status: **draft, waiting for Deva's approval.** Nothing is built until it is approved.

## 1. Intent

Phase 1 is a local simulator with sign-in and roles (PR #2). Phase 2 puts it online so **one real pilot business** (owner plus staff) can use it day to day, safely. It also builds the small API service now, so that Phase 3 only has to add the WhatsApp webhook to a server that already runs, is tested and is deployed.

Success at the end of Phase 2:
- The pilot owner and staff sign in at a real HTTPS address and use the dashboard for two weeks without our help.
- Automated tests prove that no person can read or change another business's data, both through the API and directly in the database.
- A backup has been restored into a spare database at least once, and a bad deploy has been rolled back at least once.

## 2. Goals, non-goals, anti-goals

**Goals**
1. Hosted Postgres (Supabase) replaces the SQLite file.
2. Supabase Auth replaces our local passwords, which adds email invites and password reset.
3. Row-level security (RLS) in the database, as a second lock behind the role checks we already have.
4. A small API service (FastAPI) that holds all business logic; the Streamlit dashboard calls it.
5. Hosting with HTTPS, daily backups, a tested restore, rollback, uptime checks and error logs.
6. Retention runs on its own: chat messages older than each business's setting (default 90 days) are deleted daily.

**Non-goals (later phases):** real WhatsApp (Phase 3), calendar (4), payments (5), self-service business sign-up, billing, a mobile app, more than one pilot business.

**Anti-goals (a failure even if everything else works)**
- Any path where one business sees another's data.
- The Supabase service-role key, or any key, reaching the browser, Streamlit, Git or logs.
- Real customer data going in before the backup restore and RLS tests pass.
- Telling a customer a booking is confirmed when staff haven't confirmed it (unchanged from Phase 1).

## 3. Constraints

- Keep Phase 1's rules: requests stay PENDING until staff act; the bot is a plain function; every query takes `business_id`.
- Python only. No second language.
- Secrets only in the host's secret store and a local `.env` that is never committed.
- Deva works on Windows without Docker. Nothing in Deva's day-to-day may need Docker. CI can use it.
- Hosting region close to India (the pilot is expected to be there; see open question Q1).

## 4. Approaches considered

| | Approach | Trade-off | Decision |
|---|---|---|---|
| A | Streamlit talks to the database directly, hosted with Supabase | Least work; but Phase 3 still needs a web server for Meta, and the dashboard holds database credentials | Not chosen |
| **B** | **A plus a small FastAPI service. The dashboard only talks to the API; the API alone talks to the database** | More work now; the webhook, auth checks and RLS all live in one place that Phase 3 reuses | **Chosen by Deva, 28 Oct** |
| C | Rebuild the dashboard as a JavaScript web app on Supabase | Best on phones; rewrites every screen and splits logic across two languages | Not chosen |

## 5. How it fits together

```
 browser ── HTTPS ──► Caddy (one domain, e.g. app.<domain>)
                        ├── /        → Streamlit dashboard (no database access, no secrets but the API URL)
                        └── /api/*   → FastAPI service ──► Supabase Postgres (RLS on)
                                         │                  Supabase Auth (sign-in, invites, reset)
                                         └── Phase 3: /api/webhooks/whatsapp
```

### 5.1 The API service (new `api/` package)
- FastAPI app that reuses `whatsapp_manager.services` unchanged where possible. The services keep taking a connection and `business_id`; the API adds auth and turns errors into HTTP responses (`ValidationError` → 400, `AuthError` → 403, `NotFoundError` → 404).
- Endpoints mirror what the pages do today: businesses, hours, services, appointment requests and staff decisions, conversations and handoff, leads, team, audit log, CSV export, retention, plus `POST /api/simulator/messages` (the same `handle_inbound` that the WhatsApp webhook will call in Phase 3) and `GET /api/health`.
- Every endpoint that acts on a business calls the existing `auth_service.require(actor, business_id, permission)` first. The permission table does not change.
- OpenAPI docs are generated automatically, so the dashboard and later the webhook use a documented contract.

### 5.2 Sign-in (Supabase Auth)
- Email and password through Supabase Auth. Invites and password-reset emails come from Supabase.
- The API checks the Supabase access token (a signed JWT) on every request and loads the `Actor` from our own `users`/`memberships` tables by the token's user id. Roles and the platform-admin flag live **only in our tables**, never in anything the browser can edit.
- Our `users` table keeps profile and admin flag and drops `password_hash`, `failed_logins` and `locked_until` (Supabase handles passwords and rate-limits sign-in). `auth_service` keeps `Actor`, `require`, the permission table and the team functions; `authenticate` and the password helpers are replaced.
- **Fixes "refresh signs you out":** sign-in happens on an API route that sets a secure, HTTP-only cookie on the shared domain. Streamlit reads that cookie on each page load (`st.context.cookies`) and passes it to the API. JavaScript never sees the token.
- The first platform admin is created once by a command run from the laptop (`python -m api.create_admin`), not by "first visitor wins", because the site is now public.

### 5.3 Database (Supabase Postgres)
- The current schema is rewritten as versioned SQL migration files in `supabase/migrations/`, kept in Git. `PRAGMA user_version` gives way to the migration history.
- `repositories.py` moves from `sqlite3` to `psycopg` (Postgres). Query text changes (`?` → `%s`, case-insensitive email via `lower()`), but the function names and arguments stay, so the services barely change.
- **RLS on every business-owned table.** The API connects as a limited database role (not the service role). Per request it opens a transaction, sets the signed-in user's id, and the policies allow a row only if that user has a membership in the row's business, or is a platform admin. So a missing `business_id` filter in a future query returns nothing instead of leaking.
- The service-role key is used only by the admin command and the invite call, server side.

### 5.4 Dashboard (Streamlit)
- The pages keep their layout. Data calls go through a small `api_client.py` instead of the repositories, so Streamlit needs no database credentials.
- Phase 1's local mode stays for development, as one setting: `DATA_BACKEND=local` (today's SQLite code path, no network) or `api`. This keeps Deva's laptop setup Docker-free. (Calls I made: see §8.)

### 5.5 Hosting and operations
- One container image runs Caddy, Streamlit and FastAPI, deployed to a small managed host in or near Mumbai, with HTTPS and secrets in the host's secret store.
- **Deploys:** GitHub Actions runs lint and tests against a throwaway Postgres, builds the image, and deploys on merge to `main`. Rollback means redeploying the previous image. Migrations are written so the previous image still works (add first, remove a release later).
- **Backups:** Supabase daily backups (needs the paid plan; see Q3) plus our own nightly `pg_dump` to separate storage. A restore into a spare database is rehearsed before real data goes in, and then once a month.
- **Monitoring:** `/api/health` checked every minute by an uptime service; errors logged with ids only, never message bodies, phone numbers or tokens.
- **Retention job:** a daily scheduled task calls the retention endpoint for each business. The per-business setting is a new column, default 90 days.

## 6. Testing

- Everything Phase 1 tests stays (150 tests today), running against Postgres in CI.
- API tests per endpoint: signed out → 401, wrong business → 403, wrong role → 403, right role → works.
- RLS tests that skip the API and query the database as two different users, proving each sees only their own business's rows.
- A deploy smoke test after every deploy: health check, sign in as a test user, load each page.

## 7. Rollout

1. Build and test against a Supabase project used only for development.
2. Create the production Supabase project and host; rehearse a restore; run the security checklist.
3. Deva creates the pilot business and invites its owner; the owner invites staff.
4. Two-week pilot, with fake customers in the simulator until Phase 3 brings real WhatsApp.

## 8. Calls I made (please check)

1. **Caddy and one domain**, so the sign-in cookie is shared between the dashboard and the API. This is what fixes "refresh signs you out".
2. **Local mode stays** (`DATA_BACKEND=local`) so you can run everything on your laptop without Docker. Tests run on SQLite locally and on Postgres in CI. If keeping two database paths becomes painful, we drop local mode at the end of Phase 2.
3. **The pilot starts with an empty database.** No demo data is copied across.
4. **The first admin is made by a command, not by the first visitor**, because the site is public.
5. **Default retention is 90 days**, and owners can change it.
6. **One container on one small host** for the pilot. We split it into separate services only if load needs it.

## 9. Open questions for Deva

- **Q1. Where is the pilot business, and what kind of business is it?** This sets the hosting region and the privacy rules we follow (India's DPDP Act if it's in India).
- **Q2. Which web address?** A domain you own, or a free subdomain from the host for now.
- **Q3. Is a monthly cost OK?** Daily backups need Supabase's paid plan, and the host also costs a little each month. I'll get current prices before anything is bought.

## 10. Left to the builder

The exact host (any that offers Mumbai or Singapore, containers, secrets and HTTPS), the uptime service, how the API client is laid out, the migration tooling, and the CI details. All must meet the constraints above.
