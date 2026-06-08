from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from rag_project.diagnostics.dataset import DiagnosticDataset
from rag_project.diagnostics.schemas import DiagnosticSample, TimeSeriesValidationError


REQUIRED_COLUMNS = {"sample_id", "split", "action_type", "outcome_label", "time"}


def _float_or_none(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _signal_columns(fieldnames: list[str]) -> tuple[list[str], list[str], list[str]]:
    joint_columns = [name for name in fieldnames if name.startswith("joint_")]
    muscle_columns = [name for name in fieldnames if name.startswith("muscle_")]
    event_columns = [name for name in fieldnames if name.startswith("event_")]
    return joint_columns, muscle_columns, event_columns


def _sample_from_rows(sample_id: str, rows: list[dict[str, str]], fieldnames: list[str]) -> tuple[str, DiagnosticSample]:
    rows = sorted(rows, key=lambda row: float(row["time"]))
    first = rows[0]
    joint_columns, muscle_columns, event_columns = _signal_columns(fieldnames)
    events: dict[str, float] = {}
    for column in event_columns:
        event_name = column.removeprefix("event_")
        value = next((_float_or_none(row.get(column)) for row in rows if _float_or_none(row.get(column)) is not None), None)
        if value is not None:
            events[event_name] = value

    payload = {
        "sample_id": sample_id,
        "action_type": first["action_type"],
        "outcome_label": first["outcome_label"],
        "time": [float(row["time"]) for row in rows],
        "events": events,
        "joint_angles": {
            column.removeprefix("joint_"): [float(row[column]) for row in rows]
            for column in joint_columns
        },
        "muscle_activation": {
            column.removeprefix("muscle_"): [float(row[column]) for row in rows]
            for column in muscle_columns
        },
    }
    return first["split"], DiagnosticSample.from_dict(payload)


def load_dataset_from_csv(path: Path, dataset_id: str | None = None) -> DiagnosticDataset:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - set(fieldnames)
        if missing:
            raise TimeSeriesValidationError(f"CSV missing required columns: {sorted(missing)}")
        rows = list(reader)

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["sample_id"]].append(row)

    correct: list[DiagnosticSample] = []
    eval_samples: list[DiagnosticSample] = []
    actions: set[str] = set()
    for sample_id, sample_rows in grouped.items():
        split, sample = _sample_from_rows(sample_id, sample_rows, fieldnames)
        actions.add(sample.action_type)
        if split == "correct":
            correct.append(sample)
        elif split == "eval":
            eval_samples.append(sample)
        else:
            raise TimeSeriesValidationError(f"Unsupported split for {sample_id}: {split}")

    if not actions:
        raise TimeSeriesValidationError("CSV does not contain any samples")
    if len(actions) != 1:
        raise TimeSeriesValidationError(f"CSV contains multiple action types: {sorted(actions)}")

    return DiagnosticDataset(
        dataset_id=dataset_id or path.stem,
        action_type=next(iter(actions)),
        correct_samples=correct,
        eval_samples=eval_samples,
    )
