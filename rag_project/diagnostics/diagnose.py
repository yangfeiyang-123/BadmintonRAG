from __future__ import annotations

from rag_project.diagnostics.features import extract_features
from rag_project.diagnostics.rules_forehand_clear import OUTCOME_RULES
from rag_project.diagnostics.schemas import CorrectTemplate, Deviation, DiagnosisReport, DiagnosticSample


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
            )
        )

    severity_rank = {"high": 3, "medium": 2, "low": 1}
    deviations.sort(key=lambda item: severity_rank[item.severity], reverse=True)
    confidence = "medium" if deviations else "low"

    return DiagnosisReport(
        sample_id=sample.sample_id,
        action_type=sample.action_type,
        outcome_label=sample.outcome_label,
        primary_diagnosis=rule["primary_diagnosis"],
        diagnostic_confidence=confidence,
        key_deviations=deviations[:8],
        likely_mechanisms=list(rule["mechanisms"]),
        correction_suggestions=list(rule["suggestions"]),
        evidence_queries=[
            f"forehand clear {sample.outcome_label.value}",
            "badminton forehand clear trunk rotation kinematics",
            "badminton overhead forehand stroke kinetic chain",
        ],
    )
