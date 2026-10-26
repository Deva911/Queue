# Phase 1 MVP: build check and review

26 Oct 2026. Built and run in a Claude cloud session (Linux, Python 3.13.17, Streamlit 1.66.1, pytest 9.1.1), not yet on Deva's Windows laptop.

## What was run

| Check | Command | Result |
|---|---|---|
| Tests | `python -m pytest -q` | **94 passed** in about 2 seconds |
| Lint | `ruff check --select E,F,W,B --line-length 120 .` | All checks passed |
| App starts | `streamlit run app.py` | Starts; health check returns `ok` |
| Click-through in a real browser (Playwright) | Home, Business profile, Services, Chat simulator, Leads and appointments | No errors. Chat: Hi, tap "Book", tap a service, pick a time, give a name, saved as PENDING; HUMAN pauses the bot; staff confirm from the dashboard |

Network is blocked inside the test run (any socket connect fails the test), and a test checks that no source file imports an HTTP or provider library.

## SRS acceptance tests

| SRS acceptance test | Covered by |
|---|---|
| Create a business and verify it persists after restart | `test_businesses.py::test_business_persists_after_restart` |
| Create/edit/deactivate a service; inactive services not offered | `test_services.py::test_add_edit_and_deactivate_service`, `test_inactive_service_is_not_offered_in_chat` |
| Valid and invalid menu responses and state transitions | `test_bot.py` (31 tests: every menu option, HELP, MENU, BACK, HUMAN, bad input keeps state) |
| Appointment request saved as pending | `test_conversation_flow.py::test_booking_is_saved_as_pending_with_a_lead` |
| Simulator never reports a calendar booking as completed | `test_conversation_flow.py::test_simulator_never_claims_a_calendar_booking` |
| Requesting a human pauses automation and shows the handoff | `test_conversation_flow.py::test_handoff_pauses_bot_until_staff_hands_back` |
| Service IDs can't be used across businesses | `test_tenant_isolation.py::test_service_from_another_business_cannot_be_booked` (refused by the code **and** by the database) |
| CSV exports contain only the selected business | `test_tenant_isolation.py::test_csv_exports_only_contain_own_records` |
| No network calls to Meta, calendar or payment providers | `tests/conftest.py` socket block + `test_no_live_calls.py` |

Also tested: staff can only make allowed status changes (PENDING to CONFIRMED, DECLINED or CANCELLED; CONFIRMED to CANCELLED), confirming a reschedule cancels the original, two customers can't request the same time, prices are whole cents and negative or 3-decimal prices are refused, customer text can't turn into a spreadsheet formula in CSV exports, and every page loads.

## Review notes

What is solid:

- **Tenant separation is built into the schema.** Child tables point at their parent with a `(business_id, id)` pair, so SQLite itself rejects an appointment for business A that uses business B's service. Every repository function takes `business_id`.
- **The bot is a plain function** (`services/bot.py`): state + text in, reply + next state + actions out. No database or Streamlit inside it, so the menu rules are cheap to test and will move unchanged to the real WhatsApp webhook in Phase 3.
- **No false confirmations.** Requests are always PENDING; the wording says "request, not a confirmed booking"; staff confirmation is labelled as a team decision, not a calendar booking; payment info is labelled demo-only and never asks for card details.
- **Bot actions run inside a savepoint**, so a failed booking (for example, the time was just taken) leaves no half-written lead or request behind.

Known limits (fine for a local prototype, to fix before real customers):

1. **No login.** The sidebar business picker is a demo convenience. Anyone running the app sees every business. Logins and row-level security are Phase 2.
2. **Customer cancellation is immediate.** The design suggests sending cancellations to staff review. The simulator cancels a PENDING or CONFIRMED request straight away (no real calendar is involved) and logs it for staff. Easy to switch to "cancel requested" if you prefer.
3. **Open times are simple.** Next 7 days, first 8 free times, slot length = service duration (30 minutes when not set). No buffers, staff rosters or holidays yet.
4. **Leads can repeat.** A new lead is made for each booking and each "talk to a person". Merging per customer can come later.
5. **Messages are stored in full** in the local database. Retention and deletion rules are needed before any real data (SRS NFR-003).
6. **Not yet run on Windows.** `tzdata` is in `requirements.txt` because Windows has no built-in time zone database. If Python 3.14 refuses a package, use 3.12.

## Decision for Deva

**Numbered menu or tap buttons?** The SRS says a numbered menu; the new landing page shows tappable options. The simulator does both: every bot message lists numbered options, and the same options appear as buttons under the chat (tapping one sends its number). Real WhatsApp supports up to 3 reply buttons or a list of up to 10 rows, so Phase 3 can map the same options onto a WhatsApp list message. Nothing needs changing now unless you want buttons only.
