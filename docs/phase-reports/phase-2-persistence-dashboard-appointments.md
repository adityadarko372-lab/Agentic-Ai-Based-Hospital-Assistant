# Phase 2 Report: Persistence, Dashboard and Appointment Management

**Date:** 27 October 2026
**Plan reference:** [`docs/first report.md`](../first%20report.md), Phase 2 (Tasks 3, 4 and 5)
**Status:** Complete. Every acceptance criterion was checked and passed (details in section 7).

---

## 1. What this phase was meant to do

| Task | Goal |
|---|---|
| 3 | SQLite database, fictional demo data, minimal demo login |
| 4 | **Module 5 – Appointment Management:** form → saved in SQLite → shown as **Pending** |
| 5 | **Module 1 – Patient Dashboard:** every element the spec lists, connected to real data |

Phase 2 acceptance criteria (from the plan):
1. A demo patient can log in.
2. A submitted request shows as Pending with a reference like `NH-APT-0001` and survives a backend restart.
3. Invalid input is rejected with clear messages, a double submission does not create a duplicate, and one patient cannot read another's requests.
4. The dashboard shows the logo/navigation, welcome message, assistant button, services, symptom-guidance option, booking option and recent activity, all connected to real data.
5. Tests pass, this report is written, and the work is pushed.

---

## 2. What was actually built

### Backend
- **Database (SQLite through SQLModel):** four tables in `backend/data/nova_health.db`.

  | Table | Holds |
  |---|---|
  | `users` | Demo patients (bcrypt-hashed passwords, never plain text) |
  | `departments` | The fictional hospital directory, loaded from `hospital_info.json` |
  | `appointment_requests` | Every request, its status, a human-readable reference and an idempotency key |
  | `activity_events` | A readable history: what happened, who did it, which reference |

- **Demo data, loaded at start-up:** 11 fictional departments (8 clinical, plus Laboratory, Pharmacy and Emergency, which do not take appointments) and 3 fictional patients. Departments are refreshed from the JSON file on every start. Patients are only created if missing, so requests are never wiped by a restart.
- **Hospital knowledge file:** `backend/app/knowledge/hospital_info.json` holds the departments, OPD hours, help desk, visiting hours, "what to bring", how booking works and the Indian emergency numbers (112 / 108). It starts with a `_notice` saying it is fictional. The Phase 3 Patient Assistance Agent will answer questions from this same file.
- **Demo login:** `POST /api/auth/login` returns a signed session token (JWT, HMAC-SHA256, 8-hour expiry). `GET /api/auth/me` returns the profile. Unknown email and wrong password get the **same** message, so the form cannot be used to discover which accounts exist.
- **Access control:** every protected endpoint uses the `get_current_patient` dependency, so the backend checks the token on every request. Another patient's request is reported as "not found", so its existence is not revealed.
- **Appointment service** (`app/services/appointment_service.py`): the single place where requests are created. The Phase 3 Appointment Agent will call this same function, so the chat and the form follow identical rules.
  - Validation: name 2–80 characters, letters only (Indian scripts accepted); department must exist **and** accept appointments; date from **tomorrow** to **90 days ahead** (India time); reason 10–500 characters; extra spaces tidied.
  - **Always saved as `pending`.** Nothing in Phase 2 can set "confirmed".
  - **Duplicate protection:** the browser sends an `Idempotency-Key` header. Sending the same key again returns the original request (HTTP 200) instead of creating a new one. Reusing a key with different details is refused (HTTP 409). A database unique constraint backs this up even if two requests arrive at the same instant.
  - Reference generated from the row id: `NH-APT-0001`, `NH-APT-0002`, …
  - **Cancel:** a patient can withdraw their own pending request (status `cancelled`). A second cancel is refused (409).
  - Each submit and cancel writes an activity event. The free-text reason is **not** copied into the history, so medical details stay in one place.
- **Friendly errors:** every validation failure returns `{"detail": "...", "field_errors": {"preferred_date": "Please choose a date from tomorrow onwards."}}`, so the UI can show each message under its field.
- **Session secret:** `scripts/ensure-env.ps1` (called by `setup.ps1` and `start.ps1`) writes a random 48-byte `SESSION_SECRET` into `.env` once, so users stay signed in across restarts. If the secret is missing, the server makes a temporary one and logs a warning.

### Frontend
- **Login page:** split layout with the brand message, a sign-in card, a **Fill in** button for the demo account, a demo-data notice and the emergency notice. Fields are checked before anything is sent.
- **Session handling:** the token is kept in `sessionStorage` (survives refresh, cleared when the tab closes). On load the app re-checks it with `/api/auth/me`. Any 401 signs the user out and shows "Your session ended". All pages except `/login` require sign-in, and after signing in you return to the page you asked for.
- **Top bar:** the user's initials, name, "Demo patient" label and a Sign out button.
- **Appointments page (Module 5):**
  - Form with patient name (prefilled from the profile), department (only departments that take appointments; location and hours shown as a hint), preferred date (date picker limited to the allowed range) and reason (with a character counter and an emergency reminder).
  - Instant validation using the same rules as the backend. Focus moves to the first invalid field.
  - **Confirmation dialog** summarising the request and stating it will be **Pending, not a confirmed appointment**.
  - A green success callout with the real reference, plus a toast.
  - **My requests** list (newest first) with reference, status badge, preferred date, reason and a plain-language status note: "Not yet confirmed by the hospital."
  - Cancel with its own confirmation dialog.
  - Deep link: `/appointments?department=cardiology` preselects the department. The Services page uses it now, and Phase 4 symptom guidance will too.
- **Dashboard (Module 1):** personal greeting ("Good morning, Asha"), Ask the assistant button, quick-access cards, **Upcoming requests** (pending, future dates only, soonest first), **Recent activity** from the database, hospital services from the API, and the System status card. Every card has loading skeletons, a friendly empty state, and an error message with "Try again".
- **Hospital Services page:** now loaded from the backend. Hospital details and "what to bring", clinical departments, and walk-in/emergency services, each showing location, hours, extension, whether an appointment is needed, and a "Request appointment" link.

---

## 3. How it works (data flow)

```
Appointment form ──(validate locally)──► Confirmation dialog
        │ POST /api/appointments  + Authorization: Bearer <token>
        │                         + Idempotency-Key: <uuid per draft>
        ▼
FastAPI  get_current_patient  (checks the token on every request)
        ▼
AppointmentCreate (Pydantic: name, reason, lengths)          → 422 + field_errors
        ▼
appointment_service.submit_request
   ├─ same key already used?  → return the original (200) / conflict (409)
   ├─ business rules (department exists & bookable, date window)  → 422
   ├─ INSERT appointment_requests (status = pending)
   ├─ reference = NH-APT-<id>
   ├─ INSERT activity_events ("submitted … pending hospital review")
   └─ COMMIT  (one transaction: both rows or neither)
        ▼
201 { reference, status: "pending", … }  → callout + toast + list refresh
```

---

## 4. Important files

| File | Purpose |
|---|---|
| `backend/app/db/models.py` | The four tables and the status values |
| `backend/app/db/session.py` | SQLite engine (foreign keys on), per-request sessions |
| `backend/app/db/seed.py` | Demo departments and patients (`DEMO_PASSWORD`) |
| `backend/app/knowledge/hospital_info.json` | Fictional hospital directory and guidance |
| `backend/app/core/security.py` | bcrypt hashing, token creation and checking |
| `backend/app/core/errors.py` | Friendly `field_errors` responses |
| `backend/app/core/clock.py` | UTC timestamps and "today in India" |
| `backend/app/schemas.py` | Request/response shapes and input validation |
| `backend/app/services/appointment_service.py` | Appointment rules (shared with the Phase 3 agent) |
| `backend/app/services/activity_service.py` | Recording and listing activity |
| `backend/app/api/{auth,hospital,appointments,activity,deps}.py` | HTTP endpoints and access control |
| `backend/tests/test_{auth,hospital,appointments}.py` | 45 new backend tests |
| `frontend/src/auth/AuthContext.tsx`, `RequireAuth.tsx` | Session handling and protected routes |
| `frontend/src/services/apiClient.ts`, `novaApi.ts`, `types.ts` | Typed API calls, token header, field errors |
| `frontend/src/pages/LoginPage.tsx` | Sign-in |
| `frontend/src/pages/AppointmentsPage.tsx` + `components/appointments/*` | Module 5 |
| `frontend/src/pages/DashboardPage.tsx`, `components/ActivityFeed.tsx` | Module 1 |
| `frontend/src/pages/ServicesPage.tsx` | Directory from the API |
| `frontend/tests/{auth,appointments,dashboard}.test.tsx` | 26 new Vitest tests, with an in-memory fake API |
| `frontend/e2e/appointments.spec.ts`, `shell.spec.ts`, `helpers.ts` | Real-browser tests |
| `scripts/ensure-env.ps1`, `reset-demo-data.ps1` | Session secret; clean demo database |
| `docs/screenshots/phase2-*.png` | Screenshots captured by the browser tests |

Removed: `frontend/src/data/demoDepartments.ts` (departments now come from the backend).

---

## 5. Commands

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\start.ps1"        # start (creates .env secret if missing)
powershell -ExecutionPolicy Bypass -File ".\scripts\reset-demo-data.ps1" # clean demo data (backend stopped)

cd backend;  .\.venv\Scripts\python.exe -m pytest -v
cd frontend; npm.cmd run typecheck; npm.cmd test; npm.cmd run build
cd frontend; npm.cmd run test:e2e   # app must be running
```

Demo login: `patient@novahealth.demo` / `NovaDemo@2026`.

---

## 6. Decisions and changes from the plan

| Item | Decision | Why |
|---|---|---|
| `agent_runs` / `agent_steps` tables | Moved to **Phase 3** | The plan listed them in Task 3, but nothing writes to them until the Supervisory Agent exists. Creating empty tables now would be dead code. |
| Cancellation | **Built** (the plan allowed deferring it) | Small, and the Phase 3 Appointment Agent needs it for "cancel my request". |
| Earliest date | **Tomorrow**, not today | Same-day booking cannot be honoured without a real scheduling system. Urgent needs are pointed to emergency care. |
| Dates | "Today" uses **India time (UTC+05:30)** in both backend and frontend | Consistent rules whatever the laptop's time zone. A fixed offset is exact because India has no daylight saving. |
| Timestamps | Stored as timezone-aware UTC | SQLModel 0.0.48 refuses naive datetimes (found by the first test run, see section 7). |
| Token storage | `sessionStorage` + `Authorization` header | Simple and testable for a local demo. The trade-off is documented in the README. |
| Name rule | Letters **and combining marks**, joined by space . ' - | The first rule wrongly rejected Hindi names such as "आशा वर्मा" (vowel signs are marks, not letters). Backend and frontend now use the same rule. |
| Department info | Extensions such as "Ext. 2101" instead of phone numbers | Avoids inventing numbers that could belong to a real person or business. |
| Browser tests | Ran against a **separate** `e2e.db` (deleted afterwards) | Keeps your real demo database clean. |

New pinned dependencies: `sqlmodel 0.0.48`, `SQLAlchemy 2.1.6`, `bcrypt 5.0.0`, `PyJWT 2.15.1`. No new frontend dependencies.

---

## 7. Tests actually run and their real results

All run on this laptop on 27 October 2026.

| Check | Result |
|---|---|
| Backend tests (`pytest`) | **50 passed** (5 from Phase 1 + 45 new), 1 harmless warning from a library |
| Frontend typecheck (`tsc --noEmit`) | **0 errors** |
| Frontend tests (`vitest run`) | **42 passed** in 5 files (16 from Phase 1, updated for login, + 26 new) |
| Production build (`vite build`) | **Succeeded** (JS 449 kB, 142 kB gzipped) |
| Browser tests (Playwright, Edge, desktop 1440 px + phone 390 px) | **14 passed** (7 tests × 2 screen sizes) |
| Real backend restart | Created `NH-APT-0003` (pending) through the API, stopped the server process (pid 355028), started a new one (pid 368128), signed in again: **`found=True status=pending department=Orthopaedics`** |

**What the backend tests cover:** login success; email case and spaces ignored; the same message for a wrong password and an unknown email; friendly empty-field errors; an over-long password refused safely; `/me`; 401 on every protected endpoint without a token; expired, forged, unsigned and garbage tokens rejected; departments seeded and seeding twice creates no duplicates; Emergency and Laboratory not bookable; demo notice and 112/108 present; a request saved as pending with an `NH-APT-####` reference and no "confirmed" wording; newest-first order; survival across an app restart on the same database file; the same idempotency key creating no duplicate; a reused key with different details returning 409; ten invalid inputs each giving the right field message with nothing saved; missing fields; the 90th day accepted; Hindi, Tamil and punctuated names accepted; digits and symbols rejected; whitespace tidied; patients unable to see or cancel each other's requests; the same key from two patients creating two requests; cancel once (200) and again (409); activity events recorded without the private reason; activity private per patient; a malformed idempotency key rejected.

**What the frontend tests cover:** the form rules (11 cases, matching the backend); redirect to sign-in; client-side login checks; the wrong-password message; sign-in returns to the requested page; sign-out; a session restored after refresh; incomplete form blocked; only bookable departments listed; the full submit flow (prefilled name, deep-linked department, confirmation dialog, Pending callout, list entry, idempotency header sent); server field errors shown under the field; honest status badges and a cancel button only on pending requests; every dashboard element present; empty states; upcoming requests excluding cancelled ones; activity feed content.

**What the browser tests cover (real FastAPI + SQLite + Edge):** sign-in required; wrong password refused; dashboard greeting, live backend status and departments from the API; no horizontal scrolling on 4 pages; every module reachable from the sidebar (desktop) and the drawer (phone); the services directory; **the full Module 5 journey**: blocked empty submit → fill → confirmation → `NH-APT-####` Pending → still listed after a page reload → shown on the dashboard and in recent activity → cancelled.

**Problems found and fixed during this phase:**
1. SQLModel 0.0.48 rejects naive datetimes (all 36 database tests failed on the first run). Switched to timezone-aware UTC timestamps.
2. The name rule rejected names in Indian scripts. Rewritten to accept combining marks, identically in backend and frontend, with new tests.
3. Two Vitest queries were ambiguous (a department label matched two elements; the symptom-guidance link appeared in both the sidebar and the dashboard). Tests made more precise; no app change needed.
4. During the restart check, an earlier backend process was still holding port 8000, so the first "restart" did not really restart. I stopped that process by its port and repeated the check with a new process id, which is the result recorded above.

---

## 8. Implemented, simulated and future work

| Feature | Status |
|---|---|
| SQLite persistence, demo seeding, reset script | **Implemented** |
| Demo login, signed tokens, per-request access checks | **Implemented** (demo-grade, see limitations) |
| Module 5: form, validation, confirmation, Pending status, list, cancel, duplicate protection | **Implemented** |
| Module 1: dashboard with real requests, activity and departments | **Implemented** |
| Hospital directory and guidance | **Simulated content:** fictional hospital, served from a real file and database |
| Appointment confirmation by the hospital | **Not implemented.** No scheduling system is connected, so requests stay Pending. Optional staff review is Phase 5 (Task 11). |
| Supervisory Agent, specialist agents, chat, agent activity trace | **Future: Phase 3** |
| Symptom guidance | **Future: Phase 4** |

---

## 9. Known limitations

- **Demo-grade security:** no rate limiting, account lockout, token revocation or password reset, and the demo password is public by design. Tokens in `sessionStorage` could be read by an injected script; production would use HTTP-only cookies.
- **Sign-out is client-side only:** a copied token stays valid until it expires (8 hours).
- **Request references** come from the database row id. Deleting the database restarts numbering at `NH-APT-0001`.
- **No time-of-day rules** (for example Sunday closures) are applied to preferred dates. The fictional OPD hours are only shown as information.
- **The pytest warning** about `httpx` in the Starlette test client is harmless for now.
- **Browser tests write to the running backend's database.** They cancel what they create, and `reset-demo-data.ps1` gives a clean start before a demo.

---

## 10. Current state and next steps

Modules 1 and 5 are working end to end with real persistence, and steps 1 and 4 of the spec's demonstration sequence can already be shown.

**Next: Phase 3 (Supervisory Agent, specialist agents, assistant chat and activity panel)**
1. `agent_runs` / `agent_steps` tables, `IntentClassifier` interface with the transparent rule classifier, and the Safety Gate (emergency phrases, prompt injection, scope).
2. Supervisory Agent routing to the **Patient Assistance Agent** (answers from `hospital_info.json`), the **Appointment Agent** (multi-turn, calls `appointment_service.submit_request` with `source="assistant"`) and the **Care Navigation Agent** (cautious rules, 112/108 for warning signs).
3. Chat page with suggestion chips and inline cards, plus the live Agent Activity timeline and history page.
