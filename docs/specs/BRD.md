# Business Requirements Document (BRD)
## Configurable WhatsApp Manager for Small Businesses
**Version:** 1.0  
**Status:** MVP specification  
**Last updated:** 2026-10-24

## 1. Purpose
Build a self-service platform that helps small, customer-facing businesses manage enquiries and routine service workflows through WhatsApp. A business owner configures business details, services, availability, and workflow options in a dashboard. Customers use that business's WhatsApp channel to view services, request appointments, receive updates, make payments through an approved provider, and ask for a human.

The product is intended for appointment- and service-led businesses such as tax consultants, dentists, clinics, salons, and other local service providers.

## 2. Problem statement
Small businesses often handle enquiries, appointment coordination, reminders, and follow-ups manually. Messages get missed, staff repeat the same answers, appointments conflict, and owners have limited visibility into leads and customer activity.

## 3. Product vision
Provide a simple, configurable WhatsApp-based front desk that automates predictable tasks while making it easy to transfer a conversation to a person.

## 4. Business objectives
- Reduce repetitive manual responses and missed enquiries.
- Make appointment requests and their status visible to business staff.
- Help businesses configure their own services and basic rules without needing to code.
- Support payment links and reminders through approved providers in later phases.
- Give each business a secure, separate workspace.
- Keep a clear audit trail for important changes and booking/payment state.

## 5. Target users and roles
### Business owner/admin
Creates the business workspace, configures profile, services, business hours, booking rules, staff access, and integrations.

### Staff member
Reviews enquiries, manages appointment requests, handles customer conversations, and takes over a conversation when needed.

### Customer
Contacts a business through its WhatsApp channel, reviews available information, and requests a service or appointment.

### Platform operator
Maintains the platform, monitors failures, manages deployment, and supports onboarding. Platform operators must not casually access customer content.

## 6. MVP scope
### Included in the first milestone
- Local web dashboard and simulated WhatsApp conversation.
- Business profile: name, category, address, contact email, time zone, logo path/URL.
- Service catalogue: name, description, price (optional), duration (optional), active/inactive.
- Business hours and simple appointment rules.
- Numbered customer menu with configurable options.
- Lead and conversation records.
- Appointment requests stored as `pending`; no false confirmation without verified availability.
- Human handoff flag and staff notes.
- Basic dashboard lists for leads, conversations, and appointment requests.
- SQLite persistence and automated tests.
- Demo data and clear setup instructions.

### Explicitly out of scope for the first milestone
- Sending or receiving real WhatsApp messages.
- Connecting or registering a real WhatsApp Business number.
- Real calendar reads/writes or live conflict checks.
- Charging cards or confirming real payment.
- Automated production reminders or scheduled campaigns.
- AI-generated advice, autonomous diagnosis, or tax/legal/medical recommendations.
- Multi-location franchise analytics, marketing campaign automation, and advanced reporting.
- Production deployment or claims of compliance certification.

## 7. Later-phase capabilities
- Official Meta WhatsApp Business Platform onboarding and webhooks.
- Google Calendar or Microsoft Outlook calendar integration (select one first).
- Stripe payment links and verified webhook status.
- Consent-aware reminders and follow-ups using permitted WhatsApp message templates.
- Staff notifications and human handoff workflow.
- PostgreSQL/Supabase for hosted persistence and authentication.
- Role-based access, operational monitoring, backups, and deployment hardening.

## 8. Core business workflows
### 8.1 Business onboarding
1. Owner creates an account.
2. Owner enters business profile and time zone.
3. Owner adds services and prices/durations.
4. Owner configures business hours and booking rules.
5. Owner previews the simulated customer conversation.
6. Owner can later connect approved integrations through explicit authorization.

### 8.2 Customer enquiry
1. Customer sends a message to the business channel.
2. System displays a greeting and numbered menu.
3. Customer selects an option, such as services, appointment, or human help.
4. System validates input and guides the customer through the relevant flow.
5. The conversation and lead are stored against the correct business workspace.

### 8.3 Appointment request
1. Customer chooses a service.
2. System asks for requested date/time and any required contact details.
3. In the local MVP, request is saved as `pending`.
4. Staff reviews and confirms, declines, or contacts the customer.
5. A future calendar integration may confirm a slot only after availability is checked and the provider reports success.

### 8.4 Human handoff
1. Customer chooses “Talk to a person” or types a supported handoff keyword.
2. Conversation is flagged for staff.
3. Automation stops or pauses according to the configured rule.
4. Staff sees the conversation and can record a resolution.
5. Automation resumes only when staff explicitly returns the conversation to bot handling.

### 8.5 Payment
In the MVP, payment is a simulated status only. In a later phase, the system may create a payment link through a provider such as Stripe. The system must never mark a payment paid based only on a customer message or browser redirect; it must verify provider status or a signed webhook.

## 9. Business rules
- Every business-owned record must have a `business_id`.
- Data belonging to one business must never be visible or editable by another business.
- An appointment request is not a confirmed appointment until availability and booking success are verified.
- A payment is not paid until the payment provider confirms it.
- A customer must be able to request a human at any point in a supported conversation.
- Invalid menu input receives a helpful prompt and does not corrupt conversation state.
- Opt-outs must be respected before sending future proactive messages.
- Production WhatsApp messaging must follow Meta's current platform policies, customer-service window rules, approved template rules, and applicable consent requirements.
- Do not collect sensitive information unless it is necessary, justified, and protected. Avoid collecting medical details, tax documents, identity documents, or payment-card details in the MVP.

## 10. Success measures
MVP success is measured by:
- A new business profile can be created and saved.
- Services can be added, edited, activated, and deactivated.
- The simulated menu supports valid and invalid input.
- Leads and appointment requests persist after restart.
- Human handoff is visible to staff.
- Automated tests pass.
- No real external API is called in the local MVP.

Later operational metrics may include enquiry response time, appointment request completion, staff handoff rate, confirmed appointment rate, reminder delivery, and payment completion.

## 11. Risks and mitigations
| Risk | Mitigation |
|---|---|
| Mistakenly claiming bookings are confirmed | Use `pending` state until provider-backed confirmation exists |
| Cross-business data leakage | Enforce tenant scoping in every query and test it |
| WhatsApp policy violations | Use official API and review current Meta requirements before launch |
| Duplicate webhooks or events | Add idempotency keys and event processing state in integration phase |
| Payment fraud or false payment state | Verify signed provider webhooks/status |
| Sensitive data exposure | Minimize collection, restrict access, redact logs, document retention |
| Scope grows too quickly | Complete and test local simulator before external integrations |

## 12. Delivery phases
1. **Phase 0 — Repository and docs:** version control, environment setup, specification.
2. **Phase 1 — Local simulator:** profile, services, simulated menu, leads, pending appointment requests, handoff, SQLite, tests.
3. **Phase 2 — Authentication and hosted database:** Supabase/PostgreSQL, tenant-scoped access, deployment.
4. **Phase 3 — WhatsApp integration:** official Meta onboarding, webhook verification, message handling, templates, opt-outs.
5. **Phase 4 — Calendar:** choose Google Calendar or Outlook, authorization, availability checks, conflict handling.
6. **Phase 5 — Payments and reminders:** Stripe payment links/webhooks, consent-aware reminders, monitoring.
7. **Phase 6 — Pilot and hardening:** security review, backups, support processes, limited pilot, measured rollout.

## 13. Acceptance criteria for the first milestone
- Owner can create and update a business profile.
- Owner can manage a service catalogue.
- Customer simulator supports menu navigation, service listing, appointment request, and human handoff.
- Appointment requests remain pending until staff takes an explicit action.
- Data persists in SQLite.
- The app can be started from the README instructions on Windows.
- Automated tests cover core flows and tenant separation logic.
- No live WhatsApp, calendar, or payment integrations are invoked.
