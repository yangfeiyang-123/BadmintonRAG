# BadmintonRAG

Research-grade badminton RAG and diagnostic prototype.

Current scope:

- Literature acquisition manifests and metadata for badminton action-analysis sources.
- Forehand-clear diagnostic MVP based on correct-template deviation detection.
- Processed text corpus generation, local TF-IDF vector retrieval, and retrieval evaluation.
- Offline tests for schema validation, feature extraction, template construction, source classification, text extraction, retrieval, LLM prompt construction, and diagnosis reports.

The deterministic diagnostic and retrieval pipeline does not require an LLM key. If you want to call an OpenAI-compatible chat-completions endpoint, provide:

```text
BADMINTON_LLM_BASE_URL
BADMINTON_LLM_API_KEY
BADMINTON_LLM_MODEL
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
.\.venv\Scripts\python.exe -m rag_project.knowledge.source_catalog
.\.venv\Scripts\python.exe -m rag_project.knowledge.text_corpus
.\.venv\Scripts\python.exe -m rag_project.knowledge.vector_index
.\.venv\Scripts\python.exe -m rag_project.knowledge.retrieval_eval
.\.venv\Scripts\python.exe -m rag_project.diagnostics.run_forehand_clear_rag_demo
```

This writes Markdown reports under `rag_project/outputs/forehand_clear_rag_reports/`. The generated reports are local artifacts and are ignored by Git.

Run batch diagnostics from a simulation dataset:

```powershell
.\.venv\Scripts\python.exe -m rag_project.diagnostics.batch `
  --dataset rag_project\examples\forehand_clear_dataset.json `
  --output-dir rag_project\outputs\batch_forehand_clear `
  --retrieval-backend keyword
```

Use the local vector index for evidence retrieval:

```powershell
.\.venv\Scripts\python.exe -m rag_project.knowledge.text_corpus
.\.venv\Scripts\python.exe -m rag_project.knowledge.vector_index
.\.venv\Scripts\python.exe -m rag_project.diagnostics.batch `
  --dataset rag_project\examples\forehand_clear_dataset.json `
  --output-dir rag_project\outputs\batch_forehand_clear_vector `
  --retrieval-backend vector
```

The dataset JSON must contain `correct_samples` and `eval_samples`. Each sample includes `time`, `events.impact`, `joint_angles`, `muscle_activation`, and a discrete `outcome_label`.

Serve the HTTP API:

```powershell
.\.venv\Scripts\python.exe -m rag_project.api.server --host 127.0.0.1 --port 8765
```

Open the report viewer at `http://127.0.0.1:8765/`. The viewer can load the example JSON request, call the batch diagnosis API, and render deviation signals, correct-template ranges, correction plans, and evidence.

Available endpoints:

- `GET /health`
- `POST /diagnose/batch`

`POST /diagnose/batch` accepts JSON with `dataset`, optional `retrieval_backend`, optional `evidence_chunks`, and optional `llm`. It returns the same `summary` and structured `reports` as the batch pipeline.

Example API request:

```powershell
$body = Get-Content rag_project\examples\api_batch_request.json -Raw
Invoke-RestMethod `
  -Uri http://127.0.0.1:8765/diagnose/batch `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```
