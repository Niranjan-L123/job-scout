# Runs job-scout locally using secrets from .env (gitignored).
# Usage: .\run-local.ps1 [-DryRun]
param([switch]$DryRun)

$envFile = Join-Path $PSScriptRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#=]+?)\s*=\s*(.+?)\s*$') {
            [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], "Process")
        }
    }
} else {
    Write-Warning ".env not found - running without webhook/Adzuna credentials"
}

Set-Location $PSScriptRoot
if ($DryRun) {
    python -m scraper.main --dry-run
} else {
    python -m scraper.main
}
