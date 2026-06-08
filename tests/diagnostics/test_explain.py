from rag_project.diagnostics.explain import render_diagnosis_markdown
from rag_project.diagnostics.schemas import Deviation, DiagnosisReport, OutcomeLabel
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
            )
        ],
        likely_mechanisms=["躯干带动不足"],
        correction_suggestions=["优先练习蹬地、转髋、转体后再带动肩肘腕释放。"],
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
    assert "full_text_html" in markdown
    assert "direct_biomechanics_forehand_clear" in markdown
