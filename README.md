# Nova Health: Agentic AI Hospital Assistant (Partial Implementation)

Nova Health (earlier called "Hospivanta" in the project documents) is a final-year project prototype. A **Supervisory Agent** coordinates specialist agents (Patient Assistance, Appointment and Care Navigation) to help patients find their way around hospital services.

> **Demonstration prototype.** The hospital, departments and people shown are fictional, and all data is synthetic. The app does not diagnose, it is not clinically validated, and it must not be used for real medical decisions. In an emergency in India, call **112** or **108**.

## Current status

| Phase | Scope | Status |
|---|---|---|
| 1 | Foundation, design system, app shell, `/api/health` | ✅ Done |
| 2 | Login, SQLite, dashboard, appointment requests | Planned |
| 3 | Supervisory Agent, 3 specialist agents, chat, activity panel | Planned |
| 4 | Symptom guidance, end-to-end demo, `v0.1-required-scope` | Planned |
| 5 | Optional enhancements (front desk, MedQuAD, trained classifier, Ollama) | Optional |

The full approved plan is in [`docs/first report.md`](docs/first%20report.md). Phase reports are in [`docs/phase-reports/`](docs/phase-reports/).

## Tech stack

- **Frontend:** React 19, Vite 8, TypeScript 7, React Router 7, Framer Motion, and a hand-built neumorphic CSS design system with locally bundled Inter and Fraunces fonts.
- **Backend:** Python 3.13, FastAPI, Pydantic Settings. SQLite and SQLModel are added in Phase 2.
- **Tests:** pytest for the backend, Vitest with Testing Library for the frontend. Playwright is added in Phase 3.

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

This opens two server windows and your browser:

- Frontend: http://127.0.0.1:5173
- Backend API: http://127.0.0.1:8000 (interactive docs at http://127.0.0.1:8000/docs)

To stop the app, close the two server windows.

## Test

```powershell
# Backend
cd backend
.\.venv\Scripts\python.exe -m pytest -v

# Frontend
cd frontend
npm.cmd run typecheck
npm.cmd test
```

## Project structure

```
backend/    FastAPI app (app/api, app/core), tests/
frontend/   React app (src/components, src/design-system, src/pages, src/services, src/hooks), tests/
scripts/    setup.ps1, start.ps1
docs/       plan, phase reports
```

## Security notes

- The backend binds to `127.0.0.1` only, and CORS allows only the local Vite origin.
- There is no login yet (it arrives in Phase 2). The planned demo login is not production-grade authentication.
- `.env`, databases, virtual environments, model files and raw datasets are gitignored.

## Credits and licences

- Fonts: Inter and Fraunces (SIL Open Font License), bundled via Fontsource.
- MedQuAD (CC BY 4.0) may be used in optional Phase 5 work. Attribution will be added if it is used.
