from __future__ import annotations

from statistics import mean, pstdev

from rag_project.diagnostics.features import extract_features
from rag_project.diagnostics.schemas import CorrectTemplate, DiagnosticSample, TemplateFeature


def build_correct_template(template_id: str, samples: list[DiagnosticSample]) -> CorrectTemplate:
    if not samples:
        raise ValueError("At least one correct sample is required")

    grouped: dict[str, list[tuple[float, str, str]]] = {}
    for sample in samples:
        for name, feature in extract_features(sample).items():
            grouped.setdefault(name, []).append((feature.value, feature.phase, feature.unit))

    template_features: dict[str, TemplateFeature] = {}
    for name, values in grouped.items():
        numeric_values = [v[0] for v in values]
        feature_mean = mean(numeric_values)
        feature_std = pstdev(numeric_values) if len(numeric_values) > 1 else 0.0
        spread = feature_std * 2 if feature_std > 0 else max(abs(feature_mean) * 0.1, 0.01)
        template_features[name] = TemplateFeature(
            feature=name,
            phase=values[0][1],
            mean=feature_mean,
            std=feature_std,
            unit=values[0][2],
            lower_bound=feature_mean - spread,
            upper_bound=feature_mean + spread,
            threshold_source="sample_statistics" if len(samples) >= 5 else "small_sample_initial_threshold",
        )

    return CorrectTemplate(
        template_id=template_id,
        action_type="forehand_clear",
        sample_count=len(samples),
        features=template_features,
    )
