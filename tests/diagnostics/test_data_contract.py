import csv
from pathlib import Path

from rag_project.diagnostics.data_contract import (
    REQUIRED_PREFIXES,
    SimulationContractError,
    SimulationFieldSpec,
    validate_simulation_csv_contract,
)


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_field_spec_documents_machine_readable_prefixes():
    specs = SimulationFieldSpec.default_specs()

    assert [spec.prefix for spec in specs] == ["event_", "joint_", "muscle_"]
    assert REQUIRED_PREFIXES == {"event_", "joint_", "muscle_"}
    assert specs[1].group == "joint_angles"
    assert specs[2].unit_hint == "normalized_0_to_1"


def test_validate_simulation_csv_contract_accepts_real_data_shape(tmp_path: Path):
    csv_path = tmp_path / "simulation.csv"
    _write_csv(
        csv_path,
        [
            {
                "sample_id": "correct_001",
                "split": "correct",
                "action_type": "forehand_clear",
                "outcome_label": "low_speed",
                "time": "0.0",
                "event_impact": "0.2",
                "joint_trunk_rotation": "0",
                "muscle_external_oblique": "0.1",
            },
            {
                "sample_id": "correct_001",
                "split": "correct",
                "action_type": "forehand_clear",
                "outcome_label": "low_speed",
                "time": "0.2",
                "event_impact": "0.2",
                "joint_trunk_rotation": "40",
                "muscle_external_oblique": "0.8",
            },
            {
                "sample_id": "eval_001",
                "split": "eval",
                "action_type": "forehand_clear",
                "outcome_label": "ball_high_not_far",
                "time": "0.0",
                "event_impact": "0.2",
                "joint_trunk_rotation": "0",
                "muscle_external_oblique": "0.1",
            },
            {
                "sample_id": "eval_001",
                "split": "eval",
                "action_type": "forehand_clear",
                "outcome_label": "ball_high_not_far",
                "time": "0.2",
                "event_impact": "0.2",
                "joint_trunk_rotation": "20",
                "muscle_external_oblique": "0.3",
            },
        ],
    )

    report = validate_simulation_csv_contract(csv_path)

    assert report.path == csv_path
    assert report.row_count == 4
    assert report.sample_count == 2
    assert report.correct_sample_count == 1
    assert report.eval_sample_count == 1
    assert report.signal_counts == {"event_": 1, "joint_": 1, "muscle_": 1}
    assert report.outcome_labels == ["ball_high_not_far", "low_speed"]


def test_validate_simulation_csv_contract_rejects_missing_signal_prefix(tmp_path: Path):
    csv_path = tmp_path / "missing_muscle.csv"
    _write_csv(
        csv_path,
        [
            {
                "sample_id": "eval_001",
                "split": "eval",
                "action_type": "forehand_clear",
                "outcome_label": "ball_high_not_far",
                "time": "0.0",
                "event_impact": "0.2",
                "joint_trunk_rotation": "0",
            }
        ],
    )

    try:
        validate_simulation_csv_contract(csv_path)
    except SimulationContractError as exc:
        assert "CSV requires at least one muscle_ signal column" in str(exc)
    else:
        raise AssertionError("Expected missing muscle signal to fail contract validation")


def test_validate_simulation_csv_contract_requires_impact_event(tmp_path: Path):
    csv_path = tmp_path / "missing_impact.csv"
    _write_csv(
        csv_path,
        [
            {
                "sample_id": "correct_001",
                "split": "correct",
                "action_type": "forehand_clear",
                "outcome_label": "low_speed",
                "time": "0.0",
                "event_acceleration_start": "0.1",
                "joint_trunk_rotation": "0",
                "muscle_external_oblique": "0.1",
            },
            {
                "sample_id": "eval_001",
                "split": "eval",
                "action_type": "forehand_clear",
                "outcome_label": "ball_high_not_far",
                "time": "0.0",
                "event_acceleration_start": "0.1",
                "joint_trunk_rotation": "0",
                "muscle_external_oblique": "0.1",
            },
        ],
    )

    try:
        validate_simulation_csv_contract(csv_path)
    except SimulationContractError as exc:
        assert "CSV requires event_impact" in str(exc)
    else:
        raise AssertionError("Expected missing impact event to fail contract validation")


def test_validate_simulation_csv_contract_rejects_unknown_discrete_label(tmp_path: Path):
    csv_path = tmp_path / "bad_label.csv"
    _write_csv(
        csv_path,
        [
            {
                "sample_id": "eval_001",
                "split": "eval",
                "action_type": "forehand_clear",
                "outcome_label": "only_high",
                "time": "0.0",
                "event_impact": "0.2",
                "joint_trunk_rotation": "0",
                "muscle_external_oblique": "0.1",
            }
        ],
    )

    try:
        validate_simulation_csv_contract(csv_path)
    except SimulationContractError as exc:
        assert "Unsupported outcome_label: only_high" in str(exc)
    else:
        raise AssertionError("Expected unknown discrete label to fail contract validation")


def test_validate_simulation_csv_contract_rejects_non_numeric_signal(tmp_path: Path):
    csv_path = tmp_path / "bad_signal.csv"
    _write_csv(
        csv_path,
        [
            {
                "sample_id": "correct_001",
                "split": "correct",
                "action_type": "forehand_clear",
                "outcome_label": "low_speed",
                "time": "0.0",
                "event_impact": "0.2",
                "joint_trunk_rotation": "not-a-number",
                "muscle_external_oblique": "0.1",
            },
            {
                "sample_id": "eval_001",
                "split": "eval",
                "action_type": "forehand_clear",
                "outcome_label": "ball_high_not_far",
                "time": "0.0",
                "event_impact": "0.2",
                "joint_trunk_rotation": "0",
                "muscle_external_oblique": "0.1",
            },
        ],
    )

    try:
        validate_simulation_csv_contract(csv_path)
    except SimulationContractError as exc:
        assert "Row 2 has non-numeric value in joint_trunk_rotation" in str(exc)
    else:
        raise AssertionError("Expected non-numeric signal to fail contract validation")


def test_data_contract_cli_prints_json_summary():
    import json
    import subprocess
    import sys

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "rag_project.diagnostics.data_contract",
            "--csv-dataset",
            "rag_project/examples/forehand_clear_simulation.csv",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    summary = json.loads(completed.stdout)
    assert summary["row_count"] == 12
    assert summary["sample_count"] == 3
    assert summary["correct_sample_count"] == 2
    assert summary["eval_sample_count"] == 1
