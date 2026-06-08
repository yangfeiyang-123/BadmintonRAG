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
def test_deviation_includes_correct_template_range():
    template = build_correct_template("correct", [correct_sample("a"), correct_sample("b")])
    report = diagnose_sample(poor_sample(), template)
    trunk = next(deviation for deviation in report.key_deviations if deviation.feature == "trunk_rotation_peak")

    assert trunk.template_lower_bound < trunk.template_value < trunk.template_upper_bound
    assert trunk.template_std >= 0
    assert trunk.threshold_source == "small_sample_initial_threshold"


def test_deviation_identifies_joint_or_muscle_signal():
    template = build_correct_template("correct", [correct_sample("a"), correct_sample("b")])
    report = diagnose_sample(poor_sample(), template)
    trunk = next(deviation for deviation in report.key_deviations if deviation.feature == "trunk_rotation_peak")
    oblique = next(
        deviation for deviation in report.key_deviations if deviation.feature == "external_oblique_activation_peak"
    )

    assert trunk.feature_group == "joint_angle"
    assert trunk.signal_name == "trunk_rotation"
    assert oblique.feature_group == "muscle_activation"
    assert oblique.signal_name == "external_oblique"


def test_diagnosis_includes_structured_correction_plan():
    template = build_correct_template("correct", [correct_sample("a"), correct_sample("b")])
    report = diagnose_sample(poor_sample(), template)

    assert report.correction_plan
    trunk_action = next(action for action in report.correction_plan if action.target_signal == "trunk_rotation")
    oblique_action = next(action for action in report.correction_plan if action.target_signal == "external_oblique")

    assert trunk_action.feature_group == "joint_angle"
    assert trunk_action.target_feature == "trunk_rotation_peak"
    assert trunk_action.goal
    assert trunk_action.drill
    assert trunk_action.validation_metric == "bring_observed_value_inside_template_range"
    assert oblique_action.feature_group == "muscle_activation"


def test_diagnosis_links_deviations_to_outcome_mechanisms_and_correction_focus():
    template = build_correct_template("correct", [correct_sample("a"), correct_sample("b")])
    report = diagnose_sample(poor_sample(), template)

    assert report.explanation_links
    trunk_link = next(link for link in report.explanation_links if link.signal_name == "trunk_rotation")

    assert trunk_link.outcome_label == "ball_high_not_far"
    assert trunk_link.feature == "trunk_rotation_peak"
    assert trunk_link.feature_group == "joint_angle"
    assert trunk_link.deviation_direction == "below_template"
    assert trunk_link.mechanism
    assert trunk_link.rationale
    assert trunk_link.correction_focus
    assert "trunk_rotation_peak" in trunk_link.evidence_query


def test_diagnosis_evidence_queries_include_feature_specific_explanation_queries():
    template = build_correct_template("correct", [correct_sample("a"), correct_sample("b")])
    report = diagnose_sample(poor_sample(), template)

    assert any("trunk_rotation_peak" in query for query in report.evidence_queries)
    assert any("external_oblique_activation_peak" in query for query in report.evidence_queries)
