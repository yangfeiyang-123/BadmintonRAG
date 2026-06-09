"""Hybrid retrieval over the concept knowledge base (INTEG-05).

BM25 (rank_bm25) + optional dense (bge-m3 via sentence-transformers) + metadata
filter (stroke/phase/evidence_level) + §10.2 evidence-boost rerank + §2.3 query
alias expansion. Dense is lazy and degrades gracefully to BM25-only when the model
or sentence-transformers is unavailable, so the system never hard-fails.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from rag_project.knowledge.concept_kb import (
    ANALOGY_LAYERS,
    DIRECT_CLEAR_LAYERS,
    concept_chunk_to_evidence,
    load_concept_chunks,
)
from rag_project.knowledge.evidence_index import EvidenceChunk

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MODEL_CACHE = _REPO_ROOT / ".models"
_EMB_CACHE = Path(__file__).resolve().parents[1] / "sources" / "processed" / "vector"
DENSE_MODEL = "BAAI/bge-m3"

# §2.3 query alias expansion (clear aliases always; kinetic-chain terms when relevant).
_CLEAR_ALIASES = [
    "正手高远球", "后场正手高远球", "forehand overhead clear", "backcourt forehand clear",
    "overhead forehand stroke", "high clear",
]
_CHAIN_ALIASES = [
    "proximal-distal sequence", "kinetic chain", "近端到远端", "鞭打链",
    "shoulder internal rotation", "forearm pronation", "trunk rotation",
    "elbow extension", "angular velocity", "segment acceleration",
]
_CHAIN_TRIGGERS = ["肌肉", "顺序", "发力", "muscle", "emg", "sequence", "角速度", "关节", "joint", "时序", "链"]
# Never expand into finger/grip terms (boundary §0).


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    toks = re.findall(r"[a-z0-9_]+", text)
    cjk = re.findall(r"[一-鿿]", text)
    toks += ["".join(p) for p in zip(cjk, cjk[1:])]
    toks += cjk
    return toks


def expand_query(text: str) -> str:
    low = text.lower()
    # Don't flood dataset/injury/methodology queries with clear-technique aliases —
    # it buries the dataset/injury evidence they ask for.
    if any(sig in text or sig in low for sig in _NON_TECHNIQUE_SIGNALS):
        return text
    parts = [text, *_CLEAR_ALIASES]
    if any(t in low for t in _CHAIN_TRIGGERS):
        parts += _CHAIN_ALIASES
    return " ".join(parts)


# Dataset/injury/methodology questions: even if they mention 高远球, the clear-technique
# evidence boost should NOT fire (it would bury the dataset/injury evidence the question asks for).
# Narrow signals (not bare "数据") so a clear-technique question isn't misrouted.
_NON_TECHNIQUE_SIGNALS = ["数据集", "dataset", "伤病", "损伤", "受伤", "风险", "肩痛", "emg", "肌电"]


def _question_requires_clear(text: str) -> bool:
    low = text.lower()
    if any(sig in text or sig in low for sig in _NON_TECHNIQUE_SIGNALS):
        return False
    return ("高远球" in text or "clear" in low) and "杀球" not in text and "smash" not in low


def _minmax(scores: list[float]) -> list[float]:
    if not scores:
        return scores
    lo, hi = min(scores), max(scores)
    if hi <= lo:
        return [0.0 for _ in scores]
    return [(s - lo) / (hi - lo) for s in scores]


class HybridRetriever:
    def __init__(self, chunks=None, use_dense: bool = True, dense_weight: float = 0.5):
        self.chunks = list(chunks) if chunks is not None else list(load_concept_chunks())
        self._docs = [
            self._doc_text(c) for c in self.chunks
        ]
        try:
            from rank_bm25 import BM25Okapi
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "hybrid retrieval requires rank-bm25; install requirements-hybrid.txt "
                "(rank-bm25, PyMuPDF, sentence-transformers)."
            ) from exc

        self._bm25 = BM25Okapi([_tokenize(d) for d in self._docs])
        self.dense_weight = dense_weight
        self._model = None
        self._emb = None
        self.dense_enabled = False
        if use_dense:
            self._try_init_dense()

    @staticmethod
    def _doc_text(c: dict) -> str:
        tags = " ".join(str(t) for t in c.get("retrieval_tags", []))
        aliases = " ".join(str(t) for t in c.get("stroke_aliases", []))
        return f"{c.get('text','')} {tags} {aliases}"

    def _try_init_dense(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
            import numpy as np
        except Exception:
            return
        try:
            self._model = SentenceTransformer(DENSE_MODEL, cache_folder=str(_MODEL_CACHE))
        except Exception:
            self._model = None
            return
        # cache embeddings keyed by a hash of the doc texts + model name
        # json.dumps (not "|".join) so a "|" inside a doc can't collide two partitions.
        key = hashlib.sha256((json.dumps(self._docs, ensure_ascii=False) + DENSE_MODEL).encode("utf-8")).hexdigest()[:16]
        _EMB_CACHE.mkdir(parents=True, exist_ok=True)
        cache_file = _EMB_CACHE / f"concept_dense_{key}.npy"
        if cache_file.exists():
            self._emb = np.load(cache_file)
        else:
            self._emb = self._model.encode(self._docs, normalize_embeddings=True, show_progress_bar=False)
            np.save(cache_file, self._emb)
        self.dense_enabled = True

    def _dense_scores(self, query: str) -> list[float]:
        import numpy as np

        qv = self._model.encode([query], normalize_embeddings=True, show_progress_bar=False)[0]
        return [float(x) for x in (np.asarray(self._emb) @ np.asarray(qv))]  # python float, JSON-safe

    def search(
        self,
        queries: list[str],
        top_k: int = 5,
        max_per_source: int = 2,
        filters: dict | None = None,
        prefer_direct_clear: bool = True,
        exclude_layers: frozenset = frozenset({"implementation"}),
    ) -> list[tuple[dict, float]]:
        raw = " ".join(queries)
        expanded = expand_query(raw)
        wants_clear = _question_requires_clear(raw)

        # BM25 on the expanded query (lexical recall + bilingual bridge); dense on the
        # RAW query (bge-m3 is multilingual and semantic — expansion would only dilute it).
        bm = self._bm25.get_scores(_tokenize(expanded))
        bm_n = _minmax(list(bm))
        if self.dense_enabled:
            dn = _minmax(self._dense_scores(raw))
            combined = [(1 - self.dense_weight) * b + self.dense_weight * d for b, d in zip(bm_n, dn)]
        else:
            combined = bm_n

        ranked: list[tuple[int, float]] = []
        for i, base in enumerate(combined):
            c = self.chunks[i]
            if str(c.get("evidence_level", "")) in exclude_layers:
                continue
            if not self._passes_filter(c, filters):
                continue
            score = base
            # §10.2 evidence boost: only when the question is about the clear itself,
            # so dataset/injury/analogy-classification questions are not distorted by a
            # blanket direct-clear boost (which otherwise pushes needed sources down).
            if base > 0 and prefer_direct_clear and wants_clear:
                layer = str(c.get("evidence_level", ""))
                if layer in DIRECT_CLEAR_LAYERS:
                    score += 0.20
                if layer == "coaching_direct_clear":
                    score += 0.10
                if layer == "peer_reviewed_direct_clear":
                    score += 0.10
                if layer in ANALOGY_LAYERS:
                    score -= 0.15
            if score > 0:
                ranked.append((i, score))

        ranked.sort(key=lambda x: (-x[1], x[0]))
        out: list[tuple[dict, float]] = []
        per_source: dict[str, int] = {}
        for i, score in ranked:
            c = self.chunks[i]
            primary = (c.get("source_ids") or ["?"])[0]
            if per_source.get(primary, 0) >= max_per_source:
                continue
            per_source[primary] = per_source.get(primary, 0) + 1
            out.append((c, score))
            if len(out) >= top_k:
                break
        return out

    @staticmethod
    def _passes_filter(chunk: dict, filters: dict | None) -> bool:
        if not filters:
            return True
        for field in ("stroke", "evidence_level", "phase", "phase_id"):
            allowed = filters.get(field)
            if allowed and str(chunk.get(field, "")) not in set(allowed):
                return False
        return True

    def retrieve_evidence(
        self, queries: list[str], top_k: int = 5, max_per_source: int = 2, **kw
    ) -> list[EvidenceChunk]:
        hits = self.search(queries, top_k=top_k, max_per_source=max_per_source, **kw)
        return [concept_chunk_to_evidence(c, score=s) for c, s in hits]


_DEFAULT: HybridRetriever | None = None


def get_default_retriever(use_dense: bool = True) -> HybridRetriever:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = HybridRetriever(use_dense=use_dense)
    return _DEFAULT
