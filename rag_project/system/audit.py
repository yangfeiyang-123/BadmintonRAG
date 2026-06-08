from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent


def _exists(path: Path) -> bool:
    return path.exists() and path.stat().st_size >= 0


def _domain(status: str, evidence: list[str], gap: str | None = None) -> dict[str, object]:
    payload: dict[str, object] = {"status": status, "evidence": evidence}
    if gap:
        payload["gap"] = gap
    return payload


def _status_from_paths(paths: list[Path], ready_label: str = "ready") -> str:
    return ready_label if all(_exists(path) for path in paths) else "incomplete"


def audit_system(root: Path | None = None) -> dict[str, object]:
    root = root or ROOT
    workspace = root.parent
    domains = {
        "literature_sources": _domain(
            _status_from_paths(
                [
                    root / "manifests" / "badminton_sources.csv",
                    root / "sources" / "raw" / "metadata" / "download_results.csv",
                    root / "sources" / "processed" / "metadata" / "source_catalog.json",
                ]
            ),
            [
                str(root / "manifests" / "badminton_sources.csv"),
                str(root / "sources" / "raw" / "metadata" / "download_results.csv"),
                str(root / "sources" / "processed" / "metadata" / "source_catalog.json"),
            ],
        ),
        "rag_retrieval": _domain(
            _status_from_paths(
                [
                    root / "sources" / "processed" / "text" / "chunks.jsonl",
                    root / "sources" / "processed" / "vector" / "local_tfidf_index.json",
                    root / "sources" / "processed" / "metadata" / "retrieval_eval_results.json",
                ]
            ),
            [
                str(root / "sources" / "processed" / "text" / "chunks.jsonl"),
                str(root / "sources" / "processed" / "vector" / "local_tfidf_index.json"),
                str(root / "sources" / "processed" / "metadata" / "retrieval_eval_results.json"),
            ],
        ),
        "diagnostic_engine": _domain(
            _status_from_paths(
                [
                    root / "diagnostics" / "diagnose.py",
                    root / "diagnostics" / "rules_forehand_clear.py",
                    root / "diagnostics" / "templates.py",
                    workspace / "tests" / "diagnostics" / "test_diagnose.py",
                ]
            ),
            [
                str(root / "diagnostics" / "diagnose.py"),
                str(root / "diagnostics" / "rules_forehand_clear.py"),
                str(workspace / "tests" / "diagnostics" / "test_diagnose.py"),
            ],
        ),
        "simulation_data_contract": _domain(
            _status_from_paths(
                [
                    root / "diagnostics" / "data_contract.py",
                    workspace / "docs" / "simulation_data_contract.md",
                    workspace / "tests" / "diagnostics" / "test_data_contract.py",
                ]
            ),
            [
                str(root / "diagnostics" / "data_contract.py"),
                str(workspace / "docs" / "simulation_data_contract.md"),
                str(workspace / "tests" / "diagnostics" / "test_data_contract.py"),
            ],
        ),
        "trial_run": _domain(
            _status_from_paths(
                [
                    root / "diagnostics" / "trial_run.py",
                    workspace / "scripts" / "run-csv.ps1",
                    workspace / "tests" / "diagnostics" / "test_trial_run.py",
                ]
            ),
            [
                str(root / "diagnostics" / "trial_run.py"),
                str(workspace / "scripts" / "run-csv.ps1"),
                str(workspace / "tests" / "diagnostics" / "test_trial_run.py"),
            ],
        ),
        "api": _domain(
            _status_from_paths([root / "api" / "server.py", workspace / "tests" / "api" / "test_server.py"]),
            [str(root / "api" / "server.py"), str(workspace / "tests" / "api" / "test_server.py")],
        ),
        "web_viewer": _domain(
            _status_from_paths([root / "web" / "report_viewer.html", workspace / "tests" / "web" / "test_report_viewer.py"]),
            [str(root / "web" / "report_viewer.html"), str(workspace / "tests" / "web" / "test_report_viewer.py")],
        ),
        "llm_optional": _domain(
            _status_from_paths([root / "llm" / "openai_compatible.py", workspace / "tests" / "llm" / "test_openai_compatible.py"]),
            [
                str(root / "llm" / "openai_compatible.py"),
                "BADMINTON_LLM_BASE_URL/BADMINTON_LLM_API_KEY/BADMINTON_LLM_MODEL are optional runtime env vars",
            ],
        ),
        "windows_scripts": _domain(
            _status_from_paths(
                [
                    workspace / "scripts" / "bootstrap.ps1",
                    workspace / "scripts" / "smoke.ps1",
                    workspace / "scripts" / "test.ps1",
                    workspace / "scripts" / "serve.ps1",
                    workspace / "scripts" / "run-csv.ps1",
                    workspace / "scripts" / "audit.ps1",
                ]
            ),
            [
                str(workspace / "scripts" / "bootstrap.ps1"),
                str(workspace / "scripts" / "smoke.ps1"),
                str(workspace / "scripts" / "test.ps1"),
                str(workspace / "scripts" / "serve.ps1"),
                str(workspace / "scripts" / "run-csv.ps1"),
                str(workspace / "scripts" / "audit.ps1"),
            ],
        ),
    }
    gaps = [
        f"{name}: {domain.get('gap', 'missing required evidence')}"
        for name, domain in domains.items()
        if domain["status"] == "incomplete"
    ]
    return {
        "project": "BadmintonRAG",
        "overall_status": "ready_for_real_csv_trial" if not gaps else "incomplete",
        "domains": domains,
        "gaps": gaps,
        "verification_commands": [
            ".\\.venv\\Scripts\\python.exe -m pytest -v",
            ".\\.venv\\Scripts\\python.exe -m compileall -q rag_project tests",
            ".\\scripts\\smoke.ps1",
            ".\\scripts\\run-csv.ps1 -CsvDataset rag_project\\examples\\forehand_clear_simulation.csv -OutputDir rag_project\\outputs\\trial_run -RetrievalBackend keyword",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit BadmintonRAG system readiness and evidence.")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    print(json.dumps(audit_system(args.root), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
