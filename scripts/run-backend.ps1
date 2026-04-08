param(
    [string]$Host = "127.0.0.1",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

function Resolve-Python {
    $candidates = @(
        (Join-Path $repoRoot ".venv\Scripts\python.exe"),
        (Join-Path $repoRoot "tender_navigator_mvp\.venv\Scripts\python.exe")
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    $command = Get-Command python -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    throw "Python not found. Create .venv or install Python."
}

$pythonExe = Resolve-Python
$defaultDbPath = (Join-Path $repoRoot "backend\data\tender_navigator_backend.db").Replace("\", "/")

if (-not $env:TENDER_NAVIGATOR_DATABASE_URL) {
    $env:TENDER_NAVIGATOR_DATABASE_URL = "sqlite:///$defaultDbPath"
}

if (-not $env:TENDER_NAVIGATOR_CELERY_EAGER) {
    $env:TENDER_NAVIGATOR_CELERY_EAGER = "true"
}

Write-Host "Starting backend on http://$Host`:$Port"
Write-Host "Database: $env:TENDER_NAVIGATOR_DATABASE_URL"
Write-Host "Celery eager: $env:TENDER_NAVIGATOR_CELERY_EAGER"

& $pythonExe -m uvicorn backend.app.main:app --reload --host $Host --port $Port
