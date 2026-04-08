param(
    [string]$ApiProxyTarget = "http://127.0.0.1:8000",
    [int]$Port = 3000
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

$nodeCommand = Get-Command node -ErrorAction SilentlyContinue
$npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue

if (-not $nodeCommand -or -not $npmCommand) {
    throw "Node.js and npm are required. Install Node.js 20+ first."
}

$env:NEXT_PUBLIC_API_BASE_URL = "/api/v1"
$env:TENDER_NAVIGATOR_API_PROXY_TARGET = $ApiProxyTarget.TrimEnd("/")

Write-Host "Starting frontend on http://127.0.0.1:$Port"
Write-Host "API base URL: $env:NEXT_PUBLIC_API_BASE_URL"
Write-Host "API proxy target: $env:TENDER_NAVIGATOR_API_PROXY_TARGET"

Push-Location (Join-Path $repoRoot "frontend")
try {
    & $npmCommand.Source run dev -- --hostname 127.0.0.1 --port $Port
}
finally {
    Pop-Location
}
