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

The Web viewer reads `GET /config` and enables the LLM report checkbox when `BADMINTON_LLM_BASE_URL` and `BADMINTON_LLM_MODEL` are set. The API key is only reported as present or absent and is never returned by the config endpoint.

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

After the virtual environment is ready, the Windows helper scripts provide the shortest path:

```powershell
.\scripts\bootstrap.ps1
.\scripts\smoke.ps1
.\scripts\test.ps1
```

Run the deterministic forehand-clear RAG demo:

```powershell
.\.venv\Scripts\python.exe -m rag_project.system.bootstrap bootstrap
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
.\.venv\Scripts\python.exe -m rag_project.system.bootstrap bootstrap
.\.venv\Scripts\python.exe -m rag_project.diagnostics.batch `
  --dataset rag_project\examples\forehand_clear_dataset.json `
  --output-dir rag_project\outputs\batch_forehand_clear_vector `
  --retrieval-backend vector
```

The dataset JSON must contain `correct_samples` and `eval_samples`. Each sample includes `time`, `events.impact`, `joint_angles`, `muscle_activation`, and a discrete `outcome_label`.

Run batch diagnostics from a simulation CSV:

```powershell
.\.venv\Scripts\python.exe -m rag_project.diagnostics.batch `
  --csv-dataset rag_project\examples\forehand_clear_simulation.csv `
  --output-dir rag_project\outputs\batch_forehand_clear_csv `
  --retrieval-backend keyword
```

CSV rows represent time points. Required columns are `sample_id`, `split`, `action_type`, `outcome_label`, and `time`. Use `split=correct` for template samples and `split=eval` for samples to diagnose. Event columns use `event_` prefixes such as `event_impact`; joint angle columns use `joint_` prefixes such as `joint_trunk_rotation`; muscle activation columns use `muscle_` prefixes such as `muscle_external_oblique`.

Validate a real simulation CSV before diagnosis:

```powershell
.\.venv\Scripts\python.exe -m rag_project.diagnostics.data_contract `
  --csv-dataset rag_project\examples\forehand_clear_simulation.csv
```

The full input mapping is documented in `docs/simulation_data_contract.md`.

Check or rebuild system artifacts:

```powershell
.\.venv\Scripts\python.exe -m rag_project.system.bootstrap doctor
.\.venv\Scripts\python.exe -m rag_project.system.bootstrap bootstrap
.\.venv\Scripts\python.exe -m rag_project.system.bootstrap smoke
```

Equivalent helper scripts:

```powershell
.\scripts\bootstrap.ps1
.\scripts\smoke.ps1
```

Serve the HTTP API:

```powershell
.\.venv\Scripts\python.exe -m rag_project.api.server --host 127.0.0.1 --port 8765
```

Equivalent helper script:

```powershell
.\scripts\serve.ps1 -HostName 127.0.0.1 -Port 8765
```

Open the report viewer at `http://127.0.0.1:8765/`. The viewer can load the example JSON request, load or upload simulation CSV, call the batch diagnosis API, and render deviation signals, correct-template ranges, correction plans, and evidence.

Available endpoints:

- `GET /health`
- `GET /config`
- `GET /`
- `GET /viewer`
- `GET /examples/api_batch_request.json`
- `GET /examples/forehand_clear_simulation.csv`
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
