# Phase 1 Report: Foundation and Visual Shell

**Date:** 26 October 2026
**Plan reference:** [`docs/first report.md`](../first%20report.md), Phase 1 (Tasks 1 and 2)
**Status:** Complete. All acceptance criteria were verified, except the GitHub push, whose outcome is recorded in the Git section below.

---

## 1. What this phase was meant to do

Phase 1 builds the foundation that every later phase sits on:

1. **Task 1:** check the tools, save the approved plan, create the project skeleton, add a working `GET /api/health` endpoint, connect the frontend to it, write startup scripts, and set up Git.
2. **Task 2:** build the Nova Health design system (refined neumorphism) and the application shell: logo, navigation, mobile menu, floating assistant button and accessible reusable components.

No agents, no database and no login were planned for this phase. Those arrive in Phases 2 and 3.

---

## 2. What was actually built

### Backend (FastAPI)
- `GET /api/health` returns the service name, version, environment, a `demo_data: true` flag and the state of every optional feature switch.
- Settings come from environment variables or a `.env` file through Pydantic Settings. All optional AI features are **off by default**.
- CORS allows only the local Vite address (`127.0.0.1:5173` and `localhost:5173`), and the server binds to `127.0.0.1` only.

### Frontend (React + Vite + TypeScript)
- **App shell:**
  - a sticky sidebar on desktop
  - a top bar with a live "Backend connected / offline" indicator
  - a slide-in drawer menu on phones and tablets (below 1024 px)
  - a floating **Ask Nova** button
  - a "Skip to main content" link
  - smooth fade-in page transitions
- **Dashboard:** a time-of-day greeting, the demo-data notice, an emergency notice (112 / 108), four quick-access cards, a Recent activity card (an honest empty state for now), a live System status card and a hospital services preview.
- **Hospital Services page:** six fictional departments. This list is temporary and moves to the backend in Phase 2.
- **Module pages** (AI Assistant, Symptom Guidance, Appointments, Agent Activity): honest preview pages that say **"Not built yet"** and name the phase that delivers each one. They contain no fake buttons or forms.
- **Design System page:** shows every component and its states, for review.
- **Not-found page** for unknown links.

### Design system
- **Tokens:** a porcelain surface colour, a deep teal brand colour, status colours, a spacing scale, corner radii, motion timings and a two-light neumorphic shadow set.
- **Fonts:** Inter (body text) and Fraunces (headings) are bundled locally, so the app works offline.
- **Components:** Card, Button (primary / secondary / ghost / danger, loading, disabled, icon-only), TextInput, SelectInput, TextArea, Badge (Pending / Confirmed / Emergency / Info / Neutral), Toast, Skeleton, EmptyState, Modal, DemoDataBanner, Icon.
- **Accessibility built in:**
  - visible focus rings for keyboard users
  - labels linked to their fields
  - error messages announced together with the field (`aria-describedby` and `role="alert"`)
  - badges always show text, not colour alone
  - the dialog traps keyboard focus and closes with Escape
  - touch targets are at least 44 px
  - animations switch off when the computer's "reduce motion" setting is on

---

## 3. How it works (data flow)

```
Browser (http://127.0.0.1:5173)
   │  fetch("/api/health")   ← same origin, no hard-coded ports in the UI
   ▼
Vite dev server ── proxy /api ──► FastAPI (http://127.0.0.1:8000)
                                     └─ app/api/health.py → Settings (app/core/config.py)
```

- `useBackendHealth` checks `/api/health` once at start-up and then every 20 seconds. Each request has a 5-second timeout. The result is shared through `BackendHealthProvider`, so the top bar and the dashboard use a single connection check.
- If the backend is down, the UI says **"Backend offline"** and explains how to start it. It never pretends to be connected.

---

## 4. Important files

| File | Purpose |
|---|---|
| `docs/first report.md` | The approved plan, saved word for word |
| `backend/app/main.py` | Creates the FastAPI app, CORS policy, routers |
| `backend/app/core/config.py` | Settings and feature switches (all optional AI off) |
| `backend/app/api/health.py` | `GET /api/health` |
| `backend/tests/test_health.py`, `conftest.py` | Backend tests (environment pinned so tests are deterministic) |
| `backend/requirements.txt`, `requirements-dev.txt` | Pinned Python dependencies |
| `frontend/src/design-system/*.css` | Tokens, base styles, components, layout, pages |
| `frontend/src/components/ui/*` | Reusable accessible components |
| `frontend/src/components/layout/*` | App shell, sidebar navigation, mobile drawer, logo, status, FAB |
| `frontend/src/pages/*` | Dashboard, Services, Design System, module previews, 404 |
| `frontend/src/services/apiClient.ts` | Typed fetch wrapper with timeout and friendly errors |
| `frontend/src/hooks/useBackendHealth.ts` | Backend connection checks |
| `frontend/tests/*` | Vitest component and app-shell tests |
| `frontend/e2e/shell.spec.ts`, `playwright.config.ts` | Real-browser tests (Edge) on desktop and phone sizes |
| `scripts/setup.ps1`, `scripts/start.ps1` | One-time setup, one-command start (all paths quoted) |
| `.gitignore`, `.env.example`, `README.md` | Repository hygiene and instructions |
| `docs/screenshots/phase1-*.png` | Screenshots captured by the browser tests |

---

## 5. Commands

```powershell
# One-time setup
powershell -ExecutionPolicy Bypass -File ".\scripts\setup.ps1"

# Start both servers and open the browser
powershell -ExecutionPolicy Bypass -File ".\scripts\start.ps1"

# Backend tests
cd backend; .\.venv\Scripts\python.exe -m pytest -v

# Frontend checks
cd frontend; npm.cmd run typecheck; npm.cmd test; npm.cmd run build

# Browser tests (the app must be running first)
cd frontend; npm.cmd run test:e2e
```

---

## 6. Environment found and decisions made

| Item | Found | Decision |
|---|---|---|
| Python | 3.15.2 (default) and 3.13.6 | Used **3.13** for the backend virtual environment, because brand-new Python releases often lack ready-made packages. The plan said 3.11, but 3.13 is newer and well supported. |
| Node.js / npm | v26.12.1 / 11.20.0, installed but **not on this shell's PATH** | No reinstall. The scripts add `C:\Program Files\nodejs` to PATH themselves. |
| Git | 2.56.0, installed but not on PATH, and **no global user identity** | No reinstall. Git config was left unchanged (see section 9). |
| PowerShell | Script execution is restricted, so `npm.ps1` is blocked | The project uses `npm.cmd` and runs scripts with `-ExecutionPolicy Bypass`. |
| GPU | RTX 4060 Laptop, 8 GB, driver 592.82 | Not needed until optional Phase 5 work. |
| Package versions | npm resolved React 19.3, Vite 8.3, TypeScript 7.0, Vitest 5.0, Playwright 1.64 | All pinned to exact versions in `package.json`. |

**Extra beyond the plan:** Playwright browser tests were added in Phase 1, not Phase 3. They prove the real browser reaches the real backend and that the layout works at phone size. They use the Edge browser already installed, so nothing extra was downloaded.

---

## 7. Tests actually run and their real results

All of these were run on this laptop on 26 October 2026.

| Check | Command | Result |
|---|---|---|
| Backend tests | `pytest -v` | **5 passed**, 1 warning |
| Frontend typecheck | `tsc --noEmit` | **0 errors** (after one fix, see below) |
| Frontend unit and component tests | `vitest run` | **16 passed** (2 files) |
| Production build | `vite build` | **Succeeded**, JS 424 kB (135 kB gzipped) |
| Browser tests (Edge) | `playwright test` | **8 passed** (4 tests × desktop 1440 px and phone 390 px) |
| Live connection check | `Invoke-RestMethod` on `:8000/api/health` and `:5173/api/health` | Both returned `status=ok`. The page returned HTTP 200. |

**What the tests cover:**
- **Backend:** the health response is correct, every optional feature is off by default, CORS accepts the Vite address, CORS rejects an unknown address, and unknown routes return 404.
- **Components:** buttons default to `type="button"`, mouse and keyboard activation, a loading button is disabled and announces it is busy, disabled buttons are skipped by the Tab key, field labels and error descriptions are connected, badges carry text, and the dialog moves focus inside, keeps Tab inside, closes with Escape and returns focus to the button that opened it.
- **App shell:** the brand, heading and demo notice render; "Backend connected" shows when the API answers; "Backend offline" shows when it doesn't; every module appears in the navigation; navigation works and marks the current page; the mobile menu opens and closes with Escape; the 404 page works; the skip link is present.
- **Real browser:** the live backend status shows through the proxy, four pages have no horizontal scrolling at desktop or phone width, every module is reachable from the sidebar (desktop) and the drawer (phone), and screenshots are saved.

**Problems found and fixed during this phase:**
1. **TypeScript error:** `Card`'s `title` prop clashed with the built-in HTML `title` attribute. Fixed with `Omit<…, "title">`.
2. **Logo invisible on phones:** the SVG gradient id was shared between logo copies, and the copy in the hidden desktop sidebar took the definition with it. Fixed with a unique id per logo instance (`useId`).
3. **Visual polish:** the "Check again" button text wrapped onto two lines, and the info icon shrank in the demo banner. Fixed with `nowrap` and `flex-shrink: 0`.
4. **Phone top bar:** the full status text crowded the logo. On phones only the green or red dot is shown now, and the text stays available to screen readers.

---

## 8. Implemented, simulated and future work

| Feature | Status |
|---|---|
| `/api/health`, feature switches, CORS, local-only binding | **Implemented** |
| Design system, app shell, responsive navigation, accessibility basics | **Implemented** |
| Live backend status in the UI | **Implemented** |
| Dashboard quick-access cards and System status | **Implemented** |
| Hospital departments list | **Simulated:** 6 fictional departments in a frontend file, moving to the backend in Phase 2 |
| Recent activity | **Empty state only.** Real activity arrives in Phases 2–3 |
| Login, SQLite, appointments | **Future (Phase 2)** |
| Supervisory Agent, specialist agents, chat, activity panel | **Future (Phase 3)** |
| Symptom guidance | **Future (Phase 4)** |
| Trained classifier, MedQuAD, Ollama, front desk | **Optional (Phase 5)**, all switched off |

---

## 9. Known limitations

- **No login yet.** The dashboard greets "welcome to Nova Health" without a name. Demo login comes in Phase 2.
- **Module pages are previews.** They say plainly that they are not built yet.
- **Test warning:** pytest shows a `StarletteDeprecationWarning` about `httpx` in the test client. It is harmless for now and will be reviewed if it breaks in a later library update.
- **Browser tests need the app running** (`scripts\start.ps1`) before `npm.cmd run test:e2e`.
- **Git identity:** the laptop has no global Git `user.name` / `user.email`. To avoid changing your Git config, the commit set the author only for that one command (`git -c user.name=… -c user.email=…`).
- **Terminal output:** this machine's shell sometimes mangles command output, so the test results above were read from log files or clean background terminals.

---

## 10. Current state and next steps

The foundation is working. Both servers start, the browser shows the live backend connection, and the full shell is navigable and responsive.

**Next: Phase 2 (Persistence, Dashboard and Appointment Management)**
1. Add SQLModel and SQLite tables, load the demo data, and add demo login (`patient@novahealth.demo`).
2. Move the departments to `backend/app/knowledge/hospital_info.json`, served by `/api/hospital/departments`.
3. Build the appointment request form and `/api/appointments`: validated, protected against double submission, saved as **Pending**, owned by the logged-in patient.
4. Connect the dashboard's Recent activity and upcoming requests to real data.
