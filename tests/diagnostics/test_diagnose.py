from rag_project.diagnostics.diagnose import diagnose_sample
from rag_project.diagnostics.schemas import DiagnosticSample
from rag_project.diagnostics.templates import build_correct_template


def correct_sample(sample_id):
    return DiagnosticSample.from_dict(
        {
            "sample_id": sample_id,
            "action_type": "forehand_clear",
            "outcome_label": "low_speed",
            "time": [0.0, 0.1, 0.2, 0.3],
            "events": {"acceleration_start": 0.1, "impact": 0.2, "follow_through_end": 0.3},
            "joint_angles": {
                "trunk_rotation": [0.0, 20.0, 42.0, 35.0],
                "forearm_pronation": [0.0, 10.0, 30.0, 32.0],
            },
            "muscle_activation": {
                "external_oblique": [0.1, 0.5, 0.8, 0.3],
                "anterior_deltoid": [0.1, 0.3, 0.5, 0.2],
            },
        }
    )


def poor_sample():
    return DiagnosticSample.from_dict(
        {
            "sample_id": "poor_clear",
            "action_type": "forehand_clear",
            "outcome_label": "ball_high_not_far",
            "time": [0.0, 0.1, 0.2, 0.3],
            "events": {"acceleration_start": 0.1, "impact": 0.2, "follow_through_end": 0.3},
            "joint_angles": {
                "trunk_rotation": [0.0, 10.0, 25.0, 24.0],
                "forearm_pronation": [0.0, 5.0, 12.0, 18.0],
            },
            "muscle_activation": {
                "external_oblique": [0.1, 0.2, 0.3, 0.2],
                "anterior_deltoid": [0.7, 0.6, 0.3, 0.2],
            },
        }
    )


def test_diagnoses_ball_high_not_far_with_relevant_deviations():
    template = build_correct_template("correct", [correct_sample("a"), correct_sample("b")])
    report = diagnose_sample(poor_sample(), template)
    assert report.primary_diagnosis == "击球阶段向前动量不足，末端释放效率偏低"
    names = {deviation.feature for deviation in report.key_deviations}
    assert "trunk_rotation_peak" in names
    assert "forearm_pronation_peak" in names
    assert "躯干带动不足" in report.likely_mechanisms
