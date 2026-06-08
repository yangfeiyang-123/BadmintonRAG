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
