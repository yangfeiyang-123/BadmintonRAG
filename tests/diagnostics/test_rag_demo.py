from pathlib import Path

from rag_project.diagnostics.run_forehand_clear_rag_demo import run_rag_demo


def test_rag_demo_writes_markdown_reports(tmp_path: Path):
    output_dir = tmp_path / "reports"
    paths = run_rag_demo(output_dir)

    assert len(paths) == 3
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "## 诊断结论" in text
        assert "## 文献证据" in text
        assert "source" not in path.name.lower()
