#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$ROOT/.venv/bin/python"
# --- BadmintonRAG/.env loader ---
set -a; [ -f "$ROOT/.env" ] && . "$ROOT/.env"; set +a
[ -x "$PYTHON" ] || { echo "venv not found at $PYTHON. Create it and install requirements first." >&2; exit 1; }
cd "$ROOT"
exec "$PYTHON" -m rag_project.system.audit --root rag_project
