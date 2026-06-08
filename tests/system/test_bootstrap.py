import csv
import json
from pathlib import Path

from rag_project.system.bootstrap import bootstrap_system, doctor_system


def _write_download_results(root: Path) -> None:
    metadata = root / "sources" / "raw" / "metadata"
    metadata.mkdir(parents=True)
    html = root / "sources" / "raw" / "html" / "CLEAR_ZHAO_LOWER_LIMB.html"
    html.parent.mkdir(parents=True)
    html.write_text(
        "<html><body><p>Forehand clear trunk rotation lower limb movement evidence.</p></body></html>",
        encoding="utf-8",
    )
    with (metadata / "download_results.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["id", "category", "title", "status", "notes", "downloaded_files"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "id": "CLEAR_ZHAO_LOWER_LIMB",
                "category": "clear",
                "title": "Lower Limb Movement on the Backcourt Forehand Clear Stroke",
                "status": "downloaded",
                "notes": "PMC full text",
                "downloaded_files": str(html),
            }
        )


def test_doctor_reports_missing_and_present_artifacts(tmp_path: Path):
    root = tmp_path / "rag_project"
    _write_download_results(root)

    status = doctor_system(root)

    assert status["root"] == str(root)
    assert status["artifacts"]["download_results"]["exists"] is True
    assert status["artifacts"]["source_catalog_csv"]["exists"] is False
    assert status["ready"] is False


def test_bootstrap_system_generates_index_and_eval_outputs(tmp_path: Path):
    root = tmp_path / "rag_project"
    _write_download_results(root)

    result = bootstrap_system(root)

    assert result["ready"] is True
    assert (root / "sources" / "processed" / "metadata" / "source_catalog.csv").exists()
    assert (root / "sources" / "processed" / "text" / "chunks.jsonl").exists()
    assert (root / "sources" / "processed" / "vector" / "local_tfidf_index.json").exists()
    assert (root / "sources" / "processed" / "metadata" / "retrieval_eval_results.json").exists()

    eval_result = json.loads(
        (root / "sources" / "processed" / "metadata" / "retrieval_eval_results.json").read_text(encoding="utf-8")
    )
    assert "summary" in eval_result


def test_bootstrap_cli_exposes_smoke_command():
    import subprocess
    import sys

    completed = subprocess.run(
        [sys.executable, "-m", "rag_project.system.bootstrap", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "smoke" in completed.stdout
