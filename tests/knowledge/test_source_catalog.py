import csv
import json
from pathlib import Path

from rag_project.knowledge.source_catalog import build_source_catalog, write_source_catalog


def test_build_source_catalog_marks_ingestion_decisions():
    rows = [
        {
            "id": "REV_LAM_LUNGE",
            "category": "review",
            "title": "Biomechanics of Lower Limb in Badminton Lunge",
            "status": "downloaded_html",
            "notes": "PMC open access article",
            "downloaded_files": "rag_project/sources/raw/html/REV_LAM_LUNGE.html",
        },
        {
            "id": "BOOK_GRICE",
            "category": "book",
            "title": "Badminton: Steps to Success",
            "status": "downloaded_html",
            "notes": "Commercial textbook page",
            "downloaded_files": "rag_project/sources/raw/html/BOOK_GRICE.html",
        },
    ]

    catalog = build_source_catalog(rows)

    by_id = {row["id"]: row for row in catalog}
    assert by_id["REV_LAM_LUNGE"]["source_class"] == "full_text_html"
    assert by_id["REV_LAM_LUNGE"]["ingest_text"] == "true"
    assert by_id["BOOK_GRICE"]["source_class"] == "book_preview_or_product_page"
    assert by_id["BOOK_GRICE"]["ingest_text"] == "false"
    assert "preview" in by_id["BOOK_GRICE"]["reason"]


def test_write_source_catalog_outputs_csv_and_json(tmp_path: Path):
    rows = [
        {
            "id": "BWF_COACHES",
            "category": "official",
            "title": "BWF Coach Education",
            "status": "downloaded_html_and_supplemental_pdf",
            "notes": "BWF Coach Manual",
            "downloaded_files": "rag_project/sources/raw/html/BWF_COACHES.html",
        }
    ]
    csv_path = tmp_path / "source_catalog.csv"
    json_path = tmp_path / "source_catalog.json"

    write_source_catalog(rows, csv_path, json_path)

    csv_rows = list(csv.DictReader(csv_path.open(encoding="utf-8-sig")))
    json_rows = json.loads(json_path.read_text(encoding="utf-8"))
    assert csv_rows[0]["source_class"] == "official_manual"
    assert json_rows[0]["ingest_text"] == "true"
