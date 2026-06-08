import json
from pathlib import Path

from rag_project.knowledge.text_corpus import build_text_corpus, write_text_corpus


def test_build_text_corpus_writes_structured_chunks(tmp_path: Path):
    html = tmp_path / "CLEAR_ZHAO_LOWER_LIMB.html"
    html.write_text(
        """
        <html><body>
        <h1>Forehand clear</h1>
        <p>Forehand clear trunk rotation supports lower limb drive during acceleration.</p>
        <p>Forehand clear mechanics include coordinated shoulder elbow and wrist release.</p>
        </body></html>
        """,
        encoding="utf-8",
    )
    catalog = [
        {
            "id": "CLEAR_ZHAO_LOWER_LIMB",
            "title": "Lower Limb Movement on the Backcourt Forehand Clear Stroke",
            "category": "clear",
            "source_class": "full_text_html",
            "ingest_text": "true",
            "downloaded_files": str(html),
        },
        {
            "id": "BOOK_GRICE",
            "title": "Badminton: Steps to Success",
            "category": "book",
            "source_class": "book_preview_or_product_page",
            "ingest_text": "false",
            "downloaded_files": str(html),
        },
    ]

    chunks = build_text_corpus(catalog, chunk_size=14, overlap=0)

    assert chunks
    assert {chunk["source_id"] for chunk in chunks} == {"CLEAR_ZHAO_LOWER_LIMB"}
    assert chunks[0]["chunk_id"].startswith("CLEAR_ZHAO_LOWER_LIMB::")
    assert chunks[0]["evidence_level"] == "direct_biomechanics_forehand_clear"
    assert chunks[0]["keywords"]


def test_write_text_corpus_creates_jsonl(tmp_path: Path):
    html = tmp_path / "OVERHEAD_WANG_ARM_TRUNK.html"
    html.write_text(
        "<html><body><p>Overhead forehand stroke coordinates arm and trunk action sequence.</p></body></html>",
        encoding="utf-8",
    )
    output = tmp_path / "chunks.jsonl"

    write_text_corpus(
        [
            {
                "id": "OVERHEAD_WANG_ARM_TRUNK",
                "title": "Steps for Arm and Trunk Actions of Overhead Forehand Stroke",
                "category": "overhead",
                "source_class": "full_text_html",
                "ingest_text": "true",
                "downloaded_files": str(html),
            }
        ],
        output,
        chunk_size=20,
        overlap=0,
    )

    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["source_id"] == "OVERHEAD_WANG_ARM_TRUNK"
    assert rows[0]["evidence_level"] == "overhead_stroke_transfer"
