import csv
from pathlib import Path

from rag_project.diagnostics.csv_adapter import load_dataset_from_csv


def _write_rows(path: Path) -> None:
    rows = [
        {
            "sample_id": "correct_001",
            "split": "correct",
            "action_type": "forehand_clear",
            "outcome_label": "low_speed",
            "time": "0.0",
            "event_impact": "0.2",
            "event_acceleration_start": "0.1",
            "joint_trunk_rotation": "0",
            "joint_forearm_pronation": "0",
            "muscle_external_oblique": "0.1",
        },
        {
            "sample_id": "correct_001",
            "split": "correct",
            "action_type": "forehand_clear",
            "outcome_label": "low_speed",
            "time": "0.1",
            "event_impact": "0.2",
            "event_acceleration_start": "0.1",
            "joint_trunk_rotation": "20",
            "joint_forearm_pronation": "10",
            "muscle_external_oblique": "0.5",
        },
        {
            "sample_id": "correct_001",
            "split": "correct",
            "action_type": "forehand_clear",
            "outcome_label": "low_speed",
            "time": "0.2",
            "event_impact": "0.2",
            "event_acceleration_start": "0.1",
            "joint_trunk_rotation": "42",
            "joint_forearm_pronation": "30",
            "muscle_external_oblique": "0.8",
        },
        {
            "sample_id": "eval_001",
            "split": "eval",
            "action_type": "forehand_clear",
            "outcome_label": "ball_high_not_far",
            "time": "0.0",
            "event_impact": "0.2",
            "event_acceleration_start": "0.1",
            "joint_trunk_rotation": "0",
            "joint_forearm_pronation": "0",
            "muscle_external_oblique": "0.1",
        },
        {
            "sample_id": "eval_001",
            "split": "eval",
            "action_type": "forehand_clear",
            "outcome_label": "ball_high_not_far",
            "time": "0.1",
            "event_impact": "0.2",
            "event_acceleration_start": "0.1",
            "joint_trunk_rotation": "10",
            "joint_forearm_pronation": "5",
            "muscle_external_oblique": "0.2",
        },
        {
            "sample_id": "eval_001",
            "split": "eval",
            "action_type": "forehand_clear",
            "outcome_label": "ball_high_not_far",
            "time": "0.2",
            "event_impact": "0.2",
            "event_acceleration_start": "0.1",
            "joint_trunk_rotation": "25",
            "joint_forearm_pronation": "12",
            "muscle_external_oblique": "0.3",
        },
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_load_dataset_from_csv_groups_rows_into_diagnostic_samples(tmp_path: Path):
    csv_path = tmp_path / "simulation.csv"
    _write_rows(csv_path)

    dataset = load_dataset_from_csv(csv_path, dataset_id="csv_forehand_clear")

    assert dataset.dataset_id == "csv_forehand_clear"
    assert len(dataset.correct_samples) == 1
    assert len(dataset.eval_samples) == 1
    assert dataset.correct_samples[0].time == [0.0, 0.1, 0.2]
    assert dataset.correct_samples[0].joint_angles["trunk_rotation"] == [0.0, 20.0, 42.0]
    assert dataset.eval_samples[0].muscle_activation["external_oblique"] == [0.1, 0.2, 0.3]
    assert dataset.eval_samples[0].events["impact"] == 0.2


def test_load_dataset_from_csv_can_round_trip_into_batch_diagnosis(tmp_path: Path):
    from rag_project.diagnostics.batch import run_batch_diagnosis_dataset
    from rag_project.knowledge.evidence_index import EvidenceChunk

    csv_path = tmp_path / "simulation.csv"
    _write_rows(csv_path)
    dataset = load_dataset_from_csv(csv_path)
    evidence = [
        EvidenceChunk(
            chunk_id="CLEAR_ZHAO_LOWER_LIMB::1",
            source_id="CLEAR_ZHAO_LOWER_LIMB",
            title="Lower Limb Movement on the Backcourt Forehand Clear Stroke",
            source_class="full_text_html",
            artifact_path="zhao.html",
            text="Forehand clear uses lower limb movement and trunk coordination.",
            token_count=8,
            evidence_level="direct_biomechanics_forehand_clear",
            score=2.0,
        )
    ]

    result = run_batch_diagnosis_dataset(dataset, evidence_chunks=evidence)

    assert result["summary"]["evaluated_samples"] == 1
    assert result["reports"][0]["sample_id"] == "eval_001"
    assert result["reports"][0]["correction_plan"]


def test_batch_cli_accepts_csv_dataset(tmp_path: Path):
    import json
    import subprocess
    import sys

    csv_path = tmp_path / "simulation.csv"
    output_dir = tmp_path / "out"
    _write_rows(csv_path)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "rag_project.diagnostics.batch",
            "--csv-dataset",
            str(csv_path),
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
    assert summary["evaluated_samples"] == 1
    assert (output_dir / "diagnosis_reports.json").exists()


def test_example_simulation_csv_matches_adapter_contract(tmp_path: Path):
    import json
    import subprocess
    import sys

    csv_path = Path("rag_project/examples/forehand_clear_simulation.csv")
    dataset = load_dataset_from_csv(csv_path)
    output_dir = tmp_path / "example_csv_out"

    assert len(dataset.correct_samples) == 2
    assert len(dataset.eval_samples) == 1

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "rag_project.diagnostics.batch",
            "--csv-dataset",
            str(csv_path),
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
    assert summary["evaluated_samples"] == 1
    assert (output_dir / "reports" / "eval_ball_high_not_far.md").exists()
