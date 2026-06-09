#!/usr/bin/env bash
# Usage: run-csv.sh <csv-dataset> [output-dir] [retrieval-backend: keyword|vector] [--llm]
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$ROOT/.venv/bin/python"
# --- BadmintonRAG/.env loader ---
set -a; [ -f "$ROOT/.env" ] && . "$ROOT/.env"; set +a
[ -x "$PYTHON" ] || { echo "venv not found at $PYTHON. Create it and install requirements first." >&2; exit 1; }

CSV_DATASET="${1:?csv-dataset required}"
OUTPUT_DIR="${2:-rag_project/outputs/trial_run}"
BACKEND="${3:-keyword}"
LLM_FLAG=""
[ "${4:-}" = "--llm" ] && LLM_FLAG="--llm"

cd "$ROOT"
exec "$PYTHON" -m rag_project.diagnostics.trial_run \
  --csv-dataset "$CSV_DATASET" \
  --output-dir "$OUTPUT_DIR" \
  --retrieval-backend "$BACKEND" $LLM_FLAG
