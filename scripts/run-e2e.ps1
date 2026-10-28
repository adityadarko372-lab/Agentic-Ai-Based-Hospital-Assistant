<#
.SYNOPSIS
    Run the Playwright browser tests against a fresh, throwaway database.

.DESCRIPTION
    Starts the backend on port 8000 with backend\data\e2e.db (deleted first and
    afterwards) and the Vite dev server on port 5173, runs the tests, then stops
    both. The demo database is not touched.

    -AllFeatures switches on every optional Phase 5 feature for this run only
    (front desk, health information, trained classifier, Ollama rewording).
    Tests for features that are off, or not installed, skip themselves.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\scripts\run-e2e.ps1
    powershell -ExecutionPolicy Bypass -File .\scripts\run-e2e.ps1 -AllFeatures
#>
param(
    [switch]$AllFeatures,
    [string]$LogFile = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $RepoRoot "backend"
$Frontend = Join-Path $RepoRoot "frontend"
$Python = Join-Path $Backend ".venv\Scripts\python.exe"
$Database = Join-Path $Backend "data\e2e.db"
$env:Path = "C:\Program Files\nodejs;$env:Path"

foreach ($port in 8000, 5173) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $port is in use. Stop the running app first (close its server windows)."
    }
}

$flag = if ($AllFeatures) { "true" } else { "false" }
$serverEnv = @{
    DATABASE_PATH        = $Database
    FRONT_DESK_ENABLED   = $flag
    HEALTH_INFO_ENABLED  = $flag
    LLM_PHRASING_ENABLED = $flag
    INTENT_CLASSIFIER    = $(if ($AllFeatures) { "transformer" } else { "rules" })
}
Remove-Item -LiteralPath $Database -ErrorAction SilentlyContinue

$saved = @{}
foreach ($key in $serverEnv.Keys) { $saved[$key] = [Environment]::GetEnvironmentVariable($key); [Environment]::SetEnvironmentVariable($key, $serverEnv[$key]) }
$backendProcess = Start-Process -FilePath $Python -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory $Backend -WindowStyle Hidden -PassThru
foreach ($key in $saved.Keys) { [Environment]::SetEnvironmentVariable($key, $saved[$key]) }
$frontendProcess = Start-Process -FilePath "npm.cmd" -ArgumentList "run", "dev" -WorkingDirectory $Frontend -WindowStyle Hidden -PassThru

$exitCode = 1
try {
    $ready = $false
    for ($i = 0; $i -lt 60 -and -not $ready; $i++) {
        Start-Sleep -Seconds 2
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:5173/api/health" -TimeoutSec 3
            $ready = $true
        } catch { }
    }
    if (-not $ready) { throw "The app did not start within two minutes." }
    Write-Host "Features: $($health.features | ConvertTo-Json -Compress)"
    if ($LogFile) { "Features: $($health.features | ConvertTo-Json -Compress)" | Out-File $LogFile }

    Push-Location $Frontend
    try {
        if ($LogFile) { & ".\node_modules\.bin\playwright.cmd" test *>> $LogFile } else { & ".\node_modules\.bin\playwright.cmd" test }
        $exitCode = $LASTEXITCODE
    } finally {
        Pop-Location
    }
} finally {
    foreach ($process in $backendProcess, $frontendProcess) {
        if ($process -and -not $process.HasExited) { & taskkill.exe /PID $process.Id /T /F | Out-Null }
    }
    Start-Sleep -Seconds 1
    Remove-Item -LiteralPath $Database -ErrorAction SilentlyContinue
}
if ($LogFile) { "E2E_EXIT=$exitCode" | Out-File -Append $LogFile }
exit $exitCode
