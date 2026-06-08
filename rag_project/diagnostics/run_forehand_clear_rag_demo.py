from __future__ import annotations

import json
from pathlib import Path

from rag_project.diagnostics.diagnose import diagnose_sample
from rag_project.diagnostics.explain import render_diagnosis_markdown
from rag_project.diagnostics.schemas import DiagnosticSample
from rag_project.diagnostics.templates import build_correct_template
from rag_project.knowledge.evidence_index import build_evidence_index, load_classified_sources, retrieve_evidence


ROOT = Path(__file__).resolve().parents[1]


def _load_samples(path: Path) -> list[DiagnosticSample]:
    payloads = json.loads(path.read_text(encoding="utf-8"))
    return [DiagnosticSample.from_dict(payload) for payload in payloads]


def run_rag_demo(output_dir: Path) -> list[Path]:
    correct = _load_samples(ROOT / "examples" / "forehand_clear_correct_samples.json")
    eval_samples = _load_samples(ROOT / "examples" / "forehand_clear_eval_samples.json")
    template = build_correct_template("forehand_clear_correct_v1", correct)

    sources = load_classified_sources(ROOT / "sources" / "raw" / "metadata" / "download_results.csv")
    chunks = build_evidence_index(sources)

    output_dir.mkdir(parents=True, exist_ok=True)
    report_paths: list[Path] = []
    for sample in eval_samples:
        diagnosis = diagnose_sample(sample, template)
        evidence = retrieve_evidence(chunks, diagnosis.evidence_queries, top_k=4)
        markdown = render_diagnosis_markdown(diagnosis, evidence)
        output_path = output_dir / f"{sample.sample_id}_rag_report.md"
        output_path.write_text(markdown, encoding="utf-8")
        report_paths.append(output_path)
    return report_paths


if __name__ == "__main__":
    run_rag_demo(ROOT / "outputs" / "forehand_clear_rag_reports")
