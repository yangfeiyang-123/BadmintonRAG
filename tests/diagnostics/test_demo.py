import json
from pathlib import Path

from rag_project.diagnostics.run_forehand_clear_demo import run_demo


def test_demo_outputs_three_reports(tmp_path: Path):
    output = tmp_path / "reports.json"
    run_demo(output)
    reports = json.loads(output.read_text(encoding="utf-8"))
    assert len(reports) == 3
    assert {report["outcome_label"] for report in reports} == {
        "ball_high_not_far",
        "low_speed",
        "uncoordinated_power",
    }
    assert all(report["key_deviations"] for report in reports)
