<#
.SYNOPSIS
  Makes sure the repository has a `.env` file with a random SESSION_SECRET.
  Called by setup.ps1 and start.ps1. Never overwrites an existing secret.
#>

$RepoRoot = Split-Path -Parent $PSScriptRoot
$EnvFile = Join-Path $RepoRoot ".env"
$ExampleFile = Join-Path $RepoRoot ".env.example"

if (-not (Test-Path $EnvFile)) {
    Copy-Item $ExampleFile $EnvFile
    Write-Host "Created .env from .env.example"
}

$content = Get-Content $EnvFile -Raw
if ($content -notmatch "(?m)^SESSION_SECRET=\S+") {
    # 48 random bytes from the OS cryptographic generator, URL-safe base64.
    $bytes = New-Object byte[] 48
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $secret = [Convert]::ToBase64String($bytes).TrimEnd("=").Replace("+", "-").Replace("/", "_")

    if ($content -match "(?m)^SESSION_SECRET=\s*$") {
        $content = [regex]::Replace($content, "(?m)^SESSION_SECRET=\s*$", "SESSION_SECRET=$secret")
    }
    else {
        $content = $content.TrimEnd() + "`r`nSESSION_SECRET=$secret`r`n"
    }
    Set-Content -Path $EnvFile -Value $content -NoNewline -Encoding utf8
    Write-Host "Generated a random SESSION_SECRET in .env"
}
