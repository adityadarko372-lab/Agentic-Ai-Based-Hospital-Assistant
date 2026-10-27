<#
.SYNOPSIS
  Deletes the local demo database so the next backend start recreates it with
  fresh demo patients and departments and no appointment requests.

.USAGE
  Stop the backend first, then:
  powershell -ExecutionPolicy Bypass -File ".\scripts\reset-demo-data.ps1"
#>

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Database = Join-Path $RepoRoot "backend\data\nova_health.db"

if (Test-Path $Database) {
    try {
        Remove-Item -LiteralPath $Database -ErrorAction Stop
        Write-Host "Demo database removed. It will be recreated on the next backend start." -ForegroundColor Green
    }
    catch {
        Write-Host "Could not delete the database. Stop the backend window first, then run this again." -ForegroundColor Yellow
        exit 1
    }
}
else {
    Write-Host "No demo database found; nothing to reset."
}
