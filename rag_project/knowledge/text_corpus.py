from __future__ import annotations

import csv
import json
from pathlib import Path

from rag_project.knowledge.evidence_index import EvidenceChunk, build_evidence_index
from rag_project.knowledge.source_catalog import load_download_results


def _keywords(chunk: EvidenceChunk, limit: int = 10) -> list[str]:
    candidates = []
    for token in (chunk.title + " " + chunk.text).lower().replace("-", " ").split():
        cleaned = "".join(ch for ch in token if ch.isalnum() or "\u4e00" <= ch <= "\u9fff")
        if len(cleaned) < 4:
            continue
        if cleaned not in candidates:
            candidates.append(cleaned)
        if len(candidates) >= limit:
            break
    return candidates


def load_source_catalog(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def build_text_corpus(catalog_rows: list[dict[str, str]], chunk_size: int = 160, overlap: int = 35) -> list[dict[str, object]]:
    ingestible = [row for row in catalog_rows if row.get("ingest_text") == "true"]
    chunks = build_evidence_index(ingestible, chunk_size=chunk_size, overlap=overlap)
    return [
        {
            "chunk_id": chunk.chunk_id,
            "source_id": chunk.source_id,
            "source_class": chunk.source_class,
            "evidence_level": chunk.evidence_level,
            "title": chunk.title,
            "section": "",
            "paragraph_index": index,
            "artifact_path": chunk.artifact_path,
            "text": chunk.text,
            "token_count": chunk.token_count,
            "keywords": _keywords(chunk),
        }
        for index, chunk in enumerate(chunks, start=1)
    ]


def write_text_corpus(catalog_rows: list[dict[str, str]], output_path: Path, chunk_size: int = 160, overlap: int = 35) -> None:
    corpus = build_text_corpus(catalog_rows, chunk_size=chunk_size, overlap=overlap)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for chunk in corpus:
            handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    catalog_path = root / "sources" / "processed" / "metadata" / "source_catalog.csv"
    if catalog_path.exists():
        rows = load_source_catalog(catalog_path)
    else:
        rows = load_download_results(root / "sources" / "raw" / "metadata" / "download_results.csv")
    write_text_corpus(rows, root / "sources" / "processed" / "text" / "chunks.jsonl")


if __name__ == "__main__":
    main()
