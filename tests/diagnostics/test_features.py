from rag_project.diagnostics.features import extract_features
from rag_project.diagnostics.schemas import DiagnosticSample


def sample_payload():
    return {
        "sample_id": "clear_001",
        "action_type": "forehand_clear",
        "outcome_label": "ball_high_not_far",
        "time": [0.0, 0.1, 0.2, 0.3],
        "events": {"backswing_start": 0.0, "acceleration_start": 0.1, "impact": 0.2, "follow_through_end": 0.3},
        "joint_angles": {
            "trunk_rotation": [0.0, 20.0, 40.0, 30.0],
            "elbow_flexion": [100.0, 90.0, 70.0, 80.0],
        },
        "muscle_activation": {
            "anterior_deltoid": [0.1, 0.8, 0.4, 0.2],
            "forearm_pronator_group": [0.1, 0.2, 0.7, 0.4],
        },
    }


def test_extracts_peak_and_peak_time_relative_to_impact():
    sample = DiagnosticSample.from_dict(sample_payload())
    features = extract_features(sample)
    assert features["trunk_rotation_peak"].value == 40.0
    assert features["trunk_rotation_peak_time_relative_to_impact"].value == 0.0
    assert features["anterior_deltoid_activation_peak"].value == 0.8
    assert features["anterior_deltoid_activation_peak_time_relative_to_impact"].value == -0.1


def test_extracts_velocity_peak_for_joint_angles():
    sample = DiagnosticSample.from_dict(sample_payload())
    features = extract_features(sample)
    assert features["trunk_rotation_velocity_peak"].value == 200.0
