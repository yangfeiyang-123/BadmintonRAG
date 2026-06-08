param(
    [Parameter(Mandatory = $true)]
    [string]$CsvDataset,
    [string]$OutputDir = "rag_project\outputs\trial_run",
    [ValidateSet("keyword", "vector")]
    [string]$RetrievalBackend = "keyword",
    [switch]$Llm
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
    $Args = @(
        "-m", "rag_project.diagnostics.trial_run",
        "--csv-dataset", $CsvDataset,
        "--output-dir", $OutputDir,
        "--retrieval-backend", $RetrievalBackend
    )
    if ($Llm) {
        $Args += "--llm"
    }
    & $Python @Args
}
finally {
    Pop-Location
}

