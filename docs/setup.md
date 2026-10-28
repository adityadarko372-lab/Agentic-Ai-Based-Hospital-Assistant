# Nova Health: Setup Guide (Windows)

## Requirements

| Tool | Tested version | Check with |
|---|---|---|
| Windows 10/11 + PowerShell | Windows 11 | — |
| Python | 3.13.6 | `py -3.13 --version` |
| Node.js + npm | 26.12.1 / 11.20.0 (Node 20+ works) | `node --version` |
| Git | 2.56 | `git --version` |
| Microsoft Edge | preinstalled | used only by the browser tests |

No GPU, internet connection, API key or paid service is needed to run the app. Disk use for the required scope is about 0.6 GB (Python packages and `node_modules`).

> Node.js and Git may be installed but missing from PATH in an old terminal. The scripts add `C:\Program Files\nodejs` themselves. PowerShell may block `npm.ps1`; the scripts use `npm.cmd` and `-ExecutionPolicy Bypass`.

## First-time setup

```powershell
git clone https://github.com/adityadarko372-lab/Agentic-Ai-Based-Hospital-Assistant.git
cd Agentic-Ai-Based-Hospital-Assistant
powershell -ExecutionPolicy Bypass -File ".\scripts\setup.ps1"
```

`setup.ps1`:
- creates `backend\.venv` (Python 3.13)
- installs `backend\requirements-dev.txt`
- runs `npm ci` in `frontend`
- creates `.env` with a random `SESSION_SECRET`

## Start the app

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\start.ps1"
```

| Address | What |
|---|---|
| http://127.0.0.1:5173 | the app |
| http://127.0.0.1:8000/docs | interactive API documentation |

Demo login: `patient@novahealth.demo` / `NovaDemo@2026` (or press **Fill in**). Stop the app by closing the two server windows.

## Reset the demo data

Stop the backend window first, then:

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\reset-demo-data.ps1"
```

The database `backend\data\nova_health.db` is recreated on the next start with the 3 demo patients, 11 departments and no requests.

## Run the tests

```powershell
cd backend;  .\.venv\Scripts\python.exe -m pytest -q
cd frontend; npm.cmd run typecheck; npm.cmd test; npm.cmd run build
cd frontend; npm.cmd run test:e2e      # start the app first
```

The browser tests (including the 6-step demo and the accessibility check) create, then cancel, a request in the running backend's database. Reset the demo data before a presentation.

## Configuration (`.env`)

| Setting | Default | Meaning |
|---|---|---|
| `SESSION_SECRET` | random (generated) | signs login sessions; never commit it |
| `SESSION_HOURS` | 8 | how long a login lasts |
| `DATABASE_PATH` | `backend/data/nova_health.db` | SQLite file |
| `INTENT_CLASSIFIER` | `rules` | `transformer` is optional Phase 5; falls back to rules if not installed |
| `HEALTH_INFO_ENABLED`, `LLM_PHRASING_ENABLED`, `FRONT_DESK_ENABLED` | `false` | optional Phase 5 features; not needed for the demo |

## Troubleshooting

| Problem | Fix |
|---|---|
| "Backend offline" in the top bar | Check that the backend window is running; restart with `start.ps1` |
| Port 8000 or 5173 already in use | Close old server windows, or find the process: `Get-NetTCPConnection -LocalPort 8000` |
| Signed out after a restart | `.env` has no `SESSION_SECRET`; run `scripts\ensure-env.ps1` |
| `npm` not recognised | Use a new terminal or `& "C:\Program Files\nodejs\npm.cmd"` |
| Browser tests time out | Run with the default 2 workers; close other heavy apps |
