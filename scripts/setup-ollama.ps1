<#
.SYNOPSIS
    Optional (Phase 5): start the local Ollama server and download the small
    model used to reword some assistant replies (LLM_PHRASING_ENABLED=true).

.DESCRIPTION
    Not needed for the required demo. Free and local: the model runs on this
    laptop and no text is sent anywhere. Install Ollama first:
        winget install --id Ollama.Ollama -e
    Then run:  scripts\setup-ollama.ps1   (about 2 GB download for qwen2.5:3b)
#>
param(
    [string]$Model = "qwen2.5:3b",
    [string]$LogFile = ""
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Text) {
    Write-Host $Text
    if ($LogFile) { $Text | Out-File -Append -FilePath $LogFile }
}

$exe = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
if (-not (Test-Path $exe)) {
    $command = Get-Command ollama -ErrorAction SilentlyContinue
    if ($null -eq $command) { throw "Ollama is not installed. Run: winget install --id Ollama.Ollama -e" }
    $exe = $command.Source
}
Write-Step "Ollama: $(& $exe --version 2>&1)"

$up = $false
for ($i = 0; $i -lt 20; $i++) {
    try {
        Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/version" -TimeoutSec 2 | Out-Null
        $up = $true
        break
    } catch {
        if ($i -eq 0) { Start-Process -FilePath $exe -ArgumentList "serve" -WindowStyle Hidden }
        Start-Sleep -Seconds 2
    }
}
if (-not $up) { throw "The Ollama server did not start on http://127.0.0.1:11434" }
Write-Step "Server running on http://127.0.0.1:11434"

Write-Step "Downloading $Model (skipped if already present)..."
# Ollama prints progress on stderr; Windows PowerShell would treat that as an error.
$ErrorActionPreference = "Continue"
& $exe pull $Model 2>$null
$pullExit = $LASTEXITCODE
$ErrorActionPreference = "Stop"
if ($pullExit -ne 0) { throw "ollama pull $Model failed (exit $pullExit)" }
& $exe list | ForEach-Object { Write-Step "$_" }
Write-Step "Done. Set LLM_PHRASING_ENABLED=true in .env and restart the backend."
