import pytest

from rag_project.diagnostics.schemas import (
    DiagnosticSample,
    OutcomeLabel,
    TimeSeriesValidationError,
)


def valid_payload():
    return {
        "sample_id": "clear_001",
        "action_type": "forehand_clear",
        "outcome_label": "ball_high_not_far",
        "time": [0.0, 0.1, 0.2],
        "events": {"impact": 0.1},
        "joint_angles": {"trunk_rotation": [10.0, 20.0, 30.0]},
        "muscle_activation": {"anterior_deltoid": [0.1, 0.3, 0.2]},
    }


def test_valid_sample_loads():
    sample = DiagnosticSample.from_dict(valid_payload())
    assert sample.sample_id == "clear_001"
    assert sample.outcome_label == OutcomeLabel.BALL_HIGH_NOT_FAR
    assert sample.series_length == 3


def test_rejects_unknown_action_type():
    payload = valid_payload()
    payload["action_type"] = "smash"
    with pytest.raises(TimeSeriesValidationError, match="action_type"):
        DiagnosticSample.from_dict(payload)


def test_rejects_missing_impact():
    payload = valid_payload()
    payload["events"] = {}
    with pytest.raises(TimeSeriesValidationError, match="impact"):
        DiagnosticSample.from_dict(payload)


def test_rejects_mismatched_series_lengths():
    payload = valid_payload()
    payload["joint_angles"]["trunk_rotation"] = [1.0, 2.0]
    with pytest.raises(TimeSeriesValidationError, match="length"):
        DiagnosticSample.from_dict(payload)
