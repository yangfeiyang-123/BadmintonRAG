$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Python virtual environment not found at $Python. Create it and install requirements first."
}

Push-Location $Root
try {
    & $Python -m rag_project.system.audit --root rag_project
}
finally {
    Pop-Location
}

