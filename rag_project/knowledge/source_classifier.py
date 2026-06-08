from __future__ import annotations


def classify_source(source_id: str, category: str, status: str, notes: str) -> str:
    text = f"{source_id} {category} {status} {notes}".lower()
    if "bwf" in text or "shuttle" in text or category == "official":
        return "official_manual"
    if category == "book" or "book" in text or "google books" in text or "commercial" in text:
        return "book_preview_or_product_page"
    if "pmc open access" in text or "nature scientific reports open" in text or "frontiers open" in text:
        return "full_text_html"
    if "downloaded_pdf" in status:
        return "full_text_pdf"
    if "pubmed record" in text or "airiti" in text or "metadata" in text or "thesis metadata" in text:
        return "abstract_or_metadata_only"
    if "downloaded_html" in status:
        return "full_text_html"
    return "abstract_or_metadata_only"
