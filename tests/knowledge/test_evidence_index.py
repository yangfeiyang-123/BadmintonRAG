from pathlib import Path

from rag_project.knowledge.evidence_index import build_evidence_index, retrieve_evidence


def test_builds_chunks_only_from_evidence_sources(tmp_path: Path):
    full_text = tmp_path / "CLEAR_ZHAO_LOWER_LIMB.html"
    full_text.write_text(
        "<html><body><h1>Forehand clear</h1><p>Badminton forehand clear uses trunk rotation and lower limb drive.</p></body></html>",
        encoding="utf-8",
    )
    preview = tmp_path / "BOOK_GRICE.html"
    preview.write_text("<html><body><p>Commercial product page.</p></body></html>", encoding="utf-8")

    sources = [
        {
            "id": "CLEAR_ZHAO_LOWER_LIMB",
            "title": "Lower Limb Movement on the Backcourt Forehand Clear Stroke",
            "category": "clear",
            "source_class": "full_text_html",
            "downloaded_files": str(full_text),
        },
        {
            "id": "BOOK_GRICE",
            "title": "Badminton: Steps to Success",
            "category": "book",
            "source_class": "book_preview_or_product_page",
            "downloaded_files": str(preview),
        },
    ]

    chunks = build_evidence_index(sources, chunk_size=12, overlap=3)

    assert len(chunks) == 1
    assert chunks[0].source_id == "CLEAR_ZHAO_LOWER_LIMB"
    assert chunks[0].source_class == "full_text_html"
    assert "trunk rotation" in chunks[0].text


def test_retrieves_evidence_by_query_terms(tmp_path: Path):
    source = tmp_path / "OVERHEAD_WANG_ARM_TRUNK.html"
    source.write_text(
        "<html><body><p>Overhead forehand stroke sequence coordinates arm and trunk actions.</p></body></html>",
        encoding="utf-8",
    )
    chunks = build_evidence_index(
        [
            {
                "id": "OVERHEAD_WANG_ARM_TRUNK",
                "title": "Steps for Arm and Trunk Actions of Overhead Forehand Stroke",
                "category": "overhead",
                "source_class": "full_text_html",
                "downloaded_files": str(source),
            }
        ],
        chunk_size=20,
        overlap=0,
    )

    results = retrieve_evidence(chunks, ["forehand clear trunk rotation", "overhead forehand stroke kinetic chain"], top_k=1)

    assert len(results) == 1
    assert results[0].source_id == "OVERHEAD_WANG_ARM_TRUNK"
    assert results[0].score > 0
