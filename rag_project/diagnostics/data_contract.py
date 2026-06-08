from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from rag_project.diagnostics.schemas import OutcomeLabel


REQUIRED_METADATA_COLUMNS = {"sample_id", "split", "action_type", "outcome_label", "time"}
REQUIRED_PREFIXES = {"event_", "joint_", "muscle_"}
SUPPORTED_SPLITS = {"correct", "eval"}
SUPPORTED_ACTION_TYPES = {"forehand_clear"}


class SimulationContractError(ValueError):
    pass


@dataclass(frozen=True)
class SimulationFieldSpec:
    prefix: str
    group: str
    required: bool
    unit_hint: str
    example: str
    description: str

    @staticmethod
    def default_specs() -> list["SimulationFieldSpec"]:
        return [
            SimulationFieldSpec(
                prefix="event_",
                group="events",
                required=True,
                unit_hint="seconds",
                example="event_impact",
                description="Sparse action events. Put the event time in seconds; repeated row values are allowed.",
            ),
            SimulationFieldSpec(
                prefix="joint_",
                group="joint_angles",
                required=True,
                unit_hint="degrees",
                example="joint_trunk_rotation",
                description="Joint angle time series sampled on the row time axis.",
            ),
            SimulationFieldSpec(
                prefix="muscle_",
                group="muscle_activation",
                required=True,
                unit_hint="normalized_0_to_1",
                example="muscle_external_oblique",
                description="Muscle activation time series sampled on the row time axis.",
            ),
        ]


@dataclass(frozen=True)
class SimulationContractReport:
    path: Path
    row_count: int
    sample_count: int
    correct_sample_count: int
    eval_sample_count: int
    action_types: list[str]
    outcome_labels: list[str]
    signal_counts: dict[str, int]
    field_specs: list[SimulationFieldSpec]

    def to_json_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["path"] = str(self.path)
        return payload


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    return fieldnames, rows


def _count_signal_prefixes(fieldnames: list[str]) -> dict[str, int]:
    return {prefix: sum(1 for name in fieldnames if name.startswith(prefix)) for prefix in sorted(REQUIRED_PREFIXES)}


def _validate_required_columns(fieldnames: list[str]) -> None:
    missing = REQUIRED_METADATA_COLUMNS - set(fieldnames)
    if missing:
        raise SimulationContractError(f"CSV missing required metadata columns: {sorted(missing)}")


def _validate_signal_columns(signal_counts: dict[str, int]) -> None:
    for prefix, count in signal_counts.items():
        if count == 0:
            raise SimulationContractError(f"CSV requires at least one {prefix} signal column")


def _validate_required_signal_names(fieldnames: list[str]) -> None:
    if "event_impact" not in fieldnames:
        raise SimulationContractError("CSV requires event_impact")


def _validate_numeric_signals(row: dict[str, str], index: int, fieldnames: list[str]) -> None:
    for column in fieldnames:
        if not column.startswith(("event_", "joint_", "muscle_")):
            continue
        value = row.get(column, "")
        if column.startswith("event_") and value == "":
            continue
        try:
            float(value)
        except ValueError as exc:
            raise SimulationContractError(f"Row {index} has non-numeric value in {column}") from exc


def _validate_rows(rows: list[dict[str, str]], fieldnames: list[str]) -> tuple[set[str], set[str], dict[str, str]]:
    if not rows:
        raise SimulationContractError("CSV does not contain any rows")

    action_types: set[str] = set()
    outcome_labels: set[str] = set()
    sample_splits: dict[str, str] = {}
    supported_outcomes = {label.value for label in OutcomeLabel}

    for index, row in enumerate(rows, start=2):
        sample_id = row.get("sample_id", "").strip()
        split = row.get("split", "").strip()
        action_type = row.get("action_type", "").strip()
        outcome_label = row.get("outcome_label", "").strip()

        if not sample_id:
            raise SimulationContractError(f"Row {index} is missing sample_id")
        if split not in SUPPORTED_SPLITS:
            raise SimulationContractError(f"Unsupported split for {sample_id}: {split}")
        if action_type not in SUPPORTED_ACTION_TYPES:
            raise SimulationContractError(f"Unsupported action_type: {action_type}")
        if outcome_label not in supported_outcomes:
            raise SimulationContractError(f"Unsupported outcome_label: {outcome_label}")

        previous_split = sample_splits.setdefault(sample_id, split)
        if previous_split != split:
            raise SimulationContractError(f"Sample {sample_id} appears in multiple splits")

        try:
            float(row.get("time", ""))
        except ValueError as exc:
            raise SimulationContractError(f"Row {index} has non-numeric time") from exc
        _validate_numeric_signals(row, index, fieldnames)

        action_types.add(action_type)
        outcome_labels.add(outcome_label)

    return action_types, outcome_labels, sample_splits


def validate_simulation_csv_contract(path: Path) -> SimulationContractReport:
    fieldnames, rows = _read_csv(path)
    _validate_required_columns(fieldnames)
    signal_counts = _count_signal_prefixes(fieldnames)
    _validate_signal_columns(signal_counts)
    _validate_required_signal_names(fieldnames)
    action_types, outcome_labels, sample_splits = _validate_rows(rows, fieldnames)

    correct_sample_count = sum(1 for split in sample_splits.values() if split == "correct")
    eval_sample_count = sum(1 for split in sample_splits.values() if split == "eval")
    if correct_sample_count == 0:
        raise SimulationContractError("CSV must contain at least one correct sample")
    if eval_sample_count == 0:
        raise SimulationContractError("CSV must contain at least one eval sample")

    return SimulationContractReport(
        path=path,
        row_count=len(rows),
        sample_count=len(sample_splits),
        correct_sample_count=correct_sample_count,
        eval_sample_count=eval_sample_count,
        action_types=sorted(action_types),
        outcome_labels=sorted(outcome_labels),
        signal_counts=signal_counts,
        field_specs=SimulationFieldSpec.default_specs(),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate simulation CSV input before diagnosis.")
    parser.add_argument("--csv-dataset", required=True, type=Path)
    args = parser.parse_args(argv)
    report = validate_simulation_csv_contract(args.csv_dataset)
    print(json.dumps(report.to_json_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
