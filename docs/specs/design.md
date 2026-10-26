# Technical Design
## Configurable WhatsApp Manager for Small Businesses
**Version:** 1.0  
**Status:** Phase 1 local design

## 1. Design principles
- Build a working local simulator before connecting external services.
- Keep business logic separate from UI and persistence.
- Make simulated behaviour visibly different from real integration behaviour.
- Use explicit states; never infer that a booking or payment succeeded.
- Treat tenant isolation as a core design requirement from the first database schema.
- Add external integrations only behind small adapter interfaces.

## 2. Phase 1 architecture
```text
Browser
  |
  v
Streamlit UI
  |-- Business profile and services
  |-- Customer chat simulator
  |-- Leads / appointments / handoff dashboard
  |
  v
Application services
  |-- BusinessService
  |-- ServiceCatalogueService
  |-- ConversationService
  |-- LeadService
  |-- AppointmentService
  |
  v
Repository / data-access layer
  |
  v
SQLite database
```

The first release runs locally on the developer's Windows laptop. It is a prototype and is not production-secure multi-tenant hosting.

## 3. Suggested project structure
```text
whatsapp-manager/
├── app.py
├── pages/
│   ├── 1_Business_Profile.py
│   ├── 2_Services.py
│   ├── 3_Chat_Simulator.py
│   └── 4_Leads_Appointments.py
├── src/
│   └── whatsapp_manager/
│       ├── __init__.py
│       ├── config.py
│       ├── database.py
│       ├── models.py
│       ├── repositories.py
│       ├── services/
│       │   ├── business_service.py
│       │   ├── conversation_service.py
│       │   └── appointment_service.py
│       └── integrations/
│           ├── whatsapp.py
│           ├── calendar.py
│           └── payments.py
├── tests/
│   ├── test_businesses.py
│   ├── test_services.py
│   ├── test_conversation_flow.py
│   └── test_tenant_isolation.py
├── data/                 # local database; do not commit generated DBs
├── .env.example
├── .gitignore
├── requirements.txt
├── BRD.md
├── SRS.md
├── design.md
└── README.md
```

Keep the first implementation simple. It is acceptable to begin with fewer files, but do not put database, conversation, and appointment logic all into one large `app.py`.

## 4. Core data model
### businesses
- `id` (UUID/string primary key)
- `name`
- `category`
- `address`
- `contact_email`
- `timezone`
- `logo_url`
- `status`
- `created_at`, `updated_at`

### services
- `id`
- `business_id` (foreign key)
- `name`
- `description`
- `price_minor` (integer cents, optional)
- `currency` (ISO currency code, optional)
- `duration_minutes` (optional integer)
- `is_active`
- `created_at`, `updated_at`

### business_hours
- `id`
- `business_id`
- `weekday` (0–6, documented convention)
- `opens_at`, `closes_at` (local time)
- `is_closed`

### customers
- `id`
- `business_id`
- `external_customer_key` (simulated phone/identifier; future WhatsApp ID)
- `display_name` (optional)
- `consent_status` (e.g. `UNKNOWN`, `OPTED_IN`, `OPTED_OUT`)
- `created_at`, `updated_at`

### conversations
- `id`
- `business_id`
- `customer_id`
- `state`
- `status`
- `last_message_at`
- `created_at`, `updated_at`

### messages
- `id`
- `business_id`
- `conversation_id`
- `direction` (`INBOUND`/`OUTBOUND`)
- `body`
- `created_at`
- `delivery_status` (simulated in Phase 1)

### leads
- `id`
- `business_id`
- `customer_id`
- `service_id` (optional)
- `enquiry`
- `status`
- `created_at`, `updated_at`

### appointment_requests
- `id`
- `business_id`
- `customer_id`
- `service_id`
- `requested_start_at`
- `status` (`PENDING` by default)
- `staff_note`
- `created_at`, `updated_at`

### audit_events
- `id`
- `business_id`
- `actor_id` (optional in local demo)
- `event_type`
- `entity_type`
- `entity_id`
- `details_json` (exclude secrets and unnecessary sensitive data)
- `created_at`

## 5. Tenant isolation
- All repository methods should require a `business_id` for business-owned records.
- Do not accept a business ID from a public customer message as proof of authorization.
- In production, derive authorized business IDs from the authenticated user's server-validated membership.
- Add tests that create two businesses and prove each dashboard and export only returns its own records.
- Supabase phase: enable Row Level Security (RLS) for every tenant-owned table, write policies, and test them using real user roles. Never rely only on a client-side filter.

## 6. Conversation state machine
```text
MAIN_MENU
  ├─ 1 -> SELECT_SERVICE -> REQUEST_DATE_TIME -> APPOINTMENT_PENDING
  ├─ 2 -> SERVICE_LIST -> MAIN_MENU
  ├─ 3 -> RESCHEDULE_LOOKUP -> STAFF_REVIEW
  ├─ 4 -> CANCEL_LOOKUP -> STAFF_REVIEW
  ├─ 5 -> PAYMENT_INFO (simulated) -> MAIN_MENU
  └─ 6/HUMAN -> PENDING_HANDOFF -> HUMAN_ACTIVE

Any supported state:
  MENU -> MAIN_MENU
  HELP -> show current help
  invalid input -> explain valid choices, retain state
```

The local simulator may simplify rescheduling/cancellation by creating a staff-review request rather than pretending to change a real calendar event.

## 7. Integration adapter boundaries
### WhatsApp adapter (future)
Responsibilities: send outbound messages, parse inbound webhook events, verify webhook signatures/tokens as applicable, map provider IDs to internal conversations, handle delivery receipts, deduplicate events, enforce current messaging rules.

Do not use unofficial WhatsApp Web automation. Use Meta's official platform or an approved provider. Real onboarding requires business authorization and valid account/number setup; typing a phone number into a form is not enough.

### Calendar adapter (future)
Choose Google Calendar or Microsoft Outlook first. Responsibilities: OAuth authorization, fetch free/busy or availability, create/update/cancel events, handle time zones, store provider event IDs, and reconcile errors. Confirm an appointment only after provider success. Protect against double booking using a re-check and suitable locking/idempotency strategy.

### Payment adapter (future)
Create a hosted payment link or checkout session. Store provider reference and expected amount/currency. Mark `PAID` only after verified provider status or a verified webhook. Do not collect or store raw card details. Handle expired, failed, refunded, and duplicate events.

### Supabase (future)
Use Supabase Auth for identity and PostgreSQL for persistence. Store service-role credentials only server-side. Enable RLS policies and keep migrations/versioned schema changes in Git. Supabase being installed or a project being created does not by itself connect the application; URL, keys, auth configuration, schema, and policies must be set up explicitly.

## 8. Configuration and secrets
- Keep `.env` out of Git.
- Commit `.env.example` with placeholder names only.
- Read configuration in one module.
- Validate required settings at startup.
- Do not log tokens, authorization headers, payment secrets, or full webhook payloads containing personal data.
- Phase 1 should work without any live integration credentials.

## 9. Error handling and idempotency
- UI should show a useful error without exposing stack traces to end users.
- Repository writes should use transactions where multiple related records must stay consistent.
- Future webhook handlers should persist provider event IDs and ignore duplicates.
- Retry transient provider failures safely; avoid duplicate bookings or charges.
- Keep external API calls outside database transactions where possible.

## 10. Testing strategy
- Unit tests for input validation, menu routing, state transitions, and service rules.
- Repository tests for persistence and foreign-key constraints.
- Isolation tests with at least two businesses.
- UI smoke test for key pages where practical.
- Integration adapter tests using mocks; no live API calls in normal test runs.
- Later: sandbox tests for Meta, calendar, and Stripe with explicit opt-in.

## 11. Deployment evolution
1. Local Streamlit + SQLite for prototype.
2. Hosted app with authenticated users and PostgreSQL/Supabase.
3. Official WhatsApp webhook endpoint deployed with HTTPS and verification.
4. Calendar/payment integrations configured per business with least-privilege OAuth.
5. Monitoring, backups, incident response, retention/deletion processes, and security review before real customer launch.

## 12. Key technical decisions
| Decision | Initial choice | Reason |
|---|---|---|
| UI | Streamlit | Beginner-friendly fast local dashboard |
| Language | Python | Suitable for simple workflow logic and future APIs |
| Database | SQLite | Zero-service local prototype |
| Tests | pytest | Standard Python testing |
| Version control | Git | Track changes and rollback |
| Hosted database later | Supabase/PostgreSQL | Auth and hosted relational data |
| Messaging later | Official Meta platform | Policy-aligned messaging and webhooks |
| Calendar later | One provider first | Reduce scope and integration risk |
| Payments later | Stripe or suitable regional provider | Hosted checkout and verified status |
