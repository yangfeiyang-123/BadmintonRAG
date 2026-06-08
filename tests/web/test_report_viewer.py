from pathlib import Path


def test_report_viewer_contains_csv_upload_and_conversion_logic():
    html = Path("rag_project/web/report_viewer.html").read_text(encoding="utf-8")

    assert 'id="csv-file"' in html
    assert 'id="load-csv-example"' in html
    assert "/examples/forehand_clear_simulation.csv" in html
    assert "function parseCsv" in html
    assert "function csvRowsToDataset" in html
    assert "joint_" in html
    assert "muscle_" in html
    assert 'id="use-llm"' in html
    assert "/config" in html
    assert "payload.llm" in html


def test_report_viewer_renders_explanation_links():
    html = Path("rag_project/web/report_viewer.html").read_text(encoding="utf-8")

    assert "function renderExplanationLinks" in html
    assert "Outcome-Deviation Explanation Links" in html
    assert "explanation_links" in html
