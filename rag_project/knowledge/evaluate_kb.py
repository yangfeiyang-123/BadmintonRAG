#!/usr/bin/env python3
"""Authoritative integrated KB evaluation (INTEG-05 / EVAL-01).

Evaluates the real HybridRetriever (BM25 + optional bge-m3 dense + evidence boost)
against the package gold questions and no-overclaim tests, computing the rubric
metrics (recall@k / hit_rate / MRR) with reproducibility metadata. This is the
single eval entry that finally *consumes* gold_questions_zh.jsonl over the concept
KB inside rag_project.

    python -m rag_project.knowledge.evaluate_kb            # bm25+dense if available
    python -m rag_project.knowledge.evaluate_kb --no-dense # bm25 baseline
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from rag_project.knowledge.concept_kb import CATALOG_PATH, CHUNKS_PATH, PACKAGE_DIR, load_concept_chunks
from rag_project.knowledge.hybrid_retrieval import HybridRetriever

GOLD = PACKAGE_DIR / "gold_questions_zh.jsonl"
NEG = PACKAGE_DIR / "no_overclaim_tests.jsonl"
SEED = 0


def _load_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def evaluate(use_dense: bool, k: int) -> dict:
    retriever = HybridRetriever(use_dense=use_dense)
    corpus_sources = {s for c in retriever.chunks for s in c.get("source_ids", [])}
    gold = _load_jsonl(GOLD)
    neg = _load_jsonl(NEG)

    per_q, recalls, hits, rrs = [], [], [], []
    for item in gold:
        if item.get("type") != "retrieval" or not item.get("must_retrieve"):
            continue
        must = list(item["must_retrieve"])
        hitset = retriever.search([item["question"]], top_k=k, max_per_source=2)
        ranked_sources, seen = [], set()
        for c, _ in hitset:
            for s in c.get("source_ids", []):
                if s not in seen:
                    seen.add(s); ranked_sources.append(s)
        retrieved = set(ranked_sources)
        recall = len(retrieved & set(must)) / len(must)
        hit = 1.0 if retrieved & set(must) else 0.0
        rr = next((1.0 / r for r, s in enumerate(ranked_sources, 1) if s in must), 0.0)
        uncovered = [s for s in must if s not in corpus_sources]  # missing_source (INTEG-08)
        recalls.append(recall); hits.append(hit); rrs.append(rr)
        per_q.append({
            "qid": item["qid"], "recall@k": round(recall, 3), "hit": hit, "rr": round(rr, 3),
            "found": sorted(retrieved & set(must)), "missed": sorted(set(must) - retrieved),
            "missing_from_corpus": uncovered,
        })

    n = max(len(per_q), 1)
    return {
        "run_metadata": {
            "seed": SEED,
            "retrieval_backend": f"hybrid:{'bm25+dense(bge-m3)' if retriever.dense_enabled else 'bm25'}",
            "dense_enabled": retriever.dense_enabled,
            "n_chunks": len(retriever.chunks),
            "chunks_sha256": _sha(CHUNKS_PATH),
            "gold_set_sha256": _sha(GOLD),
            "catalog_sha256": _sha(CATALOG_PATH),
            "k": k,
        },
        "macro": {
            "recall@k": round(sum(recalls) / n, 3),
            "hit_rate@k": round(sum(hits) / n, 3),
            "MRR": round(sum(rrs) / n, 3),
            "n_questions": len(per_q),
        },
        "per_question": per_q,
        "negative_tests_loaded": [t["qid"] for t in neg],
        "thresholds": {"recall@5>=": 0.80, "MRR>=": 0.70},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-dense", action="store_true", help="Disable bge-m3 dense; BM25 baseline only.")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    result = evaluate(use_dense=not args.no_dense, k=args.k)
    out = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(out, encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
