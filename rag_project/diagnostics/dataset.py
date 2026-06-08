from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from rag_project.diagnostics.schemas import DiagnosticSample, TimeSeriesValidationError


@dataclass(frozen=True)
class DiagnosticDataset:
    dataset_id: str
    action_type: str
    correct_samples: list[DiagnosticSample]
    eval_samples: list[DiagnosticSample]


def load_diagnostic_dataset(path: Path) -> DiagnosticDataset:
    payload = json.loads(path.read_text(encoding="utf-8"))
    dataset_id = str(payload.get("dataset_id") or path.stem)
    action_type = str(payload.get("action_type") or "forehand_clear")
    correct_samples = [DiagnosticSample.from_dict(row) for row in payload.get("correct_samples") or []]
    eval_samples = [DiagnosticSample.from_dict(row) for row in payload.get("eval_samples") or []]

    if not correct_samples:
        raise TimeSeriesValidationError("correct_samples cannot be empty")
    if not eval_samples:
        raise TimeSeriesValidationError("eval_samples cannot be empty")
    sample_actions = {sample.action_type for sample in correct_samples + eval_samples}
    if sample_actions != {action_type}:
        raise TimeSeriesValidationError(f"dataset action_type mismatch: {sorted(sample_actions)} vs {action_type}")

    return DiagnosticDataset(
        dataset_id=dataset_id,
        action_type=action_type,
        correct_samples=correct_samples,
        eval_samples=eval_samples,
    )
