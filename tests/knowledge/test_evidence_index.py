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


def test_skips_boilerplate_chunks(tmp_path: Path):
    source = tmp_path / "CLEAR_ZHAO_LOWER_LIMB.html"
    source.write_text(
        """
        <html><body>
        <p>Open in a new tab Figure 1 Open in a new tab Figure 2 Unit cm Open in a new tab.</p>
        <p>Forehand clear stroke analysis describes trunk rotation and lower limb drive during acceleration.</p>
        </body></html>
        """,
        encoding="utf-8",
    )

    chunks = build_evidence_index(
        [
            {
                "id": "CLEAR_ZHAO_LOWER_LIMB",
                "title": "Lower Limb Movement on the Backcourt Forehand Clear Stroke",
                "category": "clear",
                "source_class": "full_text_html",
                "downloaded_files": str(source),
            }
        ],
        chunk_size=12,
        overlap=0,
    )

    assert chunks
    assert all("Open in a new tab" not in chunk.text for chunk in chunks)


def test_retrieval_diversifies_sources_and_marks_evidence_level(tmp_path: Path):
    clear_source = tmp_path / "CLEAR_ZHAO_LOWER_LIMB.html"
    clear_source.write_text(
        """
        <html><body>
        <p>Forehand clear trunk rotation lower limb movement acceleration evidence one.</p>
        <p>Forehand clear trunk rotation lower limb movement acceleration evidence two.</p>
        </body></html>
        """,
        encoding="utf-8",
    )
    overhead_source = tmp_path / "OVERHEAD_WANG_ARM_TRUNK.html"
    overhead_source.write_text(
        "<html><body><p>Overhead forehand stroke coordinates arm and trunk action sequence.</p></body></html>",
        encoding="utf-8",
    )
    chunks = build_evidence_index(
        [
            {
                "id": "CLEAR_ZHAO_LOWER_LIMB",
                "title": "Lower Limb Movement on the Backcourt Forehand Clear Stroke",
                "category": "clear",
                "source_class": "full_text_html",
                "downloaded_files": str(clear_source),
            },
            {
                "id": "OVERHEAD_WANG_ARM_TRUNK",
                "title": "Steps for Arm and Trunk Actions of Overhead Forehand Stroke",
                "category": "overhead",
                "source_class": "full_text_html",
                "downloaded_files": str(overhead_source),
            },
        ],
        chunk_size=10,
        overlap=0,
    )

    results = retrieve_evidence(chunks, ["forehand clear trunk rotation overhead forehand stroke"], top_k=3, max_per_source=1)

    assert len(results) == 2
    assert {result.source_id for result in results} == {"CLEAR_ZHAO_LOWER_LIMB", "OVERHEAD_WANG_ARM_TRUNK"}
    assert results[0].evidence_level == "direct_biomechanics_forehand_clear"
    assert results[1].evidence_level == "overhead_stroke_transfer"
