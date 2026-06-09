from __future__ import annotations

import re
from html import unescape
from pathlib import Path


def extract_pdf_text(path: Path) -> str:
    """Extract text from a PDF using PyMuPDF, preserving page-break newlines.

    Returns "" if PyMuPDF is unavailable or the file cannot be read, so callers
    can skip gracefully (INTEG-04). Page boundaries are kept as blank lines so
    downstream chunking can still see structure.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return ""
    try:
        doc = fitz.open(path)
    except Exception:
        return ""
    parts: list[str] = []
    try:
        for page in doc:
            parts.append(page.get_text("text"))
    finally:
        doc.close()
    text = "\n\n".join(parts)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)
    return text.strip()


def extract_text(path: Path) -> str:
    """Dispatch on suffix: .pdf -> PyMuPDF, otherwise HTML extraction."""
    if path.suffix.lower() == ".pdf":
        return extract_pdf_text(path)
    return extract_html_text(path)


def extract_html_text(path: Path) -> str:
    html = path.read_text(encoding="utf-8", errors="replace")
    html = re.sub(r"(?is)<(script|style|noscript|svg).*?</\1>", " ", html)
    html = re.sub(r"(?is)<(nav|footer|header).*?</\1>", " ", html)
    html = re.sub(r"(?is)<br\s*/?>", "\n", html)
    html = re.sub(r"(?is)</(p|h1|h2|h3|li|tr)>", "\n", html)
    text = re.sub(r"(?is)<[^>]+>", " ", html)
    text = unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)
    return text.strip()
