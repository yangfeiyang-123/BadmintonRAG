from rag_project.diagnostics.explain import render_diagnosis_markdown
from rag_project.diagnostics.schemas import DiagnosisReport, ExplanationLink, OutcomeLabel


def test_renders_outcome_deviation_explanation_links():
    report = DiagnosisReport(
        sample_id="clear_002",
        action_type="forehand_clear",
        outcome_label=OutcomeLabel.BALL_HIGH_NOT_FAR,
        primary_diagnosis="forward momentum insufficient",
        diagnostic_confidence="medium",
        explanation_links=[
            ExplanationLink(
                outcome_label="ball_high_not_far",
                feature="trunk_rotation_peak",
                signal_name="trunk_rotation",
                feature_group="joint_angle",
                phase="acceleration",
                severity="high",
                deviation_direction="below_template",
                mechanism="trunk-led forward momentum is insufficient",
                rationale="trunk_rotation_peak is lower than the correct-template range during acceleration.",
                correction_focus="Move trunk_rotation back toward 36-46 degree.",
                evidence_query="badminton forehand clear ball_high_not_far trunk_rotation_peak",
            )
        ],
    )

    markdown = render_diagnosis_markdown(report, [])

    assert "## Outcome-Deviation Explanation Links" in markdown
    assert "trunk_rotation_peak -> ball_high_not_far" in markdown
    assert "trunk-led forward momentum is insufficient" in markdown
    assert "Move trunk_rotation back toward 36-46 degree." in markdown

