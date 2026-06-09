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
                goal="提高 trunk_rotation 到正确模板范围。",
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
                mechanism="trunk-led forward momentum is insufficient",
                rationale="trunk_rotation_peak is lower than the correct-template range during acceleration.",
                correction_focus="Move trunk_rotation back toward 36-46 degree.",
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
    assert "trunk_rotation_peak" in markdown
    assert "CLEAR_ZHAO_LOWER_LIMB" in markdown
    # INTEG-06: evidence is cited as [Sxx] (legacy id translated via crosswalk) with the evidence-layer label.
    assert "[S06]" in markdown
    assert "direct_biomechanics_forehand_clear" in markdown
    assert "正确模板范围" in markdown
    assert "36" in markdown
    assert "46" in markdown
    assert "joint_angle/trunk_rotation" in markdown
    assert "## 结构化改进计划" in markdown
    assert "bring_observed_value_inside_template_range" in markdown
