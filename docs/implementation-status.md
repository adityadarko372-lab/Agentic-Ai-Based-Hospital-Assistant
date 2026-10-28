# Nova Health: Implementation Status (v0.1-required-scope)

**Date:** 28 October 2026 · **Scope source:** `partial implementation.md`

This page lists clearly what is **implemented**, what is **simulated**, and what is **future work**. Nothing here is clinically validated or approved for real patient use.

## Required deliverables (`partial implementation.md`, section 6)

| # | Deliverable | Status | Where |
|---|---|---|---|
| 1 | Working web app with a professional hospital-assistance interface | **Implemented** | `frontend/`; neumorphic design system, desktop and phone layouts, automated accessibility check |
| 2 | Functional chatbot for basic hospital queries | **Implemented** | AI Assistant page; Patient Assistance Agent |
| 3 | Supervisory agent routing to three specialised agents | **Implemented** | `backend/app/agents/supervisor.py` + 3 agents |
| 4 | Symptom-guidance module with safe, predefined responses | **Implemented** | Symptom Guidance page; `care_engine.py`, `care_rules.json` |
| 5 | Appointment-request system connected to SQLite | **Implemented** | Appointments page; `appointment_service.py` |
| 6 | Activity or status panel showing processing and outcomes | **Implemented** | Agent activity panel and Agent Activity page |
| 7 | Screenshots and test cases | **Implemented** | `docs/screenshots/`; 209 pytest, 57 Vitest and 28 Playwright tests (14 scenarios × desktop and phone) |

## Demonstration sequence (section 5)

| Step | Status | Automated by |
|---|---|---|
| 1 Dashboard | Works | `e2e/demo.spec.ts` |
| 2 Hospital question | Works | `e2e/demo.spec.ts`, `assistant.spec.ts` |
| 3 Routed to Appointment Agent | Works | same |
| 4 Saved as Pending | Works | same, plus `appointments.spec.ts` |
| 5 Symptom guidance | Works (self-care and emergency cases) | `e2e/demo.spec.ts` |
| 6 Which agent handled each request | Works | `e2e/demo.spec.ts` |

## Feature details

| Feature | Status | Notes |
|---|---|---|
| Patient dashboard with live requests, activity and departments | Implemented | |
| Demo login (bcrypt, signed 8-hour tokens, per-request access checks) | Implemented (demo-grade) | No rate limiting, lockout, revocation or password reset |
| Appointment form, validation, confirmation, cancel, duplicate protection | Implemented | |
| Appointment **confirmation by the hospital** | **Not implemented** | Requests stay Pending; optional front-desk review is Phase 5 |
| Safety Gate: emergency warning signs, rule-override refusal | Implemented | 12 warning-sign groups; fixed phrase lists |
| Intent routing | Implemented: **transparent rules** | Trained classifier: optional Phase 5 (interface and fallback exist) |
| Multi-turn booking, status and cancel through chat | Implemented | |
| Care navigation (chat and form, same engine) | Implemented: **fixed rules, not clinically reviewed** | Never names a condition or medicine |
| Agent trace stored and displayed | Implemented | `agent_runs`, `agent_steps` |
| Persistence across restarts | Implemented, verified | Phase 2 restart check |
| Accessibility (axe WCAG 2.1 A/AA) | No serious or critical issues found by automated checks | Not a full manual audit |

## Simulated

| Item | How it is simulated |
|---|---|
| The hospital | "Nova Health Multi-Speciality Hospital, Pune" is fictional; its departments, locations, hours and extensions are invented (`hospital_info.json`) |
| Patients | 3 fictional demo accounts; no real personal data |
| Scheduling | No hospital system is connected; requests are only stored as Pending |
| Reply wording | Fixed templates (no language model) |

## Future work (documented, not built)

- **Optional Phase 5:** front-desk review page (staff approve or decline), MedQuAD general health information with NIH citation, trained DistilBERT intent classifier (GPU), Ollama phrasing, voice input.
- **Long-term vision (`Context.md`):** staff and doctor portals, bed management, EHR and scheduling integration, discharge and follow-up, notifications, multilingual support, production authentication, clinical review of rules, deployment.

## Not to be claimed

The prototype is **not** clinically validated, regulator-approved, production-secure or connected to any real hospital system.
