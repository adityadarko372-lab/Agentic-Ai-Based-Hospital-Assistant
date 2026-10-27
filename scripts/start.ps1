<#
.SYNOPSIS
  Starts the Nova Health backend (FastAPI, port 8000) and frontend (Vite,
  port 5173) in two separate PowerShell windows, then opens the browser.

.USAGE
  powershell -ExecutionPolicy Bypass -File ".\scripts\start.ps1"

  Close the two server windows (or press Ctrl+C in them) to stop the app.
#>

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend"
$VenvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
$NodeDir = "C:\Program Files\nodejs"

if (-not (Test-Path $VenvPython)) {
    throw "Backend environment not found. Run .\scripts\setup.ps1 first."
}
if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
    throw "Frontend dependencies not found. Run .\scripts\setup.ps1 first."
}

# A persistent session secret keeps users signed in across backend restarts.
& (Join-Path $PSScriptRoot "ensure-env.ps1")

# Each window gets its own command. Paths are single-quoted inside the command
# string because the workspace path contains spaces.
$BackendCommand = "Set-Location -LiteralPath '$BackendDir'; " +
    "`$host.UI.RawUI.WindowTitle = 'Nova Health - Backend'; " +
    "& '$VenvPython' -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

$FrontendCommand = "Set-Location -LiteralPath '$FrontendDir'; " +
    "`$host.UI.RawUI.WindowTitle = 'Nova Health - Frontend'; " +
    "`$env:Path = '$NodeDir;' + `$env:Path; " +
    "npm.cmd run dev"

Write-Host "Starting Nova Health backend on http://127.0.0.1:8000 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $BackendCommand)

Write-Host "Starting Nova Health frontend on http://127.0.0.1:5173 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $FrontendCommand)

# Wait until the backend answers before opening the browser (max ~30 s).
$healthUrl = "http://127.0.0.1:8000/api/health"
for ($attempt = 1; $attempt -le 30; $attempt++) {
    try {
        $response = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2
        if ($response.status -eq "ok") {
            Write-Host "Backend is healthy." -ForegroundColor Green
            break
        }
    }
    catch {
        Start-Sleep -Seconds 1
    }
}

Start-Sleep -Seconds 2
Start-Process "http://127.0.0.1:5173"
Write-Host "Nova Health is starting. If the page is blank, wait a few seconds and refresh." -ForegroundColor Green
