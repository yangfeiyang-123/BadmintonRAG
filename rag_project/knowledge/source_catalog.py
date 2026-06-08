from __future__ import annotations

import csv
import json
from pathlib import Path

from rag_project.knowledge.source_classifier import classify_source


CATALOG_FIELDS = [
    "id",
    "category",
    "title",
    "status",
    "source_class",
    "ingest_text",
    "reason",
    "downloaded_files",
]


def _decision(source_class: str) -> tuple[str, str]:
    if source_class in {"official_manual", "full_text_pdf", "full_text_html"}:
        return "true", "eligible evidence source"
    if source_class == "book_preview_or_product_page":
        return "false", "preview or product page only"
    if source_class == "abstract_or_metadata_only":
        return "false", "metadata or abstract only"
    return "false", "unsupported source class"


def build_source_catalog(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    catalog: list[dict[str, str]] = []
    for row in rows:
        source_class = row.get("source_class") or classify_source(
            row.get("id", ""),
            row.get("category", ""),
            row.get("status", ""),
            row.get("notes", ""),
        )
        ingest_text, reason = _decision(source_class)
        catalog.append(
            {
                "id": row.get("id", ""),
                "category": row.get("category", ""),
                "title": row.get("title", ""),
                "status": row.get("status", ""),
                "source_class": source_class,
                "ingest_text": ingest_text,
                "reason": reason,
                "downloaded_files": row.get("downloaded_files", ""),
            }
        )
    return catalog


def load_download_results(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_source_catalog(rows: list[dict[str, str]], csv_path: Path, json_path: Path) -> None:
    catalog = build_source_catalog(rows)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CATALOG_FIELDS)
        writer.writeheader()
        writer.writerows(catalog)
    json_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    rows = load_download_results(root / "sources" / "raw" / "metadata" / "download_results.csv")
    output_dir = root / "sources" / "processed" / "metadata"
    write_source_catalog(rows, output_dir / "source_catalog.csv", output_dir / "source_catalog.json")


if __name__ == "__main__":
    main()
