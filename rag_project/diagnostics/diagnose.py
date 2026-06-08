from __future__ import annotations

from rag_project.diagnostics.features import extract_features
from rag_project.diagnostics.rules_forehand_clear import OUTCOME_RULES
from rag_project.diagnostics.schemas import (
    CorrectTemplate,
    CorrectionAction,
    Deviation,
    DiagnosisReport,
    DiagnosticSample,
    ExplanationLink,
)


def _severity(observed: float, lower: float, upper: float, std: float) -> str:
    if lower <= observed <= upper:
        return "none"
    if std <= 0:
        width = max(abs(upper - lower), abs((upper + lower) / 2.0) * 0.1, 0.01)
        distance = lower - observed if observed < lower else observed - upper
        if distance > width:
            return "high"
        return "medium"
    distance = min(abs(observed - lower), abs(observed - upper))
    if distance > 2 * std:
        return "high"
    if distance > std:
        return "medium"
    return "low"


def _direction(observed: float, lower: float, upper: float) -> str:
    if observed < lower:
        return "below_template"
    if observed > upper:
        return "above_template"
    return "within_template"


def _matches_rule(feature_name: str, rule_features: list[str]) -> bool:
    return any(token in feature_name for token in rule_features)


def _feature_source(feature_name: str) -> tuple[str, str]:
    if "_activation_" in feature_name:
        return "muscle_activation", feature_name.split("_activation_", maxsplit=1)[0]
    for suffix in ("_peak_time_relative_to_impact", "_velocity_peak", "_peak"):
        if feature_name.endswith(suffix):
            return "joint_angle", feature_name[: -len(suffix)]
    return "unknown", feature_name


def _drill_for_deviation(deviation: Deviation) -> str:
    if deviation.feature_group == "muscle_activation":
        return f"在慢速分解挥拍中监控 {deviation.signal_name} 激活峰值和峰值时机，逐步接近正确模板范围。"
    if "trunk_rotation" in deviation.signal_name:
        return "练习蹬地、转髋、转体到击球窗口的连续释放，避免只用手臂向上带拍。"
    if "forearm_pronation" in deviation.signal_name or "wrist" in deviation.signal_name:
        return "练习击球前后窗口的前臂旋前和腕部释放，让拍面在身体前上方完成加速。"
    if "elbow" in deviation.signal_name or "shoulder" in deviation.signal_name:
        return "用慢速到中速分解挥拍建立肩、肘、腕的近端到远端释放顺序。"
    return f"针对 {deviation.signal_name} 做低速分解练习，并用模板范围复查。"


def _goal_for_deviation(deviation: Deviation) -> str:
    direction = "提高" if deviation.direction == "below_template" else "降低"
    return (
        f"{direction} {deviation.signal_name} 在 {deviation.phase} 阶段的 {deviation.feature}，"
        f"从 {deviation.observed_value:.4g} {deviation.unit} 调整到 "
        f"{deviation.template_lower_bound:.4g}-{deviation.template_upper_bound:.4g} {deviation.unit}。"
    )


def _build_correction_plan(deviations: list[Deviation]) -> list[CorrectionAction]:
    plan: list[CorrectionAction] = []
    seen: set[tuple[str, str]] = set()
    for deviation in deviations:
        key = (deviation.feature_group, deviation.signal_name)
        if key in seen:
            continue
        seen.add(key)
        plan.append(
            CorrectionAction(
                target_feature=deviation.feature,
                target_signal=deviation.signal_name,
                feature_group=deviation.feature_group,
                phase=deviation.phase,
                severity=deviation.severity,
                goal=_goal_for_deviation(deviation),
                drill=_drill_for_deviation(deviation),
                validation_metric="bring_observed_value_inside_template_range",
            )
        )
    return plan


def _mechanism_for_deviation(deviation: Deviation, mechanisms: list[str]) -> str:
    if "trunk_rotation" in deviation.signal_name and mechanisms:
        return mechanisms[0]
    if deviation.feature_group == "muscle_activation" and len(mechanisms) >= 2:
        return mechanisms[1]
    if ("forearm_pronation" in deviation.signal_name or "wrist" in deviation.signal_name) and len(mechanisms) >= 2:
        return mechanisms[1]
    if mechanisms:
        return mechanisms[-1]
    return "outcome_linked_signal_deviation"


def _build_explanation_links(
    outcome_label: str,
    deviations: list[Deviation],
    mechanisms: list[str],
) -> list[ExplanationLink]:
    links: list[ExplanationLink] = []
    for deviation in deviations:
        mechanism = _mechanism_for_deviation(deviation, mechanisms)
        direction = "lower than" if deviation.direction == "below_template" else "higher than"
        links.append(
            ExplanationLink(
                outcome_label=outcome_label,
                feature=deviation.feature,
                signal_name=deviation.signal_name,
                feature_group=deviation.feature_group,
                phase=deviation.phase,
                severity=deviation.severity,
                deviation_direction=deviation.direction,
                mechanism=mechanism,
                rationale=(
                    f"{deviation.feature} is {direction} the correct-template range during "
                    f"{deviation.phase}; this signal is linked to {outcome_label} through {mechanism}."
                ),
                correction_focus=(
                    f"Move {deviation.signal_name} {deviation.direction} deviation back toward "
                    f"{deviation.template_lower_bound:.4g}-{deviation.template_upper_bound:.4g} {deviation.unit}."
                ),
                evidence_query=(
                    f"badminton forehand clear {outcome_label} {deviation.feature} "
                    f"{deviation.signal_name} {mechanism}"
                ),
            )
        )
    return links


def diagnose_sample(sample: DiagnosticSample, template: CorrectTemplate) -> DiagnosisReport:
    observed_features = extract_features(sample)
    rule = OUTCOME_RULES[sample.outcome_label]
    deviations: list[Deviation] = []

    for name, observed in observed_features.items():
        template_feature = template.features.get(name)
        if template_feature is None:
            continue
        severity = _severity(observed.value, template_feature.lower_bound, template_feature.upper_bound, template_feature.std)
        if severity == "none":
            continue
        if not _matches_rule(name, rule["features"]):
            continue
        feature_group, signal_name = _feature_source(name)
        deviations.append(
            Deviation(
                feature=name,
                phase=observed.phase,
                direction=_direction(observed.value, template_feature.lower_bound, template_feature.upper_bound),
                severity=severity,
                observed_value=observed.value,
                template_value=template_feature.mean,
                unit=template_feature.unit,
                interpretation=f"{name} 相对正确模板出现 {severity} 偏差。",
                template_lower_bound=template_feature.lower_bound,
                template_upper_bound=template_feature.upper_bound,
                template_std=template_feature.std,
                threshold_source=template_feature.threshold_source,
                feature_group=feature_group,
                signal_name=signal_name,
            )
        )

    severity_rank = {"high": 3, "medium": 2, "low": 1}
    deviations.sort(key=lambda item: severity_rank[item.severity], reverse=True)
    confidence = "medium" if deviations else "low"
    key_deviations = deviations[:8]
    mechanisms = list(rule["mechanisms"])
    explanation_links = _build_explanation_links(sample.outcome_label.value, key_deviations, mechanisms)
    evidence_queries = [
        f"forehand clear {sample.outcome_label.value}",
        "badminton forehand clear trunk rotation kinematics",
        "badminton overhead forehand stroke kinetic chain",
    ]
    evidence_queries.extend(link.evidence_query for link in explanation_links)

    return DiagnosisReport(
        sample_id=sample.sample_id,
        action_type=sample.action_type,
        outcome_label=sample.outcome_label,
        primary_diagnosis=rule["primary_diagnosis"],
        diagnostic_confidence=confidence,
        key_deviations=key_deviations,
        likely_mechanisms=mechanisms,
        correction_suggestions=list(rule["suggestions"]),
        correction_plan=_build_correction_plan(key_deviations),
        explanation_links=explanation_links,
        evidence_queries=evidence_queries,
    )
