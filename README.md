# BadmintonRAG

Research-grade badminton RAG and diagnostic prototype.

Current scope:

- Literature acquisition manifests and metadata for badminton action-analysis sources.
- Forehand-clear diagnostic MVP based on correct-template deviation detection.
- Offline tests for schema validation, feature extraction, template construction, source classification, text extraction, and diagnosis reports.

The first diagnostic phase does not require an LLM key. LLM configuration is reserved for the later RAG explanation layer and should be provided through environment variables:

```text
RAG_LLM_BASE_URL
RAG_LLM_API_KEY
RAG_LLM_MODEL
```

Downloaded third-party PDF/HTML artifacts are intentionally not committed. Rebuild or refresh them with:

```powershell
python rag_project/tools/download_sources.py --proxy http://127.0.0.1:10808
```

Run tests:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -v
```

Run the deterministic forehand-clear RAG demo:

```powershell
.\.venv\Scripts\python.exe -m rag_project.diagnostics.run_forehand_clear_rag_demo
```

This writes Markdown reports under `rag_project/outputs/forehand_clear_rag_reports/`. The generated reports are local artifacts and are ignored by Git.
