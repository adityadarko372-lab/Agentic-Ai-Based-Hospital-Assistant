# Nova Health: Agentic AI Hospital Assistant (Partial Implementation)

Nova Health (earlier called "Hospivanta" in the project documents) is a final-year project prototype. A **Supervisory Agent** coordinates specialist agents (Patient Assistance, Appointment and Care Navigation) to help patients find their way around hospital services.

> **Demonstration prototype.** The hospital, departments and people shown are fictional, and all data is synthetic. The app does not diagnose, it is not clinically validated, and it must not be used for real medical decisions. In an emergency in India, call **112** or **108**.

## Current status

| Phase | Scope | Status |
|---|---|---|
| 1 | Foundation, design system, app shell, `/api/health` | ✅ Done |
| 2 | Demo login, SQLite, dashboard, appointment requests | ✅ Done |
| 3 | Supervisory Agent, 3 specialist agents, chat, activity panel | ✅ Done |
| 4 | Symptom guidance, end-to-end demo, `v0.1-required-scope` | ✅ Done (tag `v0.1-required-scope`) |
| 5 | Optional enhancements (front desk, MedQuAD, trained classifier, Ollama) | Optional |

All five required modules and the 6-step demonstration sequence from `partial implementation.md` are working.

| Document | Purpose |
|---|---|
| [`docs/setup.md`](docs/setup.md) | Install, run, reset, test, troubleshoot |
| [`docs/demo-script.md`](docs/demo-script.md) | What to click and say in the examination |
| [`docs/implementation-status.md`](docs/implementation-status.md) | Implemented / simulated / future work |
| [`docs/first report.md`](docs/first%20report.md) | The approved plan |
| [`docs/phase-reports/`](docs/phase-reports/) | One report per phase, with real test results |

## Demo account

| Email | Password | Who |
|---|---|---|
| `patient@novahealth.demo` | `NovaDemo@2026` | Asha Verma (fictional demo patient) |

Two more fictional patients (`rohan.mehta@novahealth.demo`, `kavya.iyer@novahealth.demo`) use the same password. They are used to test that patients cannot see each other's data. The login page has a **Fill in** button for the main demo account.

## Tech stack

- **Frontend:** React 19, Vite 8, TypeScript 7, React Router 7, Framer Motion, and a hand-built neumorphic CSS design system with locally bundled Inter and Fraunces fonts.
- **Backend:** Python 3.13, FastAPI, SQLModel on SQLite, bcrypt password hashing and signed (JWT) session tokens.
- **Agents:** plain Python modules (no agent framework, no AI API, no model download). Intent routing uses an explainable rule classifier behind a swappable `IntentClassifier` interface.
- **Tests:** pytest for the backend, Vitest with Testing Library for the frontend, Playwright browser tests (using the Edge browser already installed on Windows).

## Prerequisites

- Windows 10/11 with PowerShell
- Python 3.13 (`py -3.13 --version`)
- Node.js 20 or newer, with npm (`node --version`)
- Git

## Setup (once)

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\setup.ps1"
```

## Run

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\start.ps1"
```

This creates `.env` with a random session secret if it is missing, then opens two server windows and your browser:

- Frontend: http://127.0.0.1:5173
- Backend API: http://127.0.0.1:8000 (interactive docs at http://127.0.0.1:8000/docs)

To stop the app, close the two server windows.

**Reset demo data:** stop the backend, then run `.\scripts\reset-demo-data.ps1`. The database (`backend/data/nova_health.db`) is recreated with the demo patients and departments on the next start, with no appointment requests.

## API (Phase 2)

| Method | Path | Sign-in | Purpose |
|---|---|---|---|
| GET | `/api/health` | No | Status, version, optional feature switches |
| POST | `/api/auth/login` | No | Demo login, returns a session token |
| GET | `/api/auth/me` | Yes | Signed-in user's profile |
| GET | `/api/hospital/departments` | No | Fictional hospital directory |
| GET | `/api/hospital/info` | No | Hours, help desk, what to bring, emergency numbers |
| POST | `/api/appointments` | Yes | Submit a request (saved as **Pending**; `Idempotency-Key` header prevents duplicates) |
| GET | `/api/appointments/mine` | Yes | The signed-in patient's own requests |
| POST | `/api/appointments/{reference}/cancel` | Yes | Withdraw your own pending request |
| GET | `/api/activity/mine` | Yes | Your activity history |
| POST | `/api/assistant/message` | Yes | Send a chat message; the Supervisory Agent routes it and returns the reply and the full trace |
| GET | `/api/assistant/conversations/{id}` | Yes | Messages of one of your conversations |
| GET | `/api/activity/runs` | Yes | Agent runs: which agent handled each request, with every step |
| GET | `/api/activity/runs/{id}` | Yes | One run with its steps |
| GET | `/api/care-navigation/options` | No | Symptom form choices (warning signs, symptoms, durations…) |
| POST | `/api/care-navigation/assess` | Yes | Symptom Guidance form, evaluated by the Care Navigation Agent (same engine as the chat) |

## How the agents work (Phase 3)

```
message → Safety Gate (warning signs → emergency; rule-override → refused)
        → conversation context (continue an unfinished booking / follow-up)
        → IntentClassifier (transparent rules: intent + confidence + matched evidence)
        → Supervisory Agent routes to ONE specialist:
             Patient Assistance Agent  hospital_info.json (fictional directory)
             Appointment Agent         appointment_service (same rules as the form; always Pending)
             Care Navigation Agent     care_rules.json (fixed rules, not clinically reviewed, never diagnoses)
        → every step saved in agent_runs / agent_steps and shown in the Agent Activity panel
```

## Test

```powershell
# Backend
cd backend
.\.venv\Scripts\python.exe -m pytest -v

# Frontend
cd frontend
npm.cmd run typecheck
npm.cmd test

# Browser tests (start the app first with scripts\start.ps1)
npm.cmd run test:e2e
```

Browser tests create and then cancel a real appointment request in whichever database the running backend uses. Run `scripts\reset-demo-data.ps1` afterwards for a clean demo.

## Project structure

```
backend/    FastAPI app: app/api (routes), app/services (business rules), app/db (models, seed),
            app/knowledge (fictional hospital_info.json), app/core (config, security, errors), tests/
frontend/   React app: src/pages, src/components, src/auth, src/services, src/design-system, tests/, e2e/
scripts/    setup.ps1, start.ps1, ensure-env.ps1, reset-demo-data.ps1
docs/       plan, phase reports, screenshots
```

## Security notes

- The backend binds to `127.0.0.1` only, and CORS allows only the local Vite origin.
- **Demo login, not production authentication.** Passwords are bcrypt-hashed and sessions are signed tokens that expire after 8 hours, and every protected endpoint re-checks the token. There is no rate limiting, account lockout, token revocation or password reset. The demo password is public on purpose.
- The session token is kept in the browser's `sessionStorage` (cleared when the tab closes). This is acceptable for a local demo but exposed to any script injected into the page; a production build would use secure HTTP-only cookies.
- `.env`, databases, virtual environments, model files and raw datasets are gitignored.

## Credits and licences

- Fonts: Inter and Fraunces (SIL Open Font License), bundled via Fontsource.
- MedQuAD (CC BY 4.0) may be used in optional Phase 5 work. Attribution will be added if it is used.
