#!/usr/bin/env python3
"""Self-contained retrieval evaluation for the badminton forehand-clear RAG KB.

Makes the gold set *live* (fixes audit EVAL-01: gold_questions_zh.jsonl was never
consumed). Builds a lightweight BM25 index over data/chunks.jsonl, applies the
§10.2 evidence boost (favour direct_clear, penalise smash_analogy when the query
is about clear), and computes the rubric's retrieval metrics (recall@k, hit_rate,
MRR) against each gold question's must_retrieve. Also loads no_overclaim_tests.jsonl
and exposes the deterministic scoring helpers (forbidden-phrase / negate checks)
for when an answer string is supplied.

Stdlib only — runs anywhere with python3. This is the TF-IDF/BM25 baseline, NOT the
full bge-m3 hybrid+reranker target architecture (see citation_rubric.md §5).

Usage:
    python evaluate_rag.py                       # run retrieval eval, print JSON
    python evaluate_rag.py --k 5 --out results.json
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math, re
from collections import Counter, defaultdict
from pathlib import Path

PKG = Path(__file__).resolve().parent
CHUNKS = PKG / "data" / "chunks.jsonl"
GOLD = PKG / "gold_questions_zh.jsonl"
NEG = PKG / "no_overclaim_tests.jsonl"
CATALOG = PKG / "badminton_forehand_clear_sources.csv"
SCHEMA_VERSION = "1.1"
SEED = 0

# Evidence layers that count as "direct clear" for the §10.2 boost.
DIRECT_LAYERS = {"coaching_direct_clear", "peer_reviewed_direct_clear", "overhead_multi_stroke"}
ANALOGY_LAYERS = {"smash_analogy", "emg_smash_analogy", "msk_methodological"}


def tokenize(text: str) -> list[str]:
    """Char-bigrams for CJK + lowercased latin/numeric word tokens. Good enough for a baseline."""
    text = text.lower()
    toks: list[str] = []
    toks += re.findall(r"[a-z0-9_]+", text)
    cjk = re.findall(r"[一-鿿]", text)
    toks += ["".join(p) for p in zip(cjk, cjk[1:])]  # bigrams
    toks += cjk  # unigrams too, helps short queries
    return toks


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.docs = docs
        self.N = len(docs)
        self.k1, self.b = k1, b
        self.dl = [len(d) for d in docs]
        self.avgdl = sum(self.dl) / max(self.N, 1)
        self.tf = [Counter(d) for d in docs]
        df: Counter = Counter()
        for d in self.tf:
            df.update(d.keys())
        self.idf = {t: math.log(1 + (self.N - n + 0.5) / (n + 0.5)) for t, n in df.items()}

    def score(self, q: list[str], i: int) -> float:
        s = 0.0
        tf = self.tf[i]
        denom_dl = self.k1 * (1 - self.b + self.b * self.dl[i] / max(self.avgdl, 1e-9))
        for t in q:
            if t not in tf:
                continue
            s += self.idf.get(t, 0.0) * (tf[t] * (self.k1 + 1)) / (tf[t] + denom_dl)
        return s


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def question_requires_clear(q: str) -> bool:
    return ("高远球" in q or "clear" in q.lower()) and "杀球" not in q


def retrieve(bm25: BM25, chunks: list[dict], query: str, k: int, boost: bool) -> list[int]:
    q = tokenize(query)
    wants_clear = question_requires_clear(query)
    scored = []
    for i, c in enumerate(chunks):
        s = bm25.score(q, i)
        if boost and s > 0:
            lay = c["evidence_level"]
            if lay in DIRECT_LAYERS:
                s += 0.20 * s if False else 0.0  # multiplicative kept off; additive below
            # §10.2-style additive boosts (scaled to bm25 magnitude)
            scale = 1.0
            if lay in DIRECT_LAYERS:
                s += 0.20 * scale
            if lay == "coaching_direct_clear":
                s += 0.10 * scale
            if lay == "peer_reviewed_direct_clear":
                s += 0.10 * scale
            if wants_clear and lay in ANALOGY_LAYERS:
                s -= 0.15 * scale
        scored.append((s, i))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [i for s, i in scored[:k] if s > 0]


def eval_retrieval(chunks: list[dict], gold: list[dict], k: int, boost: bool) -> dict:
    texts = [c["text"] + " " + " ".join(c.get("retrieval_tags", [])) for c in chunks]
    bm25 = BM25([tokenize(t) for t in texts])
    cat_ids = {r["id"] for r in csv.DictReader(CATALOG.open(encoding="utf-8"))}

    per_q = []
    recalls, hits, rrs = [], [], []
    for item in gold:
        if item.get("type") != "retrieval":
            continue
        must = [s for s in item.get("must_retrieve", [])]
        if not must:
            continue
        order = retrieve(bm25, chunks, item["question"], k, boost)
        # rank-ordered source ids (first occurrence)
        ranked_sources, seen = [], set()
        for i in order:
            for s in chunks[i]["source_ids"]:
                if s not in seen:
                    seen.add(s); ranked_sources.append(s)
        retrieved = set(ranked_sources)
        recall = len(retrieved & set(must)) / len(must)
        hit = 1.0 if retrieved & set(must) else 0.0
        rr = 0.0
        for rank, s in enumerate(ranked_sources, 1):
            if s in must:
                rr = 1.0 / rank
                break
        missing_from_corpus = [s for s in must if s not in {x for c in chunks for x in c["source_ids"]}]
        recalls.append(recall); hits.append(hit); rrs.append(rr)
        per_q.append({
            "qid": item["qid"], "recall@k": round(recall, 3), "hit": hit,
            "rr": round(rr, 3), "n_must": len(must),
            "found": sorted(retrieved & set(must)), "missed": sorted(set(must) - retrieved),
            "uncovered_by_corpus": missing_from_corpus,
        })
    n = max(len(per_q), 1)
    return {
        "k": k, "boost": boost,
        "macro": {
            "recall@k": round(sum(recalls) / n, 3),
            "hit_rate@k": round(sum(hits) / n, 3),
            "MRR": round(sum(rrs) / n, 3),
            "n_questions": len(per_q),
        },
        "per_question": per_q,
    }


def score_answer_negative(answer: str, test: dict) -> dict:
    """Deterministic scoring of a negative (no-overclaim) test given a model answer string."""
    a = answer
    negate = any(p in a for p in test.get("must_negate", []))
    reframe = sum(1 for p in test.get("must_reframe", []) if p in a)
    forbidden = [p for p in test.get("forbidden_phrases", []) if p in a]
    return {
        "qid": test["qid"], "negate_pass": negate,
        "reframe_hits": reframe, "reframe_total": len(test.get("must_reframe", [])),
        "forbidden_violations": forbidden,
        "pass": bool(negate and not forbidden),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--no-boost", action="store_true")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    chunks = load_jsonl(CHUNKS)
    gold = load_jsonl(GOLD)
    neg = load_jsonl(NEG)

    result = {
        "run_metadata": {
            "seed": SEED,
            "retrieval_backend": "bm25_evidence_boost(baseline,not_hybrid)",
            "embedding_model": "none(tf-idf/bm25)",
            "reranker": "evidence_boost(§10.2)" if not args.no_boost else "none",
            "n_chunks": len(chunks),
            "chunks_sha256": sha256_file(CHUNKS),
            "gold_set_sha256": sha256_file(GOLD),
            "chunk_schema_version": SCHEMA_VERSION,
        },
        "retrieval": eval_retrieval(chunks, gold, args.k, boost=not args.no_boost),
        "retrieval_at5": eval_retrieval(chunks, gold, 5, boost=not args.no_boost)["macro"],
        "negative_tests_loaded": [t["qid"] for t in neg],
        "note": "内容/引用/反幻觉指标需要模型答案字符串; score_answer_negative() 已提供确定性判分器。检索为 BM25 基线,非 bge-m3 hybrid 目标架构。",
    }
    out = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(out, encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
