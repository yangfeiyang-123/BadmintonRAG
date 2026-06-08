from __future__ import annotations

import json
from pathlib import Path

from rag_project.knowledge.evidence_index import EvidenceChunk, retrieve_evidence


DEFAULT_EVAL_SET = [
    {
        "question": "正手高远球下肢参与有哪些证据？",
        "queries": ["forehand clear lower limb trunk rotation backcourt"],
        "expected_source_ids": ["CLEAR_ZHAO_LOWER_LIMB"],
    },
    {
        "question": "专家和新手正手高远球差异是什么？",
        "queries": ["novice expert backcourt forehand clear stroke differences"],
        "expected_source_ids": ["CLEAR_HUANG_EXPERT_NOVICE"],
    },
    {
        "question": "上手正手击球的手臂和躯干顺序有什么证据？",
        "queries": ["overhead forehand stroke arm trunk action sequence"],
        "expected_source_ids": ["OVERHEAD_WANG_ARM_TRUNK"],
    },
    {
        "question": "动力链和躯干旋转为什么会影响击球质量？",
        "queries": ["badminton forehand stroke trunk rotation kinetic chain"],
        "expected_source_ids": ["SMASH_ZHANG_XFACTOR", "OVERHEAD_WANG_ARM_TRUNK"],
    },
    {
        "question": "正手高远球标准动作和官方教学资料有哪些？",
        "queries": ["BWF coach forehand clear badminton manual"],
        "expected_source_ids": ["BWF_COACHES"],
    },
]


def load_chunks(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _as_evidence_chunk(row: dict[str, object]) -> EvidenceChunk:
    return EvidenceChunk(
        chunk_id=str(row["chunk_id"]),
        source_id=str(row["source_id"]),
        title=str(row["title"]),
        source_class=str(row["source_class"]),
        artifact_path=str(row["artifact_path"]),
        text=str(row["text"]),
        token_count=int(row["token_count"]),
        evidence_level=str(row["evidence_level"]),
    )


def evaluate_retrieval(
    chunks: list[dict[str, object]], eval_items: list[dict[str, object]], top_k: int = 5
) -> dict[str, object]:
    evidence_chunks = [_as_evidence_chunk(row) for row in chunks]
    results = []
    hits = 0
    for item in eval_items:
        retrieved = retrieve_evidence(evidence_chunks, [str(q) for q in item["queries"]], top_k=top_k, max_per_source=1)
        retrieved_ids = [chunk.source_id for chunk in retrieved]
        expected_ids = [str(source_id) for source_id in item["expected_source_ids"]]
        hit = bool(set(retrieved_ids) & set(expected_ids))
        if hit:
            hits += 1
        results.append(
            {
                "question": item["question"],
                "expected_source_ids": expected_ids,
                "retrieved_source_ids": retrieved_ids,
                "hit": hit,
                "top_k": top_k,
            }
        )
    total = len(eval_items)
    return {
        "summary": {
            "total": total,
            "hits": hits,
            "recall_at_k": round(hits / total, 4) if total else 0.0,
        },
        "items": results,
    }


def write_default_eval_set(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(DEFAULT_EVAL_SET, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    eval_path = root / "sources" / "processed" / "metadata" / "retrieval_eval.json"
    if not eval_path.exists():
        write_default_eval_set(eval_path)
    chunks = load_chunks(root / "sources" / "processed" / "text" / "chunks.jsonl")
    eval_items = json.loads(eval_path.read_text(encoding="utf-8"))
    result = evaluate_retrieval(chunks, eval_items)
    output = root / "sources" / "processed" / "metadata" / "retrieval_eval_results.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
