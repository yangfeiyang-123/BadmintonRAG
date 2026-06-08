from pathlib import Path

from rag_project.knowledge.extract_text import extract_html_text


def test_extract_html_text_removes_tags(tmp_path: Path):
    html = tmp_path / "sample.html"
    html.write_text("<html><body><nav>Menu</nav><h1>Title</h1><p>Useful paragraph.</p></body></html>", encoding="utf-8")
    text = extract_html_text(html)
    assert "Title" in text
    assert "Useful paragraph." in text
    assert "<p>" not in text
