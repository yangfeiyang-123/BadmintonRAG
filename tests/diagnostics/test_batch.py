import json
from pathlib import Path

from rag_project.diagnostics.batch import run_batch_diagnosis
from rag_project.knowledge.evidence_index import EvidenceChunk
from rag_project.knowledge.vector_index import build_vector_index


def _sample(sample_id: str, outcome_label: str, trunk_peak: float):
    return {
        "sample_id": sample_id,
        "action_type": "forehand_clear",
        "outcome_label": outcome_label,
        "time": [0.0, 0.1, 0.2, 0.3],
        "events": {"backswing_start": 0.0, "acceleration_start": 0.1, "impact": 0.2, "follow_through_end": 0.3},
        "joint_angles": {
            "trunk_rotation": [0.0, 20.0, trunk_peak, 35.0],
            "shoulder_internal_rotation": [5.0, 20.0, 35.0, 30.0],
            "elbow_flexion": [100.0, 90.0, 70.0, 80.0],
            "wrist_extension": [10.0, 18.0, 28.0, 22.0],
            "forearm_pronation": [0.0, 10.0, 30.0, 32.0],
        },
        "muscle_activation": {
            "external_oblique": [0.1, 0.5, 0.8, 0.3],
            "anterior_deltoid": [0.1, 0.3, 0.5, 0.2],
            "triceps_brachii": [0.1, 0.2, 0.6, 0.3],
            "forearm_pronator_group": [0.1, 0.2, 0.7, 0.4],
        },
    }


def test_run_batch_diagnosis_writes_json_summary_and_markdown(tmp_path: Path):
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(
        json.dumps(
            {
                "dataset_id": "forehand_clear_batch",
                "action_type": "forehand_clear",
                "correct_samples": [
                    _sample("correct_001", "low_speed", 42.0),
                    _sample("correct_002", "low_speed", 44.0),
                ],
                "eval_samples": [_sample("eval_001", "ball_high_not_far", 25.0)],
            }
        ),
        encoding="utf-8",
    )
    evidence = [
        EvidenceChunk(
            chunk_id="CLEAR_ZHAO_LOWER_LIMB::1",
            source_id="CLEAR_ZHAO_LOWER_LIMB",
            title="Lower Limb Movement on the Backcourt Forehand Clear Stroke",
            source_class="full_text_html",
            artifact_path="zhao.html",
            text="Forehand clear uses lower limb movement and trunk coordination.",
            token_count=8,
            evidence_level="direct_biomechanics_forehand_clear",
            score=2.0,
        )
    ]

    result = run_batch_diagnosis(dataset_path, tmp_path / "out", evidence_chunks=evidence)

    assert result["summary"]["dataset_id"] == "forehand_clear_batch"
    assert result["summary"]["evaluated_samples"] == 1
    assert result["summary"]["outcome_counts"]["ball_high_not_far"] == 1
    assert result["summary"]["retrieval_backend"] == "keyword"

    reports = json.loads((tmp_path / "out" / "diagnosis_reports.json").read_text(encoding="utf-8"))
    assert reports[0]["sample_id"] == "eval_001"
    assert reports[0]["retrieval_backend"] == "keyword"
    assert reports[0]["evidence"][0]["source_id"] == "CLEAR_ZHAO_LOWER_LIMB"

    markdown = (tmp_path / "out" / "reports" / "eval_001.md").read_text(encoding="utf-8")
    assert "# 正手高远球诊断报告：eval_001" in markdown
    # INTEG-06: legacy source id is cited as [S06] in the rendered markdown (JSON payload keeps source_id).
    assert "[S06]" in markdown


def test_run_batch_diagnosis_can_use_vector_retrieval_backend(tmp_path: Path):
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(
        json.dumps(
            {
                "dataset_id": "forehand_clear_batch",
                "action_type": "forehand_clear",
                "correct_samples": [
                    _sample("correct_001", "low_speed", 42.0),
                    _sample("correct_002", "low_speed", 44.0),
                ],
                "eval_samples": [_sample("eval_001", "ball_high_not_far", 25.0)],
            }
        ),
        encoding="utf-8",
    )
    vector_index = build_vector_index(
        [
            {
                "chunk_id": "CLEAR_ZHAO_LOWER_LIMB::1",
                "source_id": "CLEAR_ZHAO_LOWER_LIMB",
                "title": "Lower Limb Movement on the Backcourt Forehand Clear Stroke",
                "source_class": "full_text_html",
                "evidence_level": "direct_biomechanics_forehand_clear",
                "artifact_path": "zhao.html",
                "text": "Forehand clear trunk rotation lower limb movement kinematics.",
                "token_count": 8,
                "keywords": ["forehand", "clear", "trunk", "rotation"],
            },
            {
                "chunk_id": "BWF_COACHES::1",
                "source_id": "BWF_COACHES",
                "title": "BWF Coach Manual",
                "source_class": "official_manual",
                "evidence_level": "official_instruction",
                "artifact_path": "bwf.html",
                "text": "Badminton coaching manual grip footwork safety.",
                "token_count": 6,
                "keywords": ["coach", "manual"],
            },
        ]
    )

    result = run_batch_diagnosis(
        dataset_path,
        tmp_path / "out",
        retrieval_backend="vector",
        vector_index=vector_index,
    )

    assert result["summary"]["retrieval_backend"] == "vector:local_tfidf"
    reports = json.loads((tmp_path / "out" / "diagnosis_reports.json").read_text(encoding="utf-8"))
    assert reports[0]["retrieval_backend"] == "vector:local_tfidf"
    assert reports[0]["evidence"][0]["source_id"] == "CLEAR_ZHAO_LOWER_LIMB"
