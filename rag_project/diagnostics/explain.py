from __future__ import annotations

from rag_project.diagnostics.schemas import DiagnosisReport
from rag_project.knowledge.evidence_index import EvidenceChunk


def _clip(text: str, limit: int = 260) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def render_diagnosis_markdown(report: DiagnosisReport, evidence: list[EvidenceChunk]) -> str:
    lines: list[str] = [
        f"# 正手高远球诊断报告：{report.sample_id}",
        "",
        "## 诊断结论",
        "",
        f"- 后果标签：`{report.outcome_label.value}`",
        f"- 主诊断：{report.primary_diagnosis}",
        f"- 诊断置信度：`{report.diagnostic_confidence}`",
        "",
        "## 关键偏差",
        "",
    ]

    if report.key_deviations:
        for deviation in report.key_deviations:
            lines.append(
                "- "
                f"`{deviation.feature}`（{deviation.phase}）："
                f"{deviation.feature_group}/{deviation.signal_name}，"
                f"{deviation.direction} / {deviation.severity}，"
                f"观测值 {deviation.observed_value:.4g} {deviation.unit}，"
                f"模板均值 {deviation.template_value:.4g} {deviation.unit}，"
                f"正确模板范围 {deviation.template_lower_bound:.4g}-"
                f"{deviation.template_upper_bound:.4g} {deviation.unit}，"
                f"std={deviation.template_std:.4g}，threshold={deviation.threshold_source}。"
                f"{deviation.interpretation}"
            )
    else:
        lines.append("- 未检测到与该后果标签直接相关的模板外偏差。")

    lines.extend(["", "## 可能机制", ""])
    for mechanism in report.likely_mechanisms:
        lines.append(f"- {mechanism}")

    lines.extend(["", "## 改进建议", ""])
    for suggestion in report.correction_suggestions:
        lines.append(f"- {suggestion}")

    lines.extend(["", "## 结构化改进计划", ""])
    if report.correction_plan:
        for action in report.correction_plan:
            lines.append(
                "- "
                f"`{action.target_feature}`：{action.feature_group}/{action.target_signal}，"
                f"phase={action.phase}，severity={action.severity}，"
                f"goal={action.goal}，drill={action.drill}，"
                f"validation={action.validation_metric}"
            )
    else:
        lines.append("- 当前诊断没有生成结构化改进动作。")

    lines.extend(["", "## Outcome-Deviation Explanation Links", ""])
    if report.explanation_links:
        for link in report.explanation_links:
            lines.append(
                "- "
                f"`{link.feature} -> {link.outcome_label}`: "
                f"{link.feature_group}/{link.signal_name}, phase={link.phase}, "
                f"severity={link.severity}, direction={link.deviation_direction}; "
                f"mechanism={link.mechanism}; rationale={link.rationale}; "
                f"correction_focus={link.correction_focus}; evidence_query={link.evidence_query}"
            )
    else:
        lines.append("- No structured explanation links were generated.")

    lines.extend(["", "## 文献证据", ""])
    if evidence:
        for chunk in evidence:
            lines.append(
                f"- `{chunk.source_id}` | `{chunk.source_class}` | evidence={chunk.evidence_level} | score={chunk.score:.2f}"
            )
            lines.append(f"  - 标题：{chunk.title}")
            lines.append(f"  - 文件：`{chunk.artifact_path}`")
            lines.append(f"  - 摘要片段：{_clip(chunk.text)}")
    else:
        lines.append("- 当前 evidence index 没有检索到可用证据；请扩展文献正文抽取或调整查询词。")

    lines.extend(
        [
            "",
            "## 证据边界",
            "",
            "- 本报告优先使用 `official_manual`、`full_text_html` 和 `full_text_pdf` 来源。",
            "- 如果证据来自运动学/动力学研究而非 EMG，报告只做机制解释，不把推断写成确定的肌肉激活事实。",
        ]
    )

    return "\n".join(lines) + "\n"
