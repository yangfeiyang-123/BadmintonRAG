from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TimeSeriesValidationError(ValueError):
    pass


class OutcomeLabel(str, Enum):
    BALL_HIGH_NOT_FAR = "ball_high_not_far"
    LOW_SPEED = "low_speed"
    UNCOORDINATED_POWER = "uncoordinated_power"


@dataclass(frozen=True)
class DiagnosticSample:
    sample_id: str
    action_type: str
    outcome_label: OutcomeLabel
    time: list[float]
    events: dict[str, float]
    joint_angles: dict[str, list[float]]
    muscle_activation: dict[str, list[float]]

    @property
    def series_length(self) -> int:
        return len(self.time)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DiagnosticSample":
        action_type = payload.get("action_type")
        if action_type != "forehand_clear":
            raise TimeSeriesValidationError(f"Unsupported action_type: {action_type}")

        events = dict(payload.get("events") or {})
        if "impact" not in events:
            raise TimeSeriesValidationError("events.impact is required")

        try:
            outcome_label = OutcomeLabel(payload.get("outcome_label"))
        except ValueError as exc:
            raise TimeSeriesValidationError(f"Unsupported outcome_label: {payload.get('outcome_label')}") from exc

        sample = cls(
            sample_id=str(payload.get("sample_id") or ""),
            action_type=action_type,
            outcome_label=outcome_label,
            time=[float(v) for v in payload.get("time") or []],
            events={str(k): float(v) for k, v in events.items()},
            joint_angles={str(k): [float(x) for x in v] for k, v in (payload.get("joint_angles") or {}).items()},
            muscle_activation={
                str(k): [float(x) for x in v] for k, v in (payload.get("muscle_activation") or {}).items()
            },
        )
        sample.validate()
        return sample

    def validate(self) -> None:
        if not self.sample_id:
            raise TimeSeriesValidationError("sample_id is required")
        if len(self.time) < 2:
            raise TimeSeriesValidationError("time must contain at least two points")
        if sorted(self.time) != self.time:
            raise TimeSeriesValidationError("time must be sorted")
        impact = self.events["impact"]
        if impact < self.time[0] or impact > self.time[-1]:
            raise TimeSeriesValidationError("events.impact must fall inside time range")

        expected = len(self.time)
        for group_name, group in [("joint_angles", self.joint_angles), ("muscle_activation", self.muscle_activation)]:
            if not group:
                raise TimeSeriesValidationError(f"{group_name} cannot be empty")
            for signal_name, values in group.items():
                if len(values) != expected:
                    raise TimeSeriesValidationError(f"{group_name}.{signal_name} length mismatch")


@dataclass(frozen=True)
class TemplateFeature:
    feature: str
    phase: str
    mean: float
    std: float
    unit: str
    lower_bound: float
    upper_bound: float
    threshold_source: str = "sample_statistics"


@dataclass(frozen=True)
class CorrectTemplate:
    template_id: str
    action_type: str
    sample_count: int
    features: dict[str, TemplateFeature]


@dataclass(frozen=True)
class Deviation:
    feature: str
    phase: str
    direction: str
    severity: str
    observed_value: float
    template_value: float
    unit: str
    interpretation: str
    template_lower_bound: float = 0.0
    template_upper_bound: float = 0.0
    template_std: float = 0.0
    threshold_source: str = ""
    feature_group: str = ""
    signal_name: str = ""


@dataclass(frozen=True)
class CorrectionAction:
    target_feature: str
    target_signal: str
    feature_group: str
    phase: str
    severity: str
    goal: str
    drill: str
    validation_metric: str


@dataclass(frozen=True)
class DiagnosisReport:
    sample_id: str
    action_type: str
    outcome_label: OutcomeLabel
    primary_diagnosis: str
    diagnostic_confidence: str
    key_deviations: list[Deviation] = field(default_factory=list)
    likely_mechanisms: list[str] = field(default_factory=list)
    correction_suggestions: list[str] = field(default_factory=list)
    correction_plan: list[CorrectionAction] = field(default_factory=list)
    evidence_queries: list[str] = field(default_factory=list)
