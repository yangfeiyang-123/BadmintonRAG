from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from rag_project.knowledge.extract_text import extract_html_text
from rag_project.knowledge.source_classifier import classify_source


EVIDENCE_SOURCE_CLASSES = {"official_manual", "full_text_pdf", "full_text_html"}


@dataclass(frozen=True)
class EvidenceChunk:
    chunk_id: str
    source_id: str
    title: str
    source_class: str
    artifact_path: str
    text: str
    token_count: int
    score: float = 0.0


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z0-9_-]*|[\u4e00-\u9fff]+", text.lower())


def _split_words(text: str, chunk_size: int, overlap: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    step = max(chunk_size - overlap, 1)
    for start in range(0, len(words), step):
        chunk_words = words[start : start + chunk_size]
        if len(chunk_words) < 6 and chunks:
            break
        chunks.append(" ".join(chunk_words))
    return chunks


def _first_existing_artifact(downloaded_files: str) -> Path | None:
    for raw_path in downloaded_files.split(";"):
        if not raw_path.strip():
            continue
        path = Path(raw_path.replace("\\", "/"))
        if path.exists():
            return path
    return None


def load_classified_sources(download_results_path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with download_results_path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            source_class = classify_source(row["id"], row["category"], row["status"], row["notes"])
            rows.append({**row, "source_class": source_class})
    return rows


def build_evidence_index(sources: list[dict[str, str]], chunk_size: int = 160, overlap: int = 35) -> list[EvidenceChunk]:
    chunks: list[EvidenceChunk] = []
    for source in sources:
        source_class = source.get("source_class") or classify_source(
            source.get("id", ""), source.get("category", ""), source.get("status", ""), source.get("notes", "")
        )
        if source_class not in EVIDENCE_SOURCE_CLASSES:
            continue

        artifact = _first_existing_artifact(source.get("downloaded_files", ""))
        if artifact is None or artifact.suffix.lower() != ".html":
            continue

        text = extract_html_text(artifact)
        if not text:
            continue
        for index, chunk_text in enumerate(_split_words(text, chunk_size, overlap), start=1):
            tokens = _tokenize(chunk_text)
            if len(tokens) < 8:
                continue
            chunks.append(
                EvidenceChunk(
                    chunk_id=f"{source.get('id', 'unknown')}::{index}",
                    source_id=source.get("id", "unknown"),
                    title=source.get("title", ""),
                    source_class=source_class,
                    artifact_path=str(artifact),
                    text=chunk_text,
                    token_count=len(tokens),
                )
            )
    return chunks


def retrieve_evidence(chunks: list[EvidenceChunk], queries: list[str], top_k: int = 5) -> list[EvidenceChunk]:
    query_tokens = set(_tokenize(" ".join(queries)))
    if not query_tokens:
        return []

    scored: list[EvidenceChunk] = []
    for chunk in chunks:
        chunk_tokens = _tokenize(chunk.text + " " + chunk.title + " " + chunk.source_id)
        if not chunk_tokens:
            continue
        token_set = set(chunk_tokens)
        overlap = query_tokens & token_set
        if not overlap:
            continue
        score = len(overlap) + (len(overlap) / max(len(query_tokens), 1))
        if "forehand" in overlap or "clear" in overlap:
            score += 0.5
        scored.append(
            EvidenceChunk(
                chunk_id=chunk.chunk_id,
                source_id=chunk.source_id,
                title=chunk.title,
                source_class=chunk.source_class,
                artifact_path=chunk.artifact_path,
                text=chunk.text,
                token_count=chunk.token_count,
                score=round(score, 4),
            )
        )

    scored.sort(key=lambda item: (item.score, item.source_id), reverse=True)
    return scored[:top_k]
