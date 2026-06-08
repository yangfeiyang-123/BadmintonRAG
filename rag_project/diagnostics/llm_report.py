from __future__ import annotations

import json
from typing import Protocol

from rag_project.diagnostics.explain import render_diagnosis_markdown
from rag_project.diagnostics.schemas import DiagnosisReport
from rag_project.knowledge.evidence_index import EvidenceChunk


class ChatClient(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> str:
        ...


def _evidence_payload(evidence: list[EvidenceChunk]) -> list[dict[str, object]]:
    return [
        {
            "source_id": chunk.source_id,
            "title": chunk.title,
            "source_class": chunk.source_class,
            "evidence_level": chunk.evidence_level,
            "score": chunk.score,
            "snippet": " ".join(chunk.text.split())[:700],
        }
        for chunk in evidence
    ]


def _diagnosis_payload(report: DiagnosisReport) -> dict[str, object]:
    return {
        "sample_id": report.sample_id,
        "action_type": report.action_type,
        "outcome_label": report.outcome_label.name,
        "outcome_value": report.outcome_label.value,
        "primary_diagnosis": report.primary_diagnosis,
        "diagnostic_confidence": report.diagnostic_confidence,
        "key_deviations": [
            {
                "feature": deviation.feature,
                "phase": deviation.phase,
                "direction": deviation.direction,
                "severity": deviation.severity,
                "observed_value": deviation.observed_value,
                "template_value": deviation.template_value,
                "unit": deviation.unit,
                "interpretation": deviation.interpretation,
            }
            for deviation in report.key_deviations
        ],
        "likely_mechanisms": report.likely_mechanisms,
        "correction_suggestions": report.correction_suggestions,
        "correction_plan": [
            {
                "target_feature": action.target_feature,
                "target_signal": action.target_signal,
                "feature_group": action.feature_group,
                "phase": action.phase,
                "severity": action.severity,
                "goal": action.goal,
                "drill": action.drill,
                "validation_metric": action.validation_metric,
            }
            for action in report.correction_plan
        ],
        "evidence_queries": report.evidence_queries,
    }


def build_diagnostic_messages(report: DiagnosisReport, evidence: list[EvidenceChunk]) -> list[dict[str, str]]:
    system = (
        "你是羽毛球正手高远球动作诊断助手。"
        "只能基于用户提供的诊断标签、关节角/肌肉激活偏差摘要和文献证据回答，不要编造数据、论文或来源。"
        "输出必须包含：错误判断、错在哪里、可能发力/肌肉激活机制、改进建议、证据边界。"
        "涉及肌肉激活时，如果证据来自运动学或动力链推断而非直接 EMG，应明确写成机制推断。"
        "引用文献时使用 source_id。"
    )
    user_payload = {
        "task": "生成面向教练和研究者的正手高远球诊断报告",
        "diagnosis": _diagnosis_payload(report),
        "evidence": _evidence_payload(evidence),
        "output_language": "zh-CN",
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, indent=2)},
    ]


def generate_diagnostic_report(
    report: DiagnosisReport, evidence: list[EvidenceChunk], client: ChatClient | None = None
) -> str:
    if client is None:
        return render_diagnosis_markdown(report, evidence)
    return client.complete(build_diagnostic_messages(report, evidence))
