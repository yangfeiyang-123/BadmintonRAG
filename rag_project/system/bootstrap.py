from __future__ import annotations

import argparse
import json
from pathlib import Path

from rag_project.knowledge.retrieval_eval import DEFAULT_EVAL_SET, evaluate_index_retrieval, write_default_eval_set
from rag_project.knowledge.source_catalog import load_download_results, write_source_catalog
from rag_project.knowledge.text_corpus import load_source_catalog, write_text_corpus
from rag_project.knowledge.vector_index import build_vector_index, load_vector_index, write_vector_index
from rag_project.knowledge.retrieval_eval import load_chunks


ARTIFACTS = {
    "download_results": ("sources", "raw", "metadata", "download_results.csv"),
    "source_catalog_csv": ("sources", "processed", "metadata", "source_catalog.csv"),
    "source_catalog_json": ("sources", "processed", "metadata", "source_catalog.json"),
    "chunks_jsonl": ("sources", "processed", "text", "chunks.jsonl"),
    "vector_index": ("sources", "processed", "vector", "local_tfidf_index.json"),
    "retrieval_eval": ("sources", "processed", "metadata", "retrieval_eval.json"),
    "retrieval_eval_results": ("sources", "processed", "metadata", "retrieval_eval_results.json"),
}


def _artifact_status(root: Path) -> dict[str, dict[str, object]]:
    statuses: dict[str, dict[str, object]] = {}
    for name, parts in ARTIFACTS.items():
        path = root.joinpath(*parts)
        statuses[name] = {
            "path": str(path),
            "exists": path.exists(),
            "bytes": path.stat().st_size if path.exists() else 0,
        }
    return statuses


def doctor_system(root: Path | None = None) -> dict[str, object]:
    project_root = root or Path(__file__).resolve().parents[1]
    artifacts = _artifact_status(project_root)
    required = ["download_results", "source_catalog_csv", "chunks_jsonl", "vector_index", "retrieval_eval_results"]
    return {
        "root": str(project_root),
        "ready": all(bool(artifacts[name]["exists"]) for name in required),
        "artifacts": artifacts,
    }


def _write_catalog(root: Path) -> None:
    rows = load_download_results(root / "sources" / "raw" / "metadata" / "download_results.csv")
    output = root / "sources" / "processed" / "metadata"
    write_source_catalog(rows, output / "source_catalog.csv", output / "source_catalog.json")


def _write_chunks(root: Path) -> None:
    rows = load_source_catalog(root / "sources" / "processed" / "metadata" / "source_catalog.csv")
    write_text_corpus(rows, root / "sources" / "processed" / "text" / "chunks.jsonl")


def _write_vector_index(root: Path) -> None:
    chunks = load_chunks(root / "sources" / "processed" / "text" / "chunks.jsonl")
    index = build_vector_index(chunks)
    write_vector_index(index, root / "sources" / "processed" / "vector" / "local_tfidf_index.json")


def _write_retrieval_eval(root: Path) -> None:
    eval_path = root / "sources" / "processed" / "metadata" / "retrieval_eval.json"
    if not eval_path.exists():
        write_default_eval_set(eval_path)
    chunks = load_chunks(root / "sources" / "processed" / "text" / "chunks.jsonl")
    index = build_vector_index(chunks)
    eval_items = json.loads(eval_path.read_text(encoding="utf-8"))
    if not eval_items:
        eval_items = DEFAULT_EVAL_SET
    result = evaluate_index_retrieval(index, eval_items)
    output = root / "sources" / "processed" / "metadata" / "retrieval_eval_results.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


def bootstrap_system(root: Path | None = None) -> dict[str, object]:
    project_root = root or Path(__file__).resolve().parents[1]
    _write_catalog(project_root)
    _write_chunks(project_root)
    _write_vector_index(project_root)
    _write_retrieval_eval(project_root)
    return doctor_system(project_root)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap or inspect BadmintonRAG processed artifacts.")
    parser.add_argument("command", choices=["doctor", "bootstrap"], help="Run a health check or regenerate artifacts.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    if args.command == "doctor":
        result = doctor_system(args.root)
    else:
        result = bootstrap_system(args.root)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
