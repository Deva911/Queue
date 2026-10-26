# WhatsApp Manager SaaS: Project Tracker

**Owner:** Deva · **Project manager:** Claude
**Last updated:** 26 Oct 2026, 8:35am India time (03:05 UTC)
**Daily update:** every day at 8:33am India time, posted in the thread "Track WhatsApp Manager progress daily"

## How this tracker works (plain language)

- Every task has a status: **Not started**, **In progress**, **Blocked**, **Waiting on Deva**, or **Done**.
- A task is only marked **Done** when there is proof: a file you can see, a test result, a commit, or a screenshot. A plan or a message saying "will do" is not proof.
- The project moves in **stages**. A stage is only closed when every exit check for it is ticked, and Deva agrees.
- Evidence comes from the build thread "Plan WhatsApp Manager SaaS setup" and from a read-only look at `C:\Users\Devagopu\Queue`.

## Today at a glance

| | |
|---|---|
| **Stage** | 0. Project control |
| **Overall status** | 🟠 Amber: Deva said "go", but the build hasn't started yet |
| **Waiting on** | (1) Claude Code on Deva's laptop to come back online so the build can start; (2) the 4 spec files in `C:\Users\Devagopu\Queue` |
| **Waiting since** | Laptop session offline since 25 Oct 16:12 UTC (about 11 hours); "go" given 25 Oct 18:20 UTC |
| **Code written so far** | None (correct: no code is allowed before Deva approves) |

## Stage gates

| # | Stage | Goal | Exit checks | Status |
|---|---|---|---|---|
| 0 | Project control | Save specs, check the folder, set up Git safely | All 4 docs in Queue folder; docs read and checked against the plan; `.gitignore` blocks `.env` and the database file; Phase 1 scope agreed by Deva | 🟠 In progress (blocked on Deva) |
| 1 | Local foundation | Streamlit app shell, SQLite database, pytest | App starts; database is created and keeps data; tests run and results are recorded | ⚪ Not started |
| 2 | Business setup | Business profile, services, opening hours | Create, edit and save work; bad input is rejected; inactive services hidden | ⚪ Not started |
| 3 | Chat simulator | Menu, conversation memory, leads, appointment requests, handing chats to staff | Main flows and bad-input tests pass; appointments stay PENDING until staff act; handoff shows in the inbox | ⚪ Not started |
| 4 | MVP check | All tests, privacy review, saved Git checkpoint | Acceptance checklist passes; known limits written down; reviewed commit exists | ⚪ Not started |
| 5 | Hosted foundation | Supabase database, logins, keeping each business's data separate | Login and data-separation tests pass; HTTPS, backups and rollback tested | ⚪ Not started |
| 6 | WhatsApp | Official Meta WhatsApp API | Test number works end to end; webhook checks and duplicate handling tested; policies reviewed | ⚪ Not started |
| 7 | Calendar | Google Calendar or Outlook (pick one first) | Free slots, book, reschedule, cancel, clashes and failures tested | ⚪ Not started |
| 8 | Payments and reminders | Hosted checkout, verified payment events, reminders with consent | Payment only marked paid after the provider confirms; opt-out and retry tests pass | ⚪ Not started |
| 9 | Ready to launch | Security, monitoring, recovery, pilot, go/no-go | Launch-blocking tests pass; rollback and support tested; Deva approves launch | ⚪ Not started |

## Stage 0 tasks

| Task | Owner | Status | Evidence |
|---|---|---|---|
| Audit the laptop and Queue folder (read-only) | Claude | ✅ Done | [whatsapp-manager-audit.md](/mnt/project-files/whatsapp-manager-audit.md), 25 Oct 00:00 UTC |
| Write a Phase 1 plan that follows Deva's specs | Claude | ✅ Done | [whatsapp-manager-plan-v2.md](/mnt/project-files/whatsapp-manager-plan-v2.md), 25 Oct 00:04 UTC |
| Save BRD.md, SRS.md, design.md, README.md into `C:\Users\Devagopu\Queue` | Deva | 🟠 Waiting on Deva | Folder checked 26 Oct 03:03 UTC: still **empty**. Fallback: the build can use the copies Deva uploaded to the project chat |
| Set Git name and email (`git config --global ...`) | Deva | ❓ Not confirmed | No reply in the build thread yet |
| Say "go" | Deva | ✅ Done | Deva wrote "go" in the project chat, 25 Oct 18:20 UTC; passed to the build thread 18:20 UTC |
| Open Claude Code on the laptop so the build session is online | Deva | 🟠 Waiting on Deva | Build session offline since 25 Oct 16:12 UTC; the "go" message is waiting for it |
| Read all 4 docs in full and list any conflicts inside them | Claude | ⚪ Not started | Needs the files first |
| Create the project folder setup (`git init`, virtual environment, `.gitignore`, `.env.example`) | Claude | ⚪ Not started | Needs Deva's "go" |
| Deva approves Phase 1 scope | Deva | ⚪ Not started | |

## Decisions Deva needs to make

| # | Decision | Recommendation | Status |
|---|---|---|---|
| D1 | Start fresh in the empty Queue folder, or build on the restaurant ordering platform? | Start fresh in Queue (the docs' layout fits it) | Open, the new plan already assumes "fresh" |
| D2 | Approve the Phase 1 plan (local simulator only: Streamlit, SQLite, pytest) | Approve | ✅ Treated as approved: Deva said "go" 25 Oct 18:20 UTC |
| D3 | May Claude add a one-line Windows note to the README (use `py`, not `python`)? | Yes | Open |
| D4 | Time and time zone for the daily update | 8:33am India time | ✅ Decided: Deva confirmed 25 Oct 18:17 UTC |

## Risks

| # | Risk | Impact | Likelihood | What we do about it |
|---|---|---|---|---|
| R1 | Specs never reach the laptop, so the build stays paused | High | Medium | Daily reminder; fallback is building from the uploaded copies |
| R7 | Build session on the laptop is offline, so approved work can't start | High | High (today) | Deva opens Claude Code in the Queue folder; nudge in each daily update |
| R2 | Python 3.14 is very new and a package may not install | Medium | Low | Fall back to Python 3.12 (`winget install Python.Python.3.12`) |
| R3 | `python` opens the Microsoft Store on this laptop | Low | High | Use `py` to create the virtual environment; `python` works inside it |
| R4 | Secrets (keys, `.env`) end up in Git | High | Low | `.gitignore` first, before any code; never print secrets |
| R5 | Scope grows into WhatsApp, calendar or payments too early | High | Medium | Phase 1 is simulator only; no live APIs until their stage |
| R6 | Mixing up the old tax-lead bot, the restaurant platform and the new product | Medium | Medium | New product lives only in Queue; the other two stay untouched |

## Next 1 to 3 tasks

1. **Deva:** turn on the laptop and open Claude Code in `C:\Users\Devagopu\Queue` so the build session comes back online.
2. **Deva:** save the four spec files into that folder (if skipped, the build uses the uploaded copies), and run the two `git config --global` commands.
3. **Claude:** read the four docs, report any conflicts, and set up the project folder (Stage 0 finish, Stage 1 start).

## Change log

| Date (UTC) | What changed | Evidence |
|---|---|---|
| 26 Oct 2026 | Daily check: "go" given; build not started because the laptop session is offline; Queue still empty. Still Stage 0, Amber. | Build thread; Queue folder listing 03:03 UTC |
| 25 Oct 2026 | Deva said "go" in the project chat. | Message 18:20 UTC |
| 25 Oct 2026 | Deva confirmed the 8:33am India time daily update. | Thread reply, 18:17 UTC |
| 25 Oct 2026 | Tracker created. Stage 0, Amber. Audit and plan done; waiting on Deva for the spec files. | Build thread; Queue folder empty at 16:19 UTC |

## Status report template

```text
Project: WhatsApp Manager SaaS
Date:
Stage:
Overall status: Green / Amber / Red
Completed since last update:
Evidence (commit / tests / screenshots / files):
In progress:
Waiting on Deva / decisions needed:
Risks:
Next 1–3 tasks:
Stage-gate decision:
```

## Rules

- Never mark a task Done without evidence.
- Keep secrets out of Git, docs, prompts and logs.
- No live APIs during Phase 1.
- Never say a booking or payment worked without the provider confirming it.
- No launch until data separation, consent, monitoring, backup and security checks pass.
