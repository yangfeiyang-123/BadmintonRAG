import json
from pathlib import Path

from rag_project.knowledge.vector_index import build_vector_index, load_vector_index, write_vector_index


def _chunks():
    return [
        {
            "chunk_id": "CLEAR_ZHAO_LOWER_LIMB::1",
            "source_id": "CLEAR_ZHAO_LOWER_LIMB",
            "title": "Lower Limb Movement on the Backcourt Forehand Clear Stroke",
            "source_class": "full_text_html",
            "evidence_level": "direct_biomechanics_forehand_clear",
            "artifact_path": "zhao.html",
            "text": "Forehand clear trunk rotation supports lower limb drive during acceleration.",
            "token_count": 10,
            "keywords": ["forehand", "clear", "lower", "limb"],
        },
        {
            "chunk_id": "CLEAR_ZHAO_LOWER_LIMB::2",
            "source_id": "CLEAR_ZHAO_LOWER_LIMB",
            "title": "Lower Limb Movement on the Backcourt Forehand Clear Stroke",
            "source_class": "full_text_html",
            "evidence_level": "direct_biomechanics_forehand_clear",
            "artifact_path": "zhao.html",
            "text": "Backcourt forehand clear players show pressure and knee coordination.",
            "token_count": 9,
            "keywords": ["backcourt", "pressure", "knee"],
        },
        {
            "chunk_id": "OVERHEAD_WANG_ARM_TRUNK::1",
            "source_id": "OVERHEAD_WANG_ARM_TRUNK",
            "title": "Steps for Arm and Trunk Actions of Overhead Forehand Stroke",
            "source_class": "full_text_html",
            "evidence_level": "overhead_stroke_transfer",
            "artifact_path": "wang.html",
            "text": "Overhead forehand stroke coordinates arm and trunk action sequence.",
            "token_count": 9,
            "keywords": ["overhead", "arm", "trunk"],
        },
    ]


def test_vector_index_ranks_chunks_by_query_similarity():
    index = build_vector_index(_chunks())

    results = index.search("forehand clear lower limb drive", top_k=2)

    assert results[0]["source_id"] == "CLEAR_ZHAO_LOWER_LIMB"
    assert results[0]["chunk_id"] == "CLEAR_ZHAO_LOWER_LIMB::1"
    assert results[0]["score"] > results[1]["score"]
    assert results[0]["evidence_level"] == "direct_biomechanics_forehand_clear"


def test_vector_index_can_diversify_by_source():
    index = build_vector_index(_chunks())

    results = index.search("forehand clear lower limb trunk", top_k=2, max_per_source=1)

    assert len(results) == 2
    assert len({result["source_id"] for result in results}) == 2


def test_vector_index_round_trips_to_json(tmp_path: Path):
    output = tmp_path / "vector_index.json"
    index = build_vector_index(_chunks())

    write_vector_index(index, output)
    loaded = load_vector_index(output)
    results = loaded.search("overhead forehand arm trunk sequence", top_k=1)

    assert json.loads(output.read_text(encoding="utf-8"))["backend"] == "local_tfidf"
    assert results[0]["source_id"] == "OVERHEAD_WANG_ARM_TRUNK"
