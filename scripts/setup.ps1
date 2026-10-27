<#
.SYNOPSIS
  One-time setup for Nova Health: creates the backend virtual environment and
  installs backend and frontend dependencies.

.USAGE
  powershell -ExecutionPolicy Bypass -File ".\scripts\setup.ps1"
#>

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend"
$VenvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"

# Make freshly installed tools visible even if this shell predates their install.
$env:Path = "C:\Program Files\nodejs;C:\Program Files\Git\cmd;$env:Path"

Write-Host "== Nova Health setup ==" -ForegroundColor Cyan

# --- Backend ---
if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating Python 3.13 virtual environment..."
    & py -3.13 -m venv (Join-Path $BackendDir ".venv")
    if ($LASTEXITCODE -ne 0) { throw "Could not create the venv. Is Python 3.13 installed (py -3.13)?" }
}

Write-Host "Installing backend dependencies..."
& $VenvPython -m pip install --upgrade pip --quiet
& $VenvPython -m pip install -r (Join-Path $BackendDir "requirements-dev.txt") --quiet
if ($LASTEXITCODE -ne 0) { throw "Backend dependency installation failed." }

# --- Frontend ---
Write-Host "Installing frontend dependencies..."
Push-Location $FrontendDir
try {
    & npm.cmd ci
    if ($LASTEXITCODE -ne 0) { throw "Frontend dependency installation failed." }
}
finally {
    Pop-Location
}

# --- Local configuration (.env with a random SESSION_SECRET) ---
& (Join-Path $PSScriptRoot "ensure-env.ps1")

Write-Host "Setup complete. Start the app with: .\scripts\start.ps1" -ForegroundColor Green
