"""Tests for the hybrid concept-KB retriever (BM25-only path; dense is skipped).

Locks the retrieval behaviours that the code review flagged as untested: evidence
boost ordering, dataset-question boost suppression, per-source dedup, empty result
on a no-signal query, and the [Sxx] citation mapping.
"""
from __future__ import annotations

import pytest

pytest.importorskip("rank_bm25")

from rag_project.knowledge.concept_kb import concept_chunk_to_evidence, load_concept_chunks
from rag_project.knowledge.hybrid_retrieval import HybridRetriever, expand_query


@pytest.fixture(scope="module")
def retriever() -> HybridRetriever:
    return HybridRetriever(use_dense=False)


def test_concept_chunks_load_and_are_nonempty():
    chunks = load_concept_chunks()
    assert len(chunks) >= 40
    assert all(c.get("source_ids") for c in chunks)


def test_clear_query_prefers_direct_clear_over_analogy(retriever: HybridRetriever):
    hits = retriever.search(["不考虑手指，正手高远球主要肌肉和发力顺序"], top_k=5, max_per_source=1)
    assert hits, "expected non-empty retrieval for a clear-technique query"
    layers = [c.get("evidence_level") for c, _ in hits]
    # at least one direct-clear layer in the top results
    assert any(l in {"coaching_direct_clear", "peer_reviewed_direct_clear", "overhead_multi_stroke"} for l in layers)


def test_dataset_query_suppresses_clear_boost_and_retrieves_dataset(retriever: HybridRetriever):
    # Q11-style: mentions 高远球 but asks for datasets -> boost must not bury the dataset chunk.
    hits = retriever.search(["有哪些数据集可用于正手高远球的 RAG 实验与传感分析"], top_k=5, max_per_source=2)
    source_ids = {s for c, _ in hits for s in c.get("source_ids", [])}
    assert "S16" in source_ids


def test_max_per_source_caps_hits(retriever: HybridRetriever):
    hits = retriever.search(["正手高远球肩内旋肘伸展前臂旋前"], top_k=10, max_per_source=1)
    primaries = [(c.get("source_ids") or ["?"])[0] for c, _ in hits]
    assert len(primaries) == len(set(primaries)), "max_per_source=1 must not repeat a primary source"


def test_no_match_query_returns_empty(retriever: HybridRetriever):
    # "dataset_..." substring suppresses clear-alias expansion (non-technique signal), and the
    # single underscore-joined token matches no chunk -> all-zero scores -> empty (the score>0 guard).
    assert retriever.search(["dataset_zzzqqq_nomatch_token"], top_k=5) == []


def test_implementation_layer_excluded_by_default(retriever: HybridRetriever):
    hits = retriever.search(["query 别名扩展 检索系统实现 hybrid"], top_k=10)
    assert all(c.get("evidence_level") != "implementation" for c, _ in hits)


def test_expand_query_does_not_flood_dataset_questions():
    assert expand_query("有哪些数据集") == "有哪些数据集"  # non-technique -> no clear-alias flood
    assert "forehand overhead clear" in expand_query("正手高远球发力顺序")  # technique -> expanded


def test_evidence_citation_uses_sxx(retriever: HybridRetriever):
    hits = retriever.search(["正手高远球进攻型与防守型区别"], top_k=3)
    ev = [concept_chunk_to_evidence(c, s) for c, s in hits]
    assert ev and all(e.source_ids and e.source_ids[0].startswith("S") for e in ev)
    assert all(isinstance(e.score, float) for e in ev)  # JSON-safe python float
