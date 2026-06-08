import json
from pathlib import Path

from rag_project.knowledge.retrieval_eval import evaluate_retrieval, write_default_eval_set


def test_evaluate_retrieval_reports_hits_and_recall():
    chunks = [
        {
            "chunk_id": "CLEAR_ZHAO_LOWER_LIMB::1",
            "source_id": "CLEAR_ZHAO_LOWER_LIMB",
            "title": "Lower Limb Movement on the Backcourt Forehand Clear Stroke",
            "source_class": "full_text_html",
            "artifact_path": "x.html",
            "text": "Forehand clear trunk rotation and lower limb drive.",
            "token_count": 8,
            "evidence_level": "direct_biomechanics_forehand_clear",
        },
        {
            "chunk_id": "OVERHEAD_WANG_ARM_TRUNK::1",
            "source_id": "OVERHEAD_WANG_ARM_TRUNK",
            "title": "Steps for Arm and Trunk Actions of Overhead Forehand Stroke",
            "source_class": "full_text_html",
            "artifact_path": "y.html",
            "text": "Overhead forehand stroke coordinates arm and trunk sequence.",
            "token_count": 8,
            "evidence_level": "overhead_stroke_transfer",
        },
    ]
    eval_items = [
        {
            "question": "正手高远球下肢参与有哪些证据？",
            "queries": ["forehand clear lower limb trunk rotation"],
            "expected_source_ids": ["CLEAR_ZHAO_LOWER_LIMB"],
        }
    ]

    result = evaluate_retrieval(chunks, eval_items, top_k=2)

    assert result["summary"]["total"] == 1
    assert result["summary"]["hits"] == 1
    assert result["summary"]["recall_at_k"] == 1.0
    assert result["items"][0]["hit"] is True


def test_write_default_eval_set_outputs_questions(tmp_path: Path):
    output = tmp_path / "retrieval_eval.json"

    write_default_eval_set(output)

    items = json.loads(output.read_text(encoding="utf-8"))
    assert len(items) >= 5
    assert all("expected_source_ids" in item for item in items)
