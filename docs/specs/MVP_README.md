# WhatsApp Manager — MVP Starter
A beginner-friendly prototype for configuring a small business's services and simulating WhatsApp-style enquiries, appointment requests, and human handoff.

> **Important:** Phase 1 is a local simulator. It does not send real WhatsApp messages, access a real calendar, or take payments. Appointment requests remain pending until manually reviewed. Do not use this prototype with real customer data.

## 1. Documents
- `BRD.md` — business goals, scope, workflows, and delivery phases.
- `SRS.md` — detailed software requirements and acceptance tests.
- `design.md` — architecture, data model, state machine, and integration boundaries.

## 2. Phase 1 technology
- Python
- Streamlit
- SQLite
- pytest
- Git

Supabase/PostgreSQL, Meta WhatsApp Business Platform, a calendar provider, and a payment provider are future integrations. Installing a tool or creating an account does not automatically configure it in this application.

## 3. Prerequisites on Windows
Install:
1. Python 3.11 or newer (ensure Python is added to PATH).
2. Git for Windows.
3. Claude Code, if you plan to use it to implement the project.

Verify in PowerShell:
```powershell
python --version
git --version
```

## 4. Create and activate a virtual environment
Open PowerShell in the project directory:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

If PowerShell blocks activation, you can use Command Prompt instead:
```bat
.venv\Scripts\activate.bat
```

## 5. Install dependencies
Once `requirements.txt` has been created:
```powershell
pip install -r requirements.txt
```

Suggested initial `requirements.txt`:
```text
streamlit
pytest
python-dotenv
```

Keep dependencies minimal until the first working flow is tested.

## 6. Configure environment
Copy the example file:
```powershell
Copy-Item .env.example .env
```

The local simulator should run without live provider credentials. Never paste secrets into source files, prompts, screenshots, Git commits, or issue trackers. `.env` must be ignored by Git.

Suggested `.env.example`:
```dotenv
APP_ENV=local
DATABASE_URL=sqlite:///data/whatsapp_manager.db
# Future integrations only — leave blank for Phase 1.
META_WHATSAPP_TOKEN=
META_PHONE_NUMBER_ID=
META_VERIFY_TOKEN=
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
STRIPE_SECRET_KEY=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```

Use only the settings actually implemented by the application. Do not add real secrets to `.env.example`.

## 7. Run the app
After `app.py` is implemented:
```powershell
streamlit run app.py
```
Streamlit normally prints a local URL in the terminal. Open that URL in your browser.

## 8. Run tests
```powershell
pytest -q
```
Do not claim the project works unless the commands were run and the result was observed. If tests fail, capture the error and fix it before adding more features.

## 9. Git workflow
Check current state:
```powershell
git status
```

After reviewing the files you intend to include:
```powershell
git add BRD.md SRS.md design.md README.md requirements.txt .gitignore app.py src tests
git commit -m "Add WhatsApp Manager MVP foundation"
```

Do not commit `.env`, database files, tokens, passwords, or customer data. If Git is already initialized, do not run `git init` again without checking the existing repository.

Suggested `.gitignore`:
```gitignore
.venv/
__pycache__/
.pytest_cache/
.env
*.py[cod]
data/
.streamlit/secrets.toml
.DS_Store
```

Review `git status` before every commit.

## 10. Build order
1. Inspect the existing repository and read all three specification documents.
2. Confirm Python/Git versions and working-tree state.
3. Create the minimal app shell and SQLite schema.
4. Implement business profile and service catalogue.
5. Implement the simulated menu and conversation state.
6. Add lead capture and pending appointment requests.
7. Add human handoff and staff dashboard.
8. Add unit tests and tenant-isolation tests.
9. Verify the app starts and tests pass.
10. Only then plan Supabase and external integrations.

## 11. Prompt for Claude Code
Paste this into Claude Code from the project directory:

> Read `BRD.md`, `SRS.md`, `design.md`, and `README.md` before making changes. Inspect the current repository and report what already exists, Git status, Python version, dependencies, and any configuration files. Do not reveal secret values. Do not overwrite existing work. First propose a small implementation plan for Phase 1 only: local Streamlit simulator, SQLite persistence, services, leads, pending appointment requests, human handoff, and pytest tests. Do not call Meta, calendar, payment, or Supabase APIs. Wait for my approval before editing files. After implementation, run the tests and app startup check, report the exact commands and actual results, and list any known limitations.

## 12. Before connecting live services
- Confirm official provider requirements and current policies.
- Set up authentication, tenant authorization, secret storage, logging, backups, and deletion/retention processes.
- Add verified webhook handling and idempotency.
- Test using provider sandboxes and test accounts.
- Never confirm a booking or payment unless the relevant provider confirms success.
- Complete a privacy/security review before onboarding real customers.
