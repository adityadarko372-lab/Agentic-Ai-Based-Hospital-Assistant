# Nova Health: Implementation Status (v0.2)

**Date:** 28 October 2026 · **Scope source:** `partial implementation.md` (required), `docs/first report.md` Phase 5 (optional)

This page lists clearly what is **implemented**, what is **simulated**, and what is **future work**. Nothing here is clinically validated or approved for real patient use.

## Required deliverables (`partial implementation.md`, section 6)

| # | Deliverable | Status | Where |
|---|---|---|---|
| 1 | Working web app with a professional hospital-assistance interface | **Implemented** | `frontend/`; neumorphic design system, desktop and phone layouts, automated accessibility check |
| 2 | Functional chatbot for basic hospital queries | **Implemented** | AI Assistant page; Patient Assistance Agent |
| 3 | Supervisory agent routing to three specialised agents | **Implemented** | `backend/app/agents/supervisor.py` + 3 agents (a fourth, optional agent in Phase 5) |
| 4 | Symptom-guidance module with safe, predefined responses | **Implemented** | Symptom Guidance page; `care_engine.py`, `care_rules.json` |
| 5 | Appointment-request system connected to SQLite | **Implemented** | Appointments page; `appointment_service.py` |
| 6 | Activity or status panel showing processing and outcomes | **Implemented** | Agent activity panel and Agent Activity page |
| 7 | Screenshots and test cases | **Implemented** | `docs/screenshots/`; 262 pytest, 72 Vitest, and Playwright runs with optional features off and on (see the Phase 5 report) |

## Demonstration sequence (section 5)

All six steps work, with every optional feature off and with every optional feature on. They are automated in `frontend/e2e/demo.spec.ts`.

## Feature details

| Feature | Status | Notes |
|---|---|---|
| Patient dashboard with live requests, activity and departments | Implemented | Shows which optional features are really running |
| Demo login (bcrypt, signed 8-hour tokens, per-request access checks) | Implemented (demo-grade) | 6 patients + 1 staff account; no rate limiting, lockout, revocation or password reset |
| Appointment form, validation, confirmation, cancel, duplicate protection | Implemented | |
| Appointment confirmation by the hospital | **Implemented (optional, Phase 5)** | Front-desk staff confirm or decline once, with a note; off by default |
| Safety Gate: emergency warning signs, rule-override refusal | Implemented | Runs before every classifier and agent |
| Intent routing | Implemented: **transparent rules** by default | Optional fine-tuned DistilBERT + rules hybrid (Phase 5) |
| Multi-turn booking, status and cancel through chat | Implemented | |
| Care navigation (chat and form, same engine) | Implemented: **fixed rules, not clinically reviewed** | Never names a condition or medicine for the patient |
| General health information (NIH MedQuAD) | **Implemented (optional, Phase 5)** | Cited, labelled "General information", shown only above a similarity threshold |
| AI rewording of replies (local Ollama) | **Implemented (optional, Phase 5)** | Only non-clinical replies; guard on numbers and medical words; template fallback |
| Voice input | **Implemented (optional, Phase 5)** | Browser Web Speech API (en-IN); not tested with a real microphone |
| Agent trace stored and displayed | Implemented | `agent_runs`, `agent_steps` |
| Persistence across restarts | Implemented, verified | Existing databases are upgraded in place |
| Accessibility (axe WCAG 2.1 A/AA) | No serious or critical issues found by automated checks | Includes the staff page; not a full manual audit |

## Simulated

| Item | How it is simulated |
|---|---|
| The hospital | "Nova Health Multi-Speciality Hospital, Pune" is fictional; its departments, locations, hours and extensions are invented (`hospital_info.json`) |
| People | 7 fictional demo accounts; no real personal data |
| Scheduling | No hospital system is connected. "Confirmed" by the demo front desk does not book a real slot |
| Reply wording | Fixed templates by default; optional local-model rewording of non-clinical replies |

## Measured results of the optional AI parts (details in `docs/phase-reports/phase-5-optional-enhancements.md`)

| Part | Result on hand-written test data |
|---|---|
| MedQuAD search | Recall@1 0.92, Recall@3 0.98 on 50 questions; 0 of 20 off-topic questions answered at the 0.55 threshold |
| Trained intent hybrid | Routed correctly 85/108 (set A) and 44/60 (set B), vs 40 and 21 for the rules; routed wrongly 9 and 4, vs 4 and 3 |
| Ollama rewording | 8 of 10 replies reworded; 2 rejected by the guard; median 0.61 s per message |

These are small, team-written evaluation sets. They are not accuracy claims for real patients.

## Future work (documented, not built)

- MiniLM fine-tuning for MedQuAD search (base model already ranks the right topic first for 46 of 50 test questions).
- **Long-term vision (`Context.md`):** doctor portals, bed management, EHR and scheduling integration, discharge and follow-up, notifications, multilingual support, production authentication, clinical review of rules, deployment.

## Not to be claimed

The prototype is **not** clinically validated, regulator-approved, production-secure or connected to any real hospital system.
