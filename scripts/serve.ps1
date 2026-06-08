param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Python virtual environment not found at $Python. Create it and install requirements first."
}

Push-Location $Root
try {
    & $Python -m rag_project.api.server --host $HostName --port $Port
}
finally {
    Pop-Location
}
