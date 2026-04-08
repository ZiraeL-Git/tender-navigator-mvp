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

if (-not $env:TENDER_NAVIGATOR_CELERY_EAGER) {
    $env:TENDER_NAVIGATOR_CELERY_EAGER = "false"
}

if (-not $env:TENDER_NAVIGATOR_CELERY_BROKER_URL) {
    $env:TENDER_NAVIGATOR_CELERY_BROKER_URL = "redis://localhost:6379/0"
}

if (-not $env:TENDER_NAVIGATOR_CELERY_RESULT_BACKEND) {
    $env:TENDER_NAVIGATOR_CELERY_RESULT_BACKEND = $env:TENDER_NAVIGATOR_CELERY_BROKER_URL
}

Write-Host "Starting Celery worker"
Write-Host "Broker: $env:TENDER_NAVIGATOR_CELERY_BROKER_URL"

& $pythonExe -m celery -A backend.app.tasks.celery_app.celery_app worker -l info
