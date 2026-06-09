from __future__ import annotations

from rag_project.diagnostics.schemas import DiagnosisReport
from rag_project.diagnostics.zh_labels import (
    zh_direction,
    zh_feature,
    zh_group,
    zh_outcome,
    zh_phase,
    zh_severity,
    zh_signal,
    zh_unit,
)
from rag_project.knowledge.concept_kb import evidence_layer_label, load_crosswalk, resolve_source_url
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
            unit_zh = zh_unit(deviation.unit)
            lines.append(
                "- "
                f"「{zh_feature(deviation.feature)}」（{zh_phase(deviation.phase)}阶段）："
                f"{zh_group(deviation.feature_group)}·{zh_signal(deviation.signal_name)}，"
                f"{zh_direction(deviation.direction)} / 严重度{zh_severity(deviation.severity)}，"
                f"观测值 {deviation.observed_value:.4g} {unit_zh}，"
                f"模板均值 {deviation.template_value:.4g} {unit_zh}，"
                f"正确模板范围 {deviation.template_lower_bound:.4g}-"
                f"{deviation.template_upper_bound:.4g} {unit_zh}，"
                f"标准差 {deviation.template_std:.4g}。"
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
                f"「{zh_feature(action.target_feature)}」"
                f"（{zh_group(action.feature_group)}·{zh_signal(action.target_signal)}）："
                f"阶段 {zh_phase(action.phase)}，严重度 {zh_severity(action.severity)}。"
                f"目标：{action.goal} 训练：{action.drill} 验证：使观测值回到正确模板范围。"
            )
    else:
        lines.append("- 当前诊断没有生成结构化改进动作。")

    lines.extend(["", "## 结果-偏差解释链", ""])
    if report.explanation_links:
        for link in report.explanation_links:
            lines.append(
                "- "
                f"「{zh_feature(link.feature)}」→ 后果「{zh_outcome(link.outcome_label)}」："
                f"{zh_group(link.feature_group)}·{zh_signal(link.signal_name)}，"
                f"{zh_phase(link.phase)}阶段，严重度{zh_severity(link.severity)}，"
                f"{zh_direction(link.deviation_direction)}；"
                f"机制：{link.mechanism}；说明：{link.rationale}；纠正：{link.correction_focus}"
            )
    else:
        lines.append("- 当前诊断没有生成结果-偏差解释链。")

    lines.extend(["", "## 文献证据", ""])
    if evidence:
        crosswalk = load_crosswalk()
        for chunk in evidence:
            # Render [Sxx] citations (concept chunks carry source_ids; legacy chunks
            # are translated from their string id via the crosswalk) + 中文证据层标签.
            sids = list(chunk.source_ids) or [crosswalk.to_package(chunk.source_id)]
            cite = "".join(f"[{sid}]" for sid in sids)
            lines.append(
                f"- {cite} | {evidence_layer_label(chunk.evidence_level)} | score={chunk.score:.2f}"
            )
            lines.append(f"  - 标题：{chunk.title}")
            # Original-source URL(s) so the reader can open the literature itself.
            for sid in sids:
                url = resolve_source_url(sid) or resolve_source_url(chunk.source_id)
                if url:
                    lines.append(f"  - 原文 {sid}：{url}")
            lines.append(f"  - 摘要片段：{_clip(chunk.text)}")
    else:
        lines.append("- 当前 evidence index 没有检索到可用证据；请扩展文献正文抽取或调整查询词。")

    lines.extend(
        [
            "",
            "## 证据边界",
            "",
            "- 证据按层级标注：直接高远球证据 > 头顶多击球 > 杀球/EMG/方法学类比；杀球类比仅作机制参考，不作高远球定量真值。",
            "- 动作轨迹拟合度高不能证明肌肉激活唯一正确；肌骨模型存在力分配多解，仅做生理合理性验证，不把推断写成确定的肌肉激活事实。",
            "- 不考虑手和手指发力；肌群层不展开手指外在肌、握拍压力。",
            "- 上肢远端段（肩内旋/肘伸展/前臂旋前/腕屈）峰值高度重叠，命名顺序≠峰值时序，不给唯一确定先后。",
        ]
    )

    return "\n".join(lines) + "\n"
