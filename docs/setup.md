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

Demo login: `patient@novahealth.demo` / `NovaDemo@2026` (or choose an account and press **Fill in**; see [Demo accounts](#demo-accounts)). Stop the app by closing the two server windows.

## Reset the demo data

Stop the backend window first, then:

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\reset-demo-data.ps1"
```

The database `backend\data\nova_health.db` is recreated on the next start with the 6 demo patients, the front-desk staff account, 11 departments and no requests.

## Demo accounts

All accounts are fictional demo logins with the password `NovaDemo@2026`. The login page has a **Demo account** picker and a **Fill in** button.

| Email | Name | Role |
|---|---|---|
| `patient@novahealth.demo` | Asha Verma | Patient (main demo account) |
| `aditya.singh@novahealth.demo` | Aditya Singh | Patient |
| `aaryan.naik@novahealth.demo` | Aaryan Naik | Patient |
| `bhavish.keni@novahealth.demo` | Bhavish Keni | Patient |
| `rohan.mehta@novahealth.demo` | Rohan Mehta | Patient |
| `kavya.iyer@novahealth.demo` | Kavya Iyer | Patient |
| `frontdesk@novahealth.demo` | Meera Desai | Front-desk staff (needs `FRONT_DESK_ENABLED=true`) |

Patients only ever see their own requests and history. The staff account sees the Front Desk page and the services directory, not the patient pages.

## Optional Phase 5 features

None of these are needed for the required demo. Each is switched on in `.env` and falls back safely when something is missing. The dashboard's **System status** card shows what is really running.

| Feature | Switch | One-time setup |
|---|---|---|
| Front-desk review | `FRONT_DESK_ENABLED=true` | none |
| Health information (NIH MedQuAD) | `HEALTH_INFO_ENABLED=true` | steps 1, 2, 3 |
| Trained intent classifier | `INTENT_CLASSIFIER=transformer` | steps 1, 4 |
| AI rewording (local Ollama) | `LLM_PHRASING_ENABLED=true` | step 5 |
| Voice input | none | Chrome or Edge; shown only where the browser supports it |

```powershell
# 1. PyTorch with CUDA (2.75 GB), then the other ML libraries
cd backend
.\.venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cu128
.\.venv\Scripts\python.exe -m pip install -r requirements-optional.txt
cd ..

# 2. Download and prepare MedQuAD (16 MB download)
backend\.venv\Scripts\python.exe datasets\prepare_medquad.py

# 3. Build the MedQuAD search index (about 10 s on the RTX 4060), optionally evaluate it
backend\.venv\Scripts\python.exe model\health_info\build_index.py
backend\.venv\Scripts\python.exe model\health_info\evaluate.py

# 4. Build the intent data and fine-tune DistilBERT (about 30 s on the RTX 4060), then evaluate
backend\.venv\Scripts\python.exe model\intent_classifier\build_dataset.py
backend\.venv\Scripts\python.exe model\intent_classifier\train.py
backend\.venv\Scripts\python.exe model\intent_classifier\evaluate.py

# 5. Ollama and the qwen2.5:3b model (about 1.9 GB)
winget install --id Ollama.Ollama -e
powershell -ExecutionPolicy Bypass -File ".\scripts\setup-ollama.ps1"
```

If a large download stops half-way (pip prints "Connection interrupted"), download the wheel with `curl.exe -L -C - -o torch.whl <url>`, which resumes, and then `pip install torch.whl`.

Restart the backend after changing `.env`. Models, indexes and datasets are written to `model/artifacts/` and `datasets/`, which are gitignored. Licences are listed in [`LICENSES.md`](../LICENSES.md).

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
| `INTENT_CLASSIFIER` | `rules` | `transformer` uses the fine-tuned model with the rules (falls back to rules if not installed) |
| `HEALTH_INFO_ENABLED` | `false` | MedQuAD general health information |
| `HEALTH_INFO_MIN_SCORE` | `0.55` | minimum similarity before a passage is shown |
| `LLM_PHRASING_ENABLED` | `false` | local Ollama rewording of hospital-information replies |
| `OLLAMA_URL`, `OLLAMA_MODEL`, `LLM_TIMEOUT_SECONDS` | `http://127.0.0.1:11434`, `qwen2.5:3b`, `8` | only a local address is accepted |
| `FRONT_DESK_ENABLED` | `false` | front-desk review page for the staff account |

## Troubleshooting

| Problem | Fix |
|---|---|
| "Backend offline" in the top bar | Check that the backend window is running; restart with `start.ps1` |
| Port 8000 or 5173 already in use | Close old server windows, or find the process: `Get-NetTCPConnection -LocalPort 8000` |
| Signed out after a restart | `.env` has no `SESSION_SECRET`; run `scripts\ensure-env.ps1` |
| `npm` not recognised | Use a new terminal or `& "C:\Program Files\nodejs\npm.cmd"` |
| Browser tests time out | Run with the default 2 workers; close other heavy apps |
