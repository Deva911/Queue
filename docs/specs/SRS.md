# Software Requirements Specification (SRS)
## Configurable WhatsApp Manager for Small Businesses
**Version:** 1.0  
**Status:** MVP specification

## 1. Introduction
This document defines functional and non-functional requirements for the WhatsApp Manager MVP. The first release is a local simulator, not a production messaging service.

## 2. System context
The initial application is a local Python web app using Streamlit, SQLite, and pytest. A simulated customer chat represents the WhatsApp interaction. External services are intentionally disabled in this phase.

Future integrations may include:
- Meta WhatsApp Business Platform (official Cloud API and webhooks).
- One calendar provider initially: Google Calendar or Microsoft Outlook.
- Stripe for payment links and payment status.
- Supabase/PostgreSQL for hosted data and authentication.

## 3. User classes
- `OWNER`: manages one or more authorized business workspaces and settings.
- `STAFF`: handles assigned business leads, appointment requests, and conversations.
- `CUSTOMER`: interacts through the simulated chat in the MVP; later through WhatsApp.
- `PLATFORM_ADMIN`: operational role, restricted and audited.

The local MVP may use a clearly labelled demo business selector rather than production authentication. This must not be presented as secure multi-user authentication.

## 4. Functional requirements
### FR-001 Business profile
The system shall allow an authorized owner to create and edit:
- business name (required),
- business category,
- address (optional),
- contact email (optional),
- time zone (required or defaulted explicitly),
- profile image URL/path (optional),
- business status (active/inactive).

### FR-002 Service catalogue
The system shall allow an authorized owner to create, view, edit, activate, and deactivate services. Each service shall include a business ID, name, description, optional price, optional duration in minutes, and active status. Price values must be non-negative and stored as decimal/cents, not floating-point currency.

### FR-003 Business hours
The system shall store configurable opening hours by day of week and support closed days. The MVP may display these settings but must not claim live calendar availability.

### FR-004 Customer menu
The simulator shall display a greeting and numbered menu. Default options:
1. Book an appointment
2. View services and prices
3. Reschedule an appointment
4. Cancel an appointment
5. Payment information
6. Talk to a person

Business-specific options may be configured, but core navigation and human handoff must remain accessible.

### FR-005 Input validation
The system shall validate menu responses and required fields. Invalid input shall produce a helpful message and preserve the current conversation state. Support `HELP`, `MENU`, `BACK`, and `HUMAN` where applicable.

### FR-006 Conversation state
The system shall persist the current conversation state and associate each conversation with one business and one customer identifier. The simulator shall handle at least: `MAIN_MENU`, `SERVICE_LIST`, `BOOKING_SERVICE`, `BOOKING_TIME`, `PENDING_HANDOFF`, and `COMPLETED`.

### FR-007 Lead capture
The system shall record a lead with business ID, customer identifier, optional name, enquiry/service, status, created timestamp, and updated timestamp. Status values shall be controlled and documented.

### FR-008 Appointment requests
The system shall create an appointment request with business ID, service ID, customer identifier, requested start time, optional notes, status, and timestamps. In the MVP, new requests shall default to `PENDING`. The system shall not claim a calendar slot is available or confirm a booking based on unverified assumptions.

### FR-009 Appointment management
Authorized staff shall be able to view and update appointment request status to `CONFIRMED`, `DECLINED`, or `CANCELLED`, with an audit note. In the MVP, staff confirmation is a manual action and is not a claim that an external calendar has been updated.

### FR-010 Human handoff
The system shall allow the customer to request a person from any supported menu state. It shall mark the conversation `PENDING_HANDOFF`, make it visible in the dashboard, and pause automated responses until staff resumes automation.

### FR-011 Payment state
The MVP shall only simulate payment information/status. It shall never collect or store card details. Any simulated payment must be visibly labelled as a demo. Later integration must verify provider status/webhooks before setting `PAID`.

### FR-012 Dashboard
The dashboard shall show business profile, services, recent leads, conversation/handoff status, and appointment requests. Records shall be filtered to the selected authorized business.

### FR-013 Audit history
The system should record important state changes such as appointment status changes, handoff, and service activation changes with actor and timestamp where available.

### FR-014 Integration configuration
The MVP shall not require real API credentials and shall not make live API calls. Future integrations must be opt-in, documented, and use environment secrets or a managed secret store.

### FR-015 Data export
The MVP may provide a simple CSV export of business-owned leads and appointment requests. Export must apply the same business scoping as the dashboard.

## 5. Data requirements
Recommended entities:
- `businesses`
- `services`
- `business_hours`
- `customers`
- `conversations`
- `messages`
- `leads`
- `appointment_requests`
- `audit_events`
- later: `integration_accounts`, `webhook_events`, `payment_records`, `staff_members`

All business-owned entities must include `business_id` directly or be reachable through a parent entity with an enforced tenant-scoped relationship.

## 6. Data validation
- Business name and service name cannot be blank.
- Price must be zero or greater; currency must be explicit when price is supplied.
- Duration must be a positive integer when supplied.
- Dates/times must be valid and interpreted in the business time zone.
- User-provided text must be length-limited and safely rendered.
- Unknown menu selections must not trigger unintended state changes.
- A request referencing a service must verify that the service belongs to the same business.

## 7. Non-functional requirements
### NFR-001 Security
Use parameterized database queries or ORM-safe methods. Never commit API keys, passwords, access tokens, or `.env` files. Restrict production secrets to server-side execution. Redact sensitive data from logs.

### NFR-002 Tenant isolation
Every read, update, and delete must be scoped to the authorized business. Add tests proving that a user/business cannot access another business's records.

### NFR-003 Privacy
Collect only data needed for the workflow. Document retention and deletion procedures before production. Provide a path for customer data correction/deletion requests. Do not use customer conversations to train models without appropriate authorization and legal review.

### NFR-004 Reliability
Database failures must produce a useful error without falsely reporting success. Future webhook processing must be idempotent and retry-safe.

### NFR-005 Usability
The UI should use plain language, provide clear status labels, and make demo/simulated features obvious.

### NFR-006 Maintainability
Use small modules, type hints where practical, documented configuration, and automated tests. Avoid putting all business logic into Streamlit page code.

### NFR-007 Observability
Future hosted versions should include structured logs, error monitoring, health checks, and alerting without logging secrets or unnecessary message content.

### NFR-008 Accessibility
Use readable contrast, clear labels, keyboard-friendly controls where supported, and avoid conveying status by colour alone.

## 8. Suggested status values
- Lead: `NEW`, `IN_PROGRESS`, `QUALIFIED`, `CLOSED`, `OPTED_OUT`
- Conversation: `BOT_ACTIVE`, `PENDING_HANDOFF`, `HUMAN_ACTIVE`, `CLOSED`
- Appointment request: `PENDING`, `CONFIRMED`, `DECLINED`, `CANCELLED`
- Payment: `NOT_STARTED`, `PENDING`, `PAID`, `FAILED`, `REFUNDED` (payment integration phase only)

## 9. Acceptance tests
- Create a business and verify it persists after restart.
- Create/edit/deactivate a service and verify inactive services are not offered to customers.
- Send valid and invalid menu responses and verify state transitions.
- Request an appointment and verify it is saved as pending.
- Confirm that the simulator never reports an external calendar booking as completed.
- Request a human and verify automation pauses and the handoff is visible.
- Verify service IDs cannot be used across business boundaries.
- Verify CSV exports contain only the selected business's records.
- Verify no network calls to Meta, calendar, or payment providers occur in Phase 1.

## 10. Requirements traceability
| Business need | Requirements | Acceptance evidence |
|---|---|---|
| Self-service setup | FR-001, FR-002, FR-003 | Profile and service CRUD tests |
| WhatsApp-style menu | FR-004, FR-005, FR-006 | Conversation state tests |
| Lead tracking | FR-007, FR-012, FR-015 | Persistence and export tests |
| Appointment handling | FR-008, FR-009 | Pending-state and staff-action tests |
| Human support | FR-010 | Handoff test |
| Safe future payments | FR-011, FR-014 | Demo labels and no-live-call test |
| Secure tenant separation | NFR-001, NFR-002, NFR-003 | Isolation tests and review |
