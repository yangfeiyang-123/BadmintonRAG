import json
from pathlib import Path

from rag_project.diagnostics.dataset import load_diagnostic_dataset


def test_load_diagnostic_dataset_reads_correct_and_eval_samples(tmp_path: Path):
    dataset_path = tmp_path / "dataset.json"
    sample = {
        "sample_id": "correct_clear_001",
        "action_type": "forehand_clear",
        "outcome_label": "low_speed",
        "time": [0.0, 0.1, 0.2],
        "events": {"impact": 0.1},
        "joint_angles": {"trunk_rotation": [0.0, 20.0, 42.0]},
        "muscle_activation": {"external_oblique": [0.1, 0.5, 0.8]},
    }
    eval_sample = dict(sample, sample_id="eval_clear_001", outcome_label="ball_high_not_far")
    dataset_path.write_text(
        json.dumps(
            {
                "dataset_id": "forehand_clear_small",
                "action_type": "forehand_clear",
                "correct_samples": [sample],
                "eval_samples": [eval_sample],
            }
        ),
        encoding="utf-8",
    )

    dataset = load_diagnostic_dataset(dataset_path)

    assert dataset.dataset_id == "forehand_clear_small"
    assert dataset.action_type == "forehand_clear"
    assert dataset.correct_samples[0].sample_id == "correct_clear_001"
    assert dataset.eval_samples[0].outcome_label.value == "ball_high_not_far"
