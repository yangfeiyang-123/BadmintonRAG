from rag_project.diagnostics.llm_report import build_diagnostic_messages, generate_diagnostic_report
from rag_project.diagnostics.schemas import Deviation, DiagnosisReport, OutcomeLabel
from rag_project.knowledge.evidence_index import EvidenceChunk


class RecordingClient:
    def __init__(self):
        self.messages = None

    def complete(self, messages):
        self.messages = messages
        return "LLM report text"


def _report():
    return DiagnosisReport(
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
                interpretation="躯干旋转峰值低于正确动作模板。",
            )
        ],
        likely_mechanisms=["躯干带动不足"],
        correction_suggestions=["优先练习蹬地、转髋、转体后再带动肩肘腕释放。"],
        evidence_queries=["badminton forehand clear trunk rotation"],
    )


def _evidence():
    return [
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


def test_build_diagnostic_messages_ground_llm_in_diagnosis_and_evidence():
    messages = build_diagnostic_messages(_report(), _evidence())
    combined = "\n".join(message["content"] for message in messages)

    assert messages[0]["role"] == "system"
    assert "不要编造" in combined
    assert "BALL_HIGH_NOT_FAR" in combined
    assert "trunk_rotation_peak" in combined
    assert "CLEAR_ZHAO_LOWER_LIMB" in combined
    assert "肌肉激活" in combined


def test_generate_diagnostic_report_uses_client_when_provided():
    client = RecordingClient()

    text = generate_diagnostic_report(_report(), _evidence(), client=client)

    assert text == "LLM report text"
    assert client.messages is not None


def test_generate_diagnostic_report_falls_back_to_markdown_without_client():
    text = generate_diagnostic_report(_report(), _evidence())

    assert "# 正手高远球诊断报告：clear_001" in text
    assert "CLEAR_ZHAO_LOWER_LIMB" in text
