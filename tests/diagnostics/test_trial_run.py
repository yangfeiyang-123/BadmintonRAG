import json
import subprocess
import sys
from pathlib import Path


def test_trial_run_cli_writes_contract_diagnosis_and_index(tmp_path: Path):
    output_dir = tmp_path / "trial"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "rag_project.diagnostics.trial_run",
            "--csv-dataset",
            "rag_project/examples/forehand_clear_simulation.csv",
            "--output-dir",
            str(output_dir),
            "--retrieval-backend",
            "keyword",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    summary = json.loads(completed.stdout)

    assert summary["passed"] is True
    assert summary["contract_report"] == str(output_dir / "contract_report.json")
    assert summary["diagnosis_json"] == str(output_dir / "diagnosis_reports.json")
    assert summary["report_index"] == str(output_dir / "report_index.html")
    assert summary["evaluated_samples"] == 1
    assert (output_dir / "contract_report.json").exists()
    assert (output_dir / "diagnosis_reports.json").exists()
    assert (output_dir / "summary.json").exists()
    assert (output_dir / "reports" / "eval_ball_high_not_far.md").exists()
    index_html = (output_dir / "report_index.html").read_text(encoding="utf-8")
    assert "BadmintonRAG Trial Run" in index_html
    assert "eval_ball_high_not_far.md" in index_html
    assert "contract_report.json" in index_html


def test_trial_run_cli_fails_before_diagnosis_on_bad_contract(tmp_path: Path):
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text(
        "\n".join(
            [
                "sample_id,split,action_type,outcome_label,time,event_impact,joint_trunk_rotation",
                "eval_001,eval,forehand_clear,only_high,0.0,0.2,0",
            ]
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "trial"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "rag_project.diagnostics.trial_run",
            "--csv-dataset",
            str(csv_path),
            "--output-dir",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "CSV requires at least one muscle_ signal column" in completed.stderr
    assert not (output_dir / "diagnosis_reports.json").exists()

