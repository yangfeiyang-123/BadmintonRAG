from __future__ import annotations

from dataclasses import dataclass

from rag_project.diagnostics.schemas import DiagnosticSample


@dataclass(frozen=True)
class ExtractedFeature:
    name: str
    value: float
    unit: str
    phase: str


def _peak(values: list[float]) -> tuple[float, int]:
    index = max(range(len(values)), key=lambda i: values[i])
    return values[index], index


def _velocity_peak(time: list[float], values: list[float]) -> float:
    peaks = []
    for i in range(1, len(values)):
        dt = time[i] - time[i - 1]
        if dt <= 0:
            continue
        peaks.append((values[i] - values[i - 1]) / dt)
    return max(peaks) if peaks else 0.0


def _phase_for_time(sample: DiagnosticSample, value_time: float) -> str:
    impact = sample.events["impact"]
    acceleration = sample.events.get("acceleration_start", impact)
    if value_time < acceleration:
        return "backswing"
    if value_time <= impact:
        return "acceleration"
    if value_time <= impact + 0.05:
        return "impact_window"
    return "follow_through"


def extract_features(sample: DiagnosticSample) -> dict[str, ExtractedFeature]:
    features: dict[str, ExtractedFeature] = {}
    impact = sample.events["impact"]

    for signal, values in sample.joint_angles.items():
        peak, peak_index = _peak(values)
        peak_time = sample.time[peak_index]
        phase = _phase_for_time(sample, peak_time)
        features[f"{signal}_peak"] = ExtractedFeature(f"{signal}_peak", peak, "degree", phase)
        features[f"{signal}_peak_time_relative_to_impact"] = ExtractedFeature(
            f"{signal}_peak_time_relative_to_impact", round(peak_time - impact, 10), "second", phase
        )
        features[f"{signal}_velocity_peak"] = ExtractedFeature(
            f"{signal}_velocity_peak", _velocity_peak(sample.time, values), "degree_per_second", "all"
        )

    for signal, values in sample.muscle_activation.items():
        peak, peak_index = _peak(values)
        peak_time = sample.time[peak_index]
        phase = _phase_for_time(sample, peak_time)
        features[f"{signal}_activation_peak"] = ExtractedFeature(
            f"{signal}_activation_peak", peak, "normalized_activation", phase
        )
        features[f"{signal}_activation_peak_time_relative_to_impact"] = ExtractedFeature(
            f"{signal}_activation_peak_time_relative_to_impact", round(peak_time - impact, 10), "second", phase
        )

    return features
