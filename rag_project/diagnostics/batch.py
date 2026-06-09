from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from rag_project.diagnostics.csv_adapter import load_dataset_from_csv
from rag_project.diagnostics.dataset import DiagnosticDataset, load_diagnostic_dataset
from rag_project.diagnostics.diagnose import diagnose_sample
from rag_project.diagnostics.llm_report import generate_diagnostic_report
from rag_project.diagnostics.schemas import DiagnosisReport
from rag_project.diagnostics.templates import build_correct_template
from rag_project.knowledge.evidence_index import EvidenceChunk, build_evidence_index, load_classified_sources, retrieve_evidence
from rag_project.knowledge.vector_index import VectorIndex, load_vector_index
from rag_project.llm.openai_compatible import LLMConfig, OpenAICompatibleClient


ROOT = Path(__file__).resolve().parents[1]


def _report_payload(report: DiagnosisReport, evidence: list[EvidenceChunk], retrieval_backend: str) -> dict[str, object]:
    from rag_project.knowledge.concept_kb import evidence_layer_label, load_crosswalk, resolve_source_url

    crosswalk = load_crosswalk()
    payload = asdict(report)
    payload["outcome_label"] = report.outcome_label.value
    payload["retrieval_backend"] = retrieval_backend
    evidence_items = []
    for chunk in evidence:
        sids = list(chunk.source_ids) or [crosswalk.to_package(chunk.source_id)]
        urls = {sid: resolve_source_url(sid) or resolve_source_url(chunk.source_id) for sid in sids}
        evidence_items.append(
            {
                "chunk_id": chunk.chunk_id,
                "source_id": chunk.source_id,
                "source_ids": sids,
                "citation": "".join(f"[{sid}]" for sid in sids),
                "title": chunk.title,
                "source_class": chunk.source_class,
                "evidence_level": chunk.evidence_level,
                "evidence_layer_zh": evidence_layer_label(chunk.evidence_level),
                "urls": {k: v for k, v in urls.items() if v},  # original-source links
                "score": chunk.score,
                "artifact_path": chunk.artifact_path,
            }
        )
    payload["evidence"] = evidence_items
    return payload


def _load_default_evidence() -> list[EvidenceChunk]:
    sources = load_classified_sources(ROOT / "sources" / "raw" / "metadata" / "download_results.csv")
    return build_evidence_index(sources)


def _load_default_vector_index() -> VectorIndex:
    return load_vector_index(ROOT / "sources" / "processed" / "vector" / "local_tfidf_index.json")


def _vector_rows_to_evidence(rows: list[dict[str, object]]) -> list[EvidenceChunk]:
    return [
        EvidenceChunk(
            chunk_id=str(row["chunk_id"]),
            source_id=str(row["source_id"]),
            title=str(row["title"]),
            source_class=str(row["source_class"]),
            artifact_path=str(row["artifact_path"]),
            text=str(row["text"]),
            token_count=int(row["token_count"]),
            evidence_level=str(row["evidence_level"]),
            score=float(row.get("score", 0.0)),
        )
        for row in rows
    ]


def evidence_chunks_from_payload(rows: list[dict[str, object]]) -> list[EvidenceChunk]:
    return [
        EvidenceChunk(
            chunk_id=str(row["chunk_id"]),
            source_id=str(row["source_id"]),
            title=str(row["title"]),
            source_class=str(row["source_class"]),
            artifact_path=str(row["artifact_path"]),
            text=str(row["text"]),
            token_count=int(row["token_count"]),
            evidence_level=str(row["evidence_level"]),
            score=float(row.get("score", 0.0)),
        )
        for row in rows
    ]


def _retrieve_for_report(
    queries: list[str],
    retrieval_backend: str,
    evidence_chunks: list[EvidenceChunk] | None,
    vector_index: VectorIndex | None,
) -> tuple[str, list[EvidenceChunk]]:
    if retrieval_backend == "keyword":
        chunks = evidence_chunks if evidence_chunks is not None else _load_default_evidence()
        return "keyword", retrieve_evidence(chunks, queries, top_k=4, max_per_source=1)
    if retrieval_backend == "vector":
        index = vector_index if vector_index is not None else _load_default_vector_index()
        rows = index.search(" ".join(queries), top_k=4, max_per_source=1)
        return f"vector:{index.backend}", _vector_rows_to_evidence(rows)
    if retrieval_backend == "hybrid":
        # INTEG-05: retrieve over the S01–S21 concept KB with BM25(+dense) + §10.2 evidence boost.
        from rag_project.knowledge.hybrid_retrieval import get_default_retriever

        retriever = get_default_retriever()
        evidence = retriever.retrieve_evidence(queries, top_k=4, max_per_source=1)
        return f"hybrid:{'bm25+dense' if retriever.dense_enabled else 'bm25'}", evidence
    raise ValueError(f"Unsupported retrieval_backend: {retrieval_backend}")


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_batch_diagnosis(
    dataset_path: Path,
    output_dir: Path,
    evidence_chunks: list[EvidenceChunk] | None = None,
    retrieval_backend: str = "keyword",
    vector_index: VectorIndex | None = None,
    use_llm: bool = False,
) -> dict[str, object]:
    dataset = load_diagnostic_dataset(dataset_path)
    result = run_batch_diagnosis_dataset(
        dataset,
        evidence_chunks=evidence_chunks,
        retrieval_backend=retrieval_backend,
        vector_index=vector_index,
        use_llm=use_llm,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    markdown_paths = []
    for report in result["reports"]:
        markdown = str(report.pop("markdown"))
        markdown_path = reports_dir / f"{report['sample_id']}.md"
        markdown_path.write_text(markdown, encoding="utf-8")
        markdown_paths.append(str(markdown_path))

    result["summary"]["json_report"] = str(output_dir / "diagnosis_reports.json")  # type: ignore[index]
    result["summary"]["markdown_reports"] = markdown_paths  # type: ignore[index]
    _write_json(output_dir / "diagnosis_reports.json", result["reports"])
    _write_json(output_dir / "summary.json", result["summary"])
    return result


def run_batch_diagnosis_dataset(
    dataset: DiagnosticDataset,
    evidence_chunks: list[EvidenceChunk] | None = None,
    retrieval_backend: str = "keyword",
    vector_index: VectorIndex | None = None,
    use_llm: bool = False,
) -> dict[str, object]:
    template = build_correct_template(f"{dataset.dataset_id}_correct_template", dataset.correct_samples)

    client = OpenAICompatibleClient(LLMConfig.from_env()) if use_llm else None

    report_payloads = []
    resolved_backend = "keyword"
    for sample in dataset.eval_samples:
        diagnosis = diagnose_sample(sample, template)
        resolved_backend, evidence = _retrieve_for_report(
            diagnosis.evidence_queries,
            retrieval_backend=retrieval_backend,
            evidence_chunks=evidence_chunks,
            vector_index=vector_index,
        )
        markdown = generate_diagnostic_report(diagnosis, evidence, client=client)
        report_payload = _report_payload(diagnosis, evidence, resolved_backend)
        report_payload["markdown"] = markdown
        report_payloads.append(report_payload)

    outcome_counts = Counter(str(report["outcome_label"]) for report in report_payloads)
    summary = {
        "dataset_id": dataset.dataset_id,
        "action_type": dataset.action_type,
        "correct_samples": len(dataset.correct_samples),
        "evaluated_samples": len(dataset.eval_samples),
        "retrieval_backend": resolved_backend,
        "outcome_counts": dict(sorted(outcome_counts.items())),
    }
    return {"summary": summary, "reports": report_payloads}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run batch forehand-clear diagnostics from a simulation dataset.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--dataset", type=Path, help="Path to dataset JSON with correct_samples/eval_samples.")
    source.add_argument("--csv-dataset", type=Path, help="Path to simulation CSV rows using joint_* and muscle_* columns.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for JSON and Markdown reports.")
    parser.add_argument(
        "--retrieval-backend",
        choices=["keyword", "vector", "hybrid"],
        default="keyword",
        help="Evidence retrieval backend. 'hybrid' = concept KB BM25(+dense bge-m3) with evidence boost.",
    )
    parser.add_argument("--llm", action="store_true", help="Call an OpenAI-compatible LLM using BADMINTON_LLM_* env vars.")
    args = parser.parse_args()

    if args.csv_dataset:
        dataset = load_dataset_from_csv(args.csv_dataset)
        result = run_batch_diagnosis_dataset(
            dataset,
            retrieval_backend=args.retrieval_backend,
            use_llm=args.llm,
        )
        args.output_dir.mkdir(parents=True, exist_ok=True)
        reports_dir = args.output_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        markdown_paths = []
        for report in result["reports"]:
            markdown = str(report.pop("markdown"))
            markdown_path = reports_dir / f"{report['sample_id']}.md"
            markdown_path.write_text(markdown, encoding="utf-8")
            markdown_paths.append(str(markdown_path))
        result["summary"]["json_report"] = str(args.output_dir / "diagnosis_reports.json")  # type: ignore[index]
        result["summary"]["markdown_reports"] = markdown_paths  # type: ignore[index]
        _write_json(args.output_dir / "diagnosis_reports.json", result["reports"])
        _write_json(args.output_dir / "summary.json", result["summary"])
    else:
        result = run_batch_diagnosis(
            args.dataset,
            args.output_dir,
            retrieval_backend=args.retrieval_backend,
            use_llm=args.llm,
        )
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
