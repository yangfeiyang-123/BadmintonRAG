from rag_project.diagnostics.explain import render_diagnosis_markdown
from rag_project.diagnostics.schemas import DiagnosisReport, ExplanationLink, OutcomeLabel


def test_renders_outcome_deviation_explanation_links():
    report = DiagnosisReport(
        sample_id="clear_002",
        action_type="forehand_clear",
        outcome_label=OutcomeLabel.BALL_HIGH_NOT_FAR,
        primary_diagnosis="击球阶段向前动量不足",
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
                mechanism="躯干带动不足",
                rationale="躯干旋转·峰值在前挥加速阶段低于正确模板范围。",
                correction_focus="把「躯干旋转」的偏差调回 36-46 度。",
                evidence_query="badminton forehand clear ball_high_not_far trunk_rotation_peak",
            )
        ],
    )

    markdown = render_diagnosis_markdown(report, [])

    # Section renamed to Chinese; joint/muscle names and labels translated.
    assert "## 结果-偏差解释链" in markdown
    assert "躯干旋转·峰值" in markdown
    assert "后果「球过高不够远」" in markdown
    assert "关节角·躯干旋转" in markdown
    assert "前挥加速" in markdown
    assert "躯干带动不足" in markdown
    assert "把「躯干旋转」的偏差调回" in markdown
    # No English raw identifiers or the old English section title.
    assert "Outcome-Deviation Explanation Links" not in markdown
    assert "trunk_rotation_peak ->" not in markdown
    assert "evidence_query" not in markdown
