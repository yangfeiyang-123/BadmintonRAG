# Forehand Clear Diagnostic RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first offline diagnostic loop for forehand clear: classify sources, extract text, validate time-series samples, build correct templates, detect deviations, and produce structured diagnoses for three discrete outcome labels.

**Architecture:** The first phase is deterministic Python code. The diagnostic engine compares a candidate forehand-clear time series against a correct-action template, filters deviations through outcome-specific rules, and returns structured JSON. The RAG/LLM layer is left as an evidence interface and does not need a model key yet.

**Tech Stack:** Python 3 standard library, `pytest`, optional `pypdf`/`bs4` only if already available; no network calls and no LLM dependency in phase one.

---

## File Structure

- Create `rag_project/__init__.py`: package marker.
- Create `rag_project/diagnostics/__init__.py`: diagnostics package marker.
- Create `rag_project/knowledge/__init__.py`: knowledge package marker.
- Create `rag_project/diagnostics/schemas.py`: dataclasses and validation for samples, templates, deviations, and diagnoses.
- Create `rag_project/diagnostics/phase_alignment.py`: event validation and impact-centered phase windows.
- Create `rag_project/diagnostics/features.py`: feature extraction from joint angles and muscle activations.
- Create `rag_project/diagnostics/templates.py`: correct-template construction from labeled correct samples.
- Create `rag_project/diagnostics/rules_forehand_clear.py`: outcome-label rule definitions.
- Create `rag_project/diagnostics/diagnose.py`: deviation detection, rule filtering, ranking, and report generation.
- Create `rag_project/knowledge/source_classifier.py`: artifact classification from manifests and saved files.
- Create `rag_project/knowledge/extract_text.py`: lightweight PDF/HTML text extraction with conservative fallback.
- Create `rag_project/examples/forehand_clear_correct_samples.json`: small deterministic correct-sample fixture.
- Create `rag_project/examples/forehand_clear_eval_samples.json`: three deterministic evaluation samples.
- Create `tests/diagnostics/test_schemas.py`: schema validation tests.
- Create `tests/diagnostics/test_features.py`: feature extraction tests.
- Create `tests/diagnostics/test_templates.py`: template construction tests.
- Create `tests/diagnostics/test_diagnose.py`: end-to-end diagnosis tests.
- Create `tests/knowledge/test_source_classifier.py`: source classification tests.
- Create `tests/knowledge/test_extract_text.py`: text extraction smoke tests.

## Model Key Policy

No LLM URL or key is needed for this phase. The first phase must run fully offline.

When phase two adds explanation generation, the implementation will read these optional environment variables:

```text
RAG_LLM_BASE_URL
RAG_LLM_API_KEY
RAG_LLM_MODEL
```

Keys must never be written into source files, sample files, docs, or test fixtures.

---

### Task 1: Package Skeleton And Schema Validation

**Files:**
- Create: `rag_project/__init__.py`
- Create: `rag_project/diagnostics/__init__.py`
- Create: `rag_project/knowledge/__init__.py`
- Create: `rag_project/diagnostics/schemas.py`
- Create: `tests/diagnostics/test_schemas.py`

- [ ] **Step 1: Write failing schema tests**

Create `tests/diagnostics/test_schemas.py`:

```python
import pytest

from rag_project.diagnostics.schemas import (
    DiagnosticSample,
    OutcomeLabel,
    TimeSeriesValidationError,
)


def valid_payload():
    return {
        "sample_id": "clear_001",
        "action_type": "forehand_clear",
        "outcome_label": "ball_high_not_far",
        "time": [0.0, 0.1, 0.2],
        "events": {"impact": 0.1},
        "joint_angles": {"trunk_rotation": [10.0, 20.0, 30.0]},
        "muscle_activation": {"anterior_deltoid": [0.1, 0.3, 0.2]},
    }


def test_valid_sample_loads():
    sample = DiagnosticSample.from_dict(valid_payload())
    assert sample.sample_id == "clear_001"
    assert sample.outcome_label == OutcomeLabel.BALL_HIGH_NOT_FAR
    assert sample.series_length == 3


def test_rejects_unknown_action_type():
    payload = valid_payload()
    payload["action_type"] = "smash"
    with pytest.raises(TimeSeriesValidationError, match="action_type"):
        DiagnosticSample.from_dict(payload)


def test_rejects_missing_impact():
    payload = valid_payload()
    payload["events"] = {}
    with pytest.raises(TimeSeriesValidationError, match="impact"):
        DiagnosticSample.from_dict(payload)


def test_rejects_mismatched_series_lengths():
    payload = valid_payload()
    payload["joint_angles"]["trunk_rotation"] = [1.0, 2.0]
    with pytest.raises(TimeSeriesValidationError, match="length"):
        DiagnosticSample.from_dict(payload)
```

- [ ] **Step 2: Run schema tests and verify failure**

Run:

```powershell
python -m pytest tests/diagnostics/test_schemas.py -v
```

Expected: FAIL because `rag_project.diagnostics.schemas` does not exist.

- [ ] **Step 3: Implement schema dataclasses**

Create `rag_project/diagnostics/schemas.py`:

```python
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
            muscle_activation={str(k): [float(x) for x in v] for k, v in (payload.get("muscle_activation") or {}).items()},
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
    evidence_queries: list[str] = field(default_factory=list)
```

- [ ] **Step 4: Add package marker files**

Create empty files:

```text
rag_project/__init__.py
rag_project/diagnostics/__init__.py
rag_project/knowledge/__init__.py
```

- [ ] **Step 5: Run schema tests and verify pass**

Run:

```powershell
python -m pytest tests/diagnostics/test_schemas.py -v
```

Expected: PASS.

---

### Task 2: Phase Windows And Feature Extraction

**Files:**
- Create: `rag_project/diagnostics/phase_alignment.py`
- Create: `rag_project/diagnostics/features.py`
- Create: `tests/diagnostics/test_features.py`

- [ ] **Step 1: Write failing feature tests**

Create `tests/diagnostics/test_features.py`:

```python
from rag_project.diagnostics.features import extract_features
from rag_project.diagnostics.schemas import DiagnosticSample


def sample_payload():
    return {
        "sample_id": "clear_001",
        "action_type": "forehand_clear",
        "outcome_label": "ball_high_not_far",
        "time": [0.0, 0.1, 0.2, 0.3],
        "events": {"backswing_start": 0.0, "acceleration_start": 0.1, "impact": 0.2, "follow_through_end": 0.3},
        "joint_angles": {
            "trunk_rotation": [0.0, 20.0, 40.0, 30.0],
            "elbow_flexion": [100.0, 90.0, 70.0, 80.0],
        },
        "muscle_activation": {
            "anterior_deltoid": [0.1, 0.8, 0.4, 0.2],
            "forearm_pronator_group": [0.1, 0.2, 0.7, 0.4],
        },
    }


def test_extracts_peak_and_peak_time_relative_to_impact():
    sample = DiagnosticSample.from_dict(sample_payload())
    features = extract_features(sample)
    assert features["trunk_rotation_peak"].value == 40.0
    assert features["trunk_rotation_peak_time_relative_to_impact"].value == 0.0
    assert features["anterior_deltoid_activation_peak"].value == 0.8
    assert features["anterior_deltoid_activation_peak_time_relative_to_impact"].value == -0.1


def test_extracts_velocity_peak_for_joint_angles():
    sample = DiagnosticSample.from_dict(sample_payload())
    features = extract_features(sample)
    assert features["trunk_rotation_velocity_peak"].value == 200.0
```

- [ ] **Step 2: Run feature tests and verify failure**

Run:

```powershell
python -m pytest tests/diagnostics/test_features.py -v
```

Expected: FAIL because feature extraction does not exist.

- [ ] **Step 3: Implement phase helper**

Create `rag_project/diagnostics/phase_alignment.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from rag_project.diagnostics.schemas import DiagnosticSample


@dataclass(frozen=True)
class PhaseWindow:
    name: str
    start: float
    end: float


def phase_windows(sample: DiagnosticSample) -> list[PhaseWindow]:
    impact = sample.events["impact"]
    return [
        PhaseWindow("backswing", sample.events.get("backswing_start", sample.time[0]), sample.events.get("acceleration_start", impact)),
        PhaseWindow("acceleration", sample.events.get("acceleration_start", sample.time[0]), impact),
        PhaseWindow("impact_window", impact - 0.05, impact + 0.05),
        PhaseWindow("follow_through", impact, sample.events.get("follow_through_end", sample.time[-1])),
    ]
```

- [ ] **Step 4: Implement feature extraction**

Create `rag_project/diagnostics/features.py`:

```python
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
        features[f"{signal}_activation_peak"] = ExtractedFeature(f"{signal}_activation_peak", peak, "normalized_activation", phase)
        features[f"{signal}_activation_peak_time_relative_to_impact"] = ExtractedFeature(
            f"{signal}_activation_peak_time_relative_to_impact", round(peak_time - impact, 10), "second", phase
        )

    return features
```

- [ ] **Step 5: Run feature tests and verify pass**

Run:

```powershell
python -m pytest tests/diagnostics/test_features.py -v
```

Expected: PASS.

---

### Task 3: Correct Template Construction

**Files:**
- Create: `rag_project/diagnostics/templates.py`
- Create: `tests/diagnostics/test_templates.py`

- [ ] **Step 1: Write failing template tests**

Create `tests/diagnostics/test_templates.py`:

```python
from rag_project.diagnostics.schemas import DiagnosticSample
from rag_project.diagnostics.templates import build_correct_template


def make_sample(sample_id, trunk_peak):
    return DiagnosticSample.from_dict({
        "sample_id": sample_id,
        "action_type": "forehand_clear",
        "outcome_label": "low_speed",
        "time": [0.0, 0.1, 0.2],
        "events": {"impact": 0.2, "acceleration_start": 0.1},
        "joint_angles": {"trunk_rotation": [0.0, trunk_peak / 2.0, trunk_peak]},
        "muscle_activation": {"anterior_deltoid": [0.1, 0.2, 0.3]},
    })


def test_builds_template_bounds_from_correct_samples():
    template = build_correct_template("forehand_clear_correct_v1", [make_sample("a", 40.0), make_sample("b", 44.0)])
    feature = template.features["trunk_rotation_peak"]
    assert template.sample_count == 2
    assert feature.mean == 42.0
    assert feature.lower_bound < 42.0
    assert feature.upper_bound > 42.0
```

- [ ] **Step 2: Run template tests and verify failure**

Run:

```powershell
python -m pytest tests/diagnostics/test_templates.py -v
```

Expected: FAIL because `templates.py` does not exist.

- [ ] **Step 3: Implement template construction**

Create `rag_project/diagnostics/templates.py`:

```python
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

    return CorrectTemplate(template_id=template_id, action_type="forehand_clear", sample_count=len(samples), features=template_features)
```

- [ ] **Step 4: Run template tests and verify pass**

Run:

```powershell
python -m pytest tests/diagnostics/test_templates.py -v
```

Expected: PASS.

---

### Task 4: Source Classification

**Files:**
- Create: `rag_project/knowledge/source_classifier.py`
- Create: `tests/knowledge/test_source_classifier.py`

- [ ] **Step 1: Write failing source classification tests**

Create `tests/knowledge/test_source_classifier.py`:

```python
from rag_project.knowledge.source_classifier import classify_source


def test_classifies_official_manual():
    result = classify_source("BWF_COACHES", "official", "downloaded_html_and_supplemental_pdf", "BWF Coach Manual")
    assert result == "official_manual"


def test_classifies_book_preview():
    result = classify_source("BOOK_GRICE", "book", "downloaded_html", "Badminton: Steps to Success")
    assert result == "book_preview_or_product_page"


def test_classifies_pubmed_as_metadata_when_only_html():
    result = classify_source("REV_PHOMSOUPHA_LAFFAYE", "review", "downloaded_html", "PubMed record")
    assert result == "abstract_or_metadata_only"


def test_classifies_pmc_html_as_full_text():
    result = classify_source("REV_LAM_LUNGE", "review", "downloaded_html", "PMC open access article")
    assert result == "full_text_html"
```

- [ ] **Step 2: Run classification tests and verify failure**

Run:

```powershell
python -m pytest tests/knowledge/test_source_classifier.py -v
```

Expected: FAIL because `source_classifier.py` does not exist.

- [ ] **Step 3: Implement source classifier**

Create `rag_project/knowledge/source_classifier.py`:

```python
from __future__ import annotations


def classify_source(source_id: str, category: str, status: str, notes: str) -> str:
    text = f"{source_id} {category} {status} {notes}".lower()
    if "bwf" in text or "shuttle" in text or category == "official":
        return "official_manual"
    if category == "book" or "book" in text or "google books" in text or "commercial" in text:
        return "book_preview_or_product_page"
    if "pmc open access" in text or "nature scientific reports open" in text or "frontiers open" in text:
        return "full_text_html"
    if "downloaded_pdf" in status:
        return "full_text_pdf"
    if "pubmed record" in text or "airiti" in text or "metadata" in text or "thesis metadata" in text:
        return "abstract_or_metadata_only"
    if "downloaded_html" in status:
        return "full_text_html"
    return "abstract_or_metadata_only"
```

- [ ] **Step 4: Run classification tests and verify pass**

Run:

```powershell
python -m pytest tests/knowledge/test_source_classifier.py -v
```

Expected: PASS.

---

### Task 5: Forehand Clear Outcome Rules And Diagnosis

**Files:**
- Create: `rag_project/diagnostics/rules_forehand_clear.py`
- Create: `rag_project/diagnostics/diagnose.py`
- Create: `tests/diagnostics/test_diagnose.py`

- [ ] **Step 1: Write failing diagnosis tests**

Create `tests/diagnostics/test_diagnose.py`:

```python
from rag_project.diagnostics.diagnose import diagnose_sample
from rag_project.diagnostics.schemas import DiagnosticSample
from rag_project.diagnostics.templates import build_correct_template


def correct_sample(sample_id):
    return DiagnosticSample.from_dict({
        "sample_id": sample_id,
        "action_type": "forehand_clear",
        "outcome_label": "low_speed",
        "time": [0.0, 0.1, 0.2, 0.3],
        "events": {"acceleration_start": 0.1, "impact": 0.2, "follow_through_end": 0.3},
        "joint_angles": {
            "trunk_rotation": [0.0, 20.0, 42.0, 35.0],
            "forearm_pronation": [0.0, 10.0, 30.0, 32.0],
        },
        "muscle_activation": {
            "external_oblique": [0.1, 0.5, 0.8, 0.3],
            "anterior_deltoid": [0.1, 0.3, 0.5, 0.2],
        },
    })


def poor_sample():
    return DiagnosticSample.from_dict({
        "sample_id": "poor_clear",
        "action_type": "forehand_clear",
        "outcome_label": "ball_high_not_far",
        "time": [0.0, 0.1, 0.2, 0.3],
        "events": {"acceleration_start": 0.1, "impact": 0.2, "follow_through_end": 0.3},
        "joint_angles": {
            "trunk_rotation": [0.0, 10.0, 25.0, 24.0],
            "forearm_pronation": [0.0, 5.0, 12.0, 18.0],
        },
        "muscle_activation": {
            "external_oblique": [0.1, 0.2, 0.3, 0.2],
            "anterior_deltoid": [0.7, 0.6, 0.3, 0.2],
        },
    })


def test_diagnoses_ball_high_not_far_with_relevant_deviations():
    template = build_correct_template("correct", [correct_sample("a"), correct_sample("b")])
    report = diagnose_sample(poor_sample(), template)
    assert report.primary_diagnosis == "击球阶段向前动量不足，末端释放效率偏低"
    names = {deviation.feature for deviation in report.key_deviations}
    assert "trunk_rotation_peak" in names
    assert "forearm_pronation_peak" in names
    assert "躯干带动不足" in report.likely_mechanisms
```

- [ ] **Step 2: Run diagnosis tests and verify failure**

Run:

```powershell
python -m pytest tests/diagnostics/test_diagnose.py -v
```

Expected: FAIL because diagnosis modules do not exist.

- [ ] **Step 3: Implement outcome rules**

Create `rag_project/diagnostics/rules_forehand_clear.py`:

```python
from __future__ import annotations

from rag_project.diagnostics.schemas import OutcomeLabel


OUTCOME_RULES = {
    OutcomeLabel.BALL_HIGH_NOT_FAR: {
        "primary_diagnosis": "击球阶段向前动量不足，末端释放效率偏低",
        "features": ["trunk_rotation", "forearm_pronation", "wrist", "elbow", "external_oblique", "anterior_deltoid"],
        "mechanisms": ["躯干带动不足", "末端释放滞后或不足", "发力方向偏上，向前动量不足"],
        "suggestions": [
            "优先练习蹬地、转髋、转体后再带动肩肘腕释放。",
            "击球点保持在身体前上方，避免击球点过后导致向前穿透不足。",
            "练习击球前后窗口的前臂旋前和腕部释放。",
        ],
    },
    OutcomeLabel.LOW_SPEED: {
        "primary_diagnosis": "动力链总输出不足",
        "features": ["trunk_rotation_velocity", "shoulder", "elbow", "forearm_pronation", "wrist"],
        "mechanisms": ["动力链总输出不足", "近端到远端传递效率低", "击球阶段力量释放不集中"],
        "suggestions": ["提高蹬转与躯干旋转输出。", "练习肩肘腕在击球窗口集中释放。"],
    },
    OutcomeLabel.UNCOORDINATED_POWER: {
        "primary_diagnosis": "近端到远端释放顺序异常",
        "features": ["peak_time_relative_to_impact", "trunk_rotation", "shoulder", "elbow", "wrist"],
        "mechanisms": ["动作阶段衔接问题", "肌肉激活时序不稳定", "动力链释放顺序异常"],
        "suggestions": ["用慢速分解练习建立蹬转、转体、挥臂的顺序。", "把末端释放集中到击球前后窗口。"],
    },
}
```

- [ ] **Step 4: Implement diagnosis engine**

Create `rag_project/diagnostics/diagnose.py`:

```python
from __future__ import annotations

from rag_project.diagnostics.features import extract_features
from rag_project.diagnostics.rules_forehand_clear import OUTCOME_RULES
from rag_project.diagnostics.schemas import CorrectTemplate, Deviation, DiagnosisReport, DiagnosticSample


def _severity(observed: float, lower: float, upper: float, std: float) -> str:
    if lower <= observed <= upper:
        return "none"
    if std <= 0:
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
```

- [ ] **Step 5: Run diagnosis tests and verify pass**

Run:

```powershell
python -m pytest tests/diagnostics/test_diagnose.py -v
```

Expected: PASS.

---

### Task 6: Text Extraction Smoke Layer

**Files:**
- Create: `rag_project/knowledge/extract_text.py`
- Create: `tests/knowledge/test_extract_text.py`

- [ ] **Step 1: Write failing extraction tests**

Create `tests/knowledge/test_extract_text.py`:

```python
from pathlib import Path

from rag_project.knowledge.extract_text import extract_html_text


def test_extract_html_text_removes_tags(tmp_path: Path):
    html = tmp_path / "sample.html"
    html.write_text("<html><body><nav>Menu</nav><h1>Title</h1><p>Useful paragraph.</p></body></html>", encoding="utf-8")
    text = extract_html_text(html)
    assert "Title" in text
    assert "Useful paragraph." in text
    assert "<p>" not in text
```

- [ ] **Step 2: Run extraction tests and verify failure**

Run:

```powershell
python -m pytest tests/knowledge/test_extract_text.py -v
```

Expected: FAIL because `extract_text.py` does not exist.

- [ ] **Step 3: Implement conservative HTML extractor**

Create `rag_project/knowledge/extract_text.py`:

```python
from __future__ import annotations

import re
from html import unescape
from pathlib import Path


def extract_html_text(path: Path) -> str:
    html = path.read_text(encoding="utf-8", errors="replace")
    html = re.sub(r"(?is)<(script|style|noscript|svg).*?</\1>", " ", html)
    html = re.sub(r"(?is)<(nav|footer|header).*?</\1>", " ", html)
    html = re.sub(r"(?is)<br\s*/?>", "\n", html)
    html = re.sub(r"(?is)</(p|h1|h2|h3|li|tr)>", "\n", html)
    text = re.sub(r"(?is)<[^>]+>", " ", html)
    text = unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)
    return text.strip()
```

- [ ] **Step 4: Run extraction tests and verify pass**

Run:

```powershell
python -m pytest tests/knowledge/test_extract_text.py -v
```

Expected: PASS.

---

### Task 7: Example Fixtures And End-To-End Command

**Files:**
- Create: `rag_project/examples/forehand_clear_correct_samples.json`
- Create: `rag_project/examples/forehand_clear_eval_samples.json`
- Create: `rag_project/diagnostics/run_forehand_clear_demo.py`
- Create: `tests/diagnostics/test_demo.py`

- [ ] **Step 1: Write failing demo test**

Create `tests/diagnostics/test_demo.py`:

```python
import json
from pathlib import Path

from rag_project.diagnostics.run_forehand_clear_demo import run_demo


def test_demo_outputs_three_reports(tmp_path: Path):
    output = tmp_path / "reports.json"
    run_demo(output)
    reports = json.loads(output.read_text(encoding="utf-8"))
    assert len(reports) == 3
    assert {report["outcome_label"] for report in reports} == {"ball_high_not_far", "low_speed", "uncoordinated_power"}
    assert all(report["key_deviations"] for report in reports)
```

- [ ] **Step 2: Run demo test and verify failure**

Run:

```powershell
python -m pytest tests/diagnostics/test_demo.py -v
```

Expected: FAIL because demo runner does not exist.

- [ ] **Step 3: Create fixture JSON files**

Create fixtures with four time points, at least two correct samples, and three evaluation samples. The evaluation samples must each use one of:

```text
ball_high_not_far
low_speed
uncoordinated_power
```

Use the signal names from the design: `trunk_rotation`, `forearm_pronation`, `elbow_flexion`, `anterior_deltoid`, and `external_oblique`.

- [ ] **Step 4: Implement demo runner**

Create `rag_project/diagnostics/run_forehand_clear_demo.py`:

```python
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from rag_project.diagnostics.diagnose import diagnose_sample
from rag_project.diagnostics.schemas import DiagnosticSample
from rag_project.diagnostics.templates import build_correct_template


ROOT = Path(__file__).resolve().parents[1]


def _load_samples(path: Path) -> list[DiagnosticSample]:
    payloads = json.loads(path.read_text(encoding="utf-8"))
    return [DiagnosticSample.from_dict(payload) for payload in payloads]


def run_demo(output_path: Path) -> None:
    correct = _load_samples(ROOT / "examples" / "forehand_clear_correct_samples.json")
    eval_samples = _load_samples(ROOT / "examples" / "forehand_clear_eval_samples.json")
    template = build_correct_template("forehand_clear_correct_v1", correct)
    reports = [asdict(diagnose_sample(sample, template)) for sample in eval_samples]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    run_demo(ROOT / "outputs" / "forehand_clear_demo_reports.json")
```

- [ ] **Step 5: Run demo test and verify pass**

Run:

```powershell
python -m pytest tests/diagnostics/test_demo.py -v
```

Expected: PASS.

- [ ] **Step 6: Run demo command**

Run:

```powershell
python -m rag_project.diagnostics.run_forehand_clear_demo
```

Expected: creates `rag_project/outputs/forehand_clear_demo_reports.json` with three diagnosis reports.

---

### Task 8: Full Verification

**Files:**
- Read all files created above.

- [ ] **Step 1: Run all tests**

Run:

```powershell
python -m pytest -v
```

Expected: all tests PASS.

- [ ] **Step 2: Run artifact inventory check**

Run:

```powershell
python -c "import csv; from pathlib import Path; rows=list(csv.DictReader(Path('rag_project/sources/raw/metadata/download_results.csv').open(encoding='utf-8-sig'))); print(len(rows), sum(1 for r in rows if r['downloaded_files']))"
```

Expected: `37 37`.

- [ ] **Step 3: Run PDF validity check**

Run:

```powershell
python -c "from pathlib import Path; pdfs=list(Path('rag_project/sources/raw/pdf').glob('*.pdf')); bad=[p for p in pdfs if not p.read_bytes()[:16].lstrip().startswith(b'%PDF-')]; print(len(pdfs), len(bad))"
```

Expected: `11 0`.

- [ ] **Step 4: Commit if repository exists**

Run:

```powershell
git status --short
```

Expected in this workspace: this may fail with `fatal: not a git repository`. If it fails, report that commit is unavailable. If it succeeds, commit:

```powershell
git add docs rag_project tests
git commit -m "feat: add forehand clear diagnostic MVP"
```

---

## Self-Review

- The plan covers the design requirements for source classification, text extraction, schema validation, template construction, feature extraction, three outcome rules, and structured diagnosis.
- The first phase does not require an LLM URL or key.
- No task writes secrets into files.
- Each implementation task starts with a failing test and ends with a passing verification command.
- Commit is conditional because the current workspace has already shown it is not a Git repository.
