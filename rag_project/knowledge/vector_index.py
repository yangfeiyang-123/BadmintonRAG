from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from rag_project.knowledge.retrieval_eval import load_chunks

TOKEN_RE = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]", re.IGNORECASE)


def _tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_RE.finditer(text)]


def _document_text(chunk: dict[str, object]) -> str:
    keywords = " ".join(str(keyword) for keyword in chunk.get("keywords", []))
    return f"{chunk.get('title', '')} {keywords} {chunk.get('text', '')}"


def _term_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    counts = Counter(tokens)
    weighted = {token: count * idf[token] for token, count in counts.items() if token in idf}
    norm = math.sqrt(sum(value * value for value in weighted.values()))
    if not norm:
        return {}
    return {token: value / norm for token, value in weighted.items()}


@dataclass(frozen=True)
class VectorIndex:
    chunks: list[dict[str, object]]
    vocabulary: list[str]
    idf: dict[str, float]
    vectors: list[dict[str, float]]
    backend: str = "local_tfidf"

    def search(self, query: str, top_k: int = 5, max_per_source: int | None = None) -> list[dict[str, object]]:
        query_vector = _term_vector(_tokenize(query), self.idf)
        scored = []
        for chunk, vector in zip(self.chunks, self.vectors):
            score = sum(query_vector.get(token, 0.0) * weight for token, weight in vector.items())
            if score <= 0:
                continue
            result = dict(chunk)
            result["score"] = round(score, 6)
            scored.append(result)

        scored.sort(key=lambda row: (float(row["score"]), str(row["evidence_level"])), reverse=True)
        if max_per_source is None:
            return scored[:top_k]

        source_counts: Counter[str] = Counter()
        diversified = []
        for row in scored:
            source_id = str(row["source_id"])
            if source_counts[source_id] >= max_per_source:
                continue
            source_counts[source_id] += 1
            diversified.append(row)
            if len(diversified) >= top_k:
                break
        return diversified

    def to_jsonable(self) -> dict[str, object]:
        return {
            "backend": self.backend,
            "chunks": self.chunks,
            "vocabulary": self.vocabulary,
            "idf": self.idf,
            "vectors": self.vectors,
        }


def build_vector_index(chunks: list[dict[str, object]]) -> VectorIndex:
    documents = [_tokenize(_document_text(chunk)) for chunk in chunks]
    document_frequency: Counter[str] = Counter()
    for tokens in documents:
        document_frequency.update(set(tokens))

    total = len(documents)
    idf = {
        token: math.log((1 + total) / (1 + frequency)) + 1
        for token, frequency in sorted(document_frequency.items())
    }
    vectors = [_term_vector(tokens, idf) for tokens in documents]
    return VectorIndex(chunks=list(chunks), vocabulary=list(idf), idf=idf, vectors=vectors)


def write_vector_index(index: VectorIndex, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(index.to_jsonable(), ensure_ascii=False, indent=2), encoding="utf-8")


def load_vector_index(path: Path) -> VectorIndex:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return VectorIndex(
        chunks=list(payload["chunks"]),
        vocabulary=list(payload["vocabulary"]),
        idf={str(token): float(value) for token, value in payload["idf"].items()},
        vectors=[
            {str(token): float(value) for token, value in vector.items()}
            for vector in payload["vectors"]
        ],
        backend=str(payload.get("backend", "local_tfidf")),
    )


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    chunks = load_chunks(root / "sources" / "processed" / "text" / "chunks.jsonl")
    index = build_vector_index(chunks)
    write_vector_index(index, root / "sources" / "processed" / "vector" / "local_tfidf_index.json")


if __name__ == "__main__":
    main()
