from rag_project.diagnostics.explain import render_diagnosis_markdown
from rag_project.diagnostics.schemas import CorrectionAction, Deviation, DiagnosisReport, ExplanationLink, OutcomeLabel
from rag_project.knowledge.evidence_index import EvidenceChunk


def test_renders_markdown_with_evidence_citations():
    report = DiagnosisReport(
        sample_id="clear_001",
        action_type="forehand_clear",
        outcome_label=OutcomeLabel.BALL_HIGH_NOT_FAR,
        primary_diagnosis="击球阶段向前动量不足，末端释放效率偏低",
        diagnostic_confidence="medium",
        key_deviations=[
            Deviation(
                feature="trunk_rotation_peak",
                phase="acceleration",
                direction="below_template",
                severity="high",
                observed_value=25.0,
                template_value=42.0,
                unit="degree",
                interpretation="躯干旋转峰值低于正确模板。",
                template_lower_bound=36.0,
                template_upper_bound=46.0,
                template_std=2.0,
                threshold_source="small_sample_initial_threshold",
                feature_group="joint_angle",
                signal_name="trunk_rotation",
            )
        ],
        likely_mechanisms=["躯干带动不足"],
        correction_suggestions=["优先练习蹬地、转髋、转体后再带动肩肘腕释放。"],
        correction_plan=[
            CorrectionAction(
                target_feature="trunk_rotation_peak",
                target_signal="trunk_rotation",
                feature_group="joint_angle",
                phase="acceleration",
                severity="high",
                goal="提高「躯干旋转」到正确模板范围。",
                drill="练习蹬地、转髋、转体到击球窗口的连续释放。",
                validation_metric="bring_observed_value_inside_template_range",
            )
        ],
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
        evidence_queries=["badminton forehand clear trunk rotation"],
    )
    evidence = [
        EvidenceChunk(
            chunk_id="CLEAR_ZHAO_LOWER_LIMB::1",
            source_id="CLEAR_ZHAO_LOWER_LIMB",
            title="Lower Limb Movement on the Backcourt Forehand Clear Stroke",
            source_class="full_text_html",
            artifact_path="rag_project/sources/raw/html/CLEAR_ZHAO_LOWER_LIMB.html",
            text="Badminton forehand clear stroke uses lower limb movement and trunk coordination.",
            token_count=10,
            evidence_level="direct_biomechanics_forehand_clear",
            score=3.0,
        )
    ]

    markdown = render_diagnosis_markdown(report, evidence)

    assert "## 诊断结论" in markdown
    assert "击球阶段向前动量不足" in markdown
    # Structured output is Chinese: joint/muscle names and field labels translated.
    assert "躯干旋转·峰值" in markdown
    assert "关节角·躯干旋转" in markdown
    assert "前挥加速" in markdown
    assert "低于正确模板" in markdown
    assert "正确模板范围" in markdown and "36" in markdown and "46" in markdown
    assert "## 结构化改进计划" in markdown
    assert "使观测值回到正确模板范围" in markdown
    assert "## 结果-偏差解释链" in markdown
    # INTEG-06: [Sxx] citation + Chinese evidence-layer label.
    assert "[S06]" in markdown
    assert "直接高远球生物力学" in markdown
    # Task 1: original-source URL is shown so the reader can open the literature.
    assert "原文 S06" in markdown and "https://" in markdown
    # No English joint/muscle identifiers or raw field names leak into the structured output.
    assert "trunk_rotation_peak" not in markdown
    assert "joint_angle/" not in markdown
    assert "below_template" not in markdown
    assert "evidence_query" not in markdown
