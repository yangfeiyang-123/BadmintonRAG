from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

from rag_project.diagnostics.batch import run_batch_diagnosis_dataset
from rag_project.diagnostics.csv_adapter import load_dataset_from_csv
from rag_project.diagnostics.data_contract import SimulationContractError, validate_simulation_csv_contract


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_report_index(output_dir: Path, summary: dict[str, object], markdown_paths: list[str]) -> Path:
    report_index = output_dir / "report_index.html"
    report_items = "\n".join(
        f'<li><a href="{html.escape(Path(path).as_posix())}">{html.escape(Path(path).name)}</a></li>'
        for path in markdown_paths
    )
    body = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>BadmintonRAG Trial Run</title>
  <style>
    body {{ font-family: "Segoe UI", Arial, sans-serif; margin: 32px; color: #1f2937; }}
    code {{ background: #f3f4f6; padding: 2px 5px; border-radius: 4px; }}
    li {{ margin: 8px 0; }}
  </style>
</head>
<body>
  <h1>BadmintonRAG Trial Run</h1>
  <p>Dataset: <code>{html.escape(str(summary["dataset_id"]))}</code></p>
  <p>Action: <code>{html.escape(str(summary["action_type"]))}</code></p>
  <p>Evaluated samples: <code>{html.escape(str(summary["evaluated_samples"]))}</code></p>
  <h2>Artifacts</h2>
  <ul>
    <li><a href="contract_report.json">contract_report.json</a></li>
    <li><a href="diagnosis_reports.json">diagnosis_reports.json</a></li>
    <li><a href="summary.json">summary.json</a></li>
  </ul>
  <h2>Markdown Reports</h2>
  <ul>{report_items}</ul>
</body>
</html>
"""
    report_index.write_text(body, encoding="utf-8")
    return report_index


def run_trial(
    csv_dataset: Path,
    output_dir: Path,
    retrieval_backend: str = "keyword",
    use_llm: bool = False,
) -> dict[str, object]:
    contract_report = validate_simulation_csv_contract(csv_dataset)
    dataset = load_dataset_from_csv(csv_dataset)
    result = run_batch_diagnosis_dataset(
        dataset,
        retrieval_backend=retrieval_backend,
        use_llm=use_llm,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    markdown_paths: list[str] = []
    reports = []
    for report in result["reports"]:
        report_payload = dict(report)
        markdown = str(report_payload.pop("markdown"))
        markdown_path = reports_dir / f"{report_payload['sample_id']}.md"
        markdown_path.write_text(markdown, encoding="utf-8")
        markdown_paths.append(str(Path("reports") / markdown_path.name))
        reports.append(report_payload)

    contract_path = output_dir / "contract_report.json"
    diagnosis_path = output_dir / "diagnosis_reports.json"
    summary_path = output_dir / "summary.json"
    summary = dict(result["summary"])
    report_index = _write_report_index(output_dir, summary, markdown_paths)
    trial_summary = {
        "passed": True,
        **summary,
        "contract_report": str(contract_path),
        "diagnosis_json": str(diagnosis_path),
        "summary_json": str(summary_path),
        "report_index": str(report_index),
        "markdown_reports": [str(output_dir / path) for path in markdown_paths],
    }

    _write_json(contract_path, contract_report.to_json_dict())
    _write_json(diagnosis_path, reports)
    _write_json(summary_path, trial_summary)
    return trial_summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a full CSV trial: contract check, diagnosis, and report index.")
    parser.add_argument("--csv-dataset", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--retrieval-backend", choices=["keyword", "vector", "hybrid"], default="keyword")
    parser.add_argument("--llm", action="store_true", help="Call an OpenAI-compatible LLM using BADMINTON_LLM_* env vars.")
    args = parser.parse_args(argv)

    try:
        summary = run_trial(
            csv_dataset=args.csv_dataset,
            output_dir=args.output_dir,
            retrieval_backend=args.retrieval_backend,
            use_llm=args.llm,
        )
    except SimulationContractError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

