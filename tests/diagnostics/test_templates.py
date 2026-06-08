from rag_project.diagnostics.schemas import DiagnosticSample
from rag_project.diagnostics.templates import build_correct_template


def make_sample(sample_id, trunk_peak):
    return DiagnosticSample.from_dict(
        {
            "sample_id": sample_id,
            "action_type": "forehand_clear",
            "outcome_label": "low_speed",
            "time": [0.0, 0.1, 0.2],
            "events": {"impact": 0.2, "acceleration_start": 0.1},
            "joint_angles": {"trunk_rotation": [0.0, trunk_peak / 2.0, trunk_peak]},
            "muscle_activation": {"anterior_deltoid": [0.1, 0.2, 0.3]},
        }
    )


def test_builds_template_bounds_from_correct_samples():
    template = build_correct_template("forehand_clear_correct_v1", [make_sample("a", 40.0), make_sample("b", 44.0)])
    feature = template.features["trunk_rotation_peak"]
    assert template.sample_count == 2
    assert feature.mean == 42.0
    assert feature.lower_bound < 42.0
    assert feature.upper_bound > 42.0
