from pathlib import Path

from rag_project.system.smoke import smoke_system


def test_smoke_system_checks_api_web_and_example_request():
    result = smoke_system(Path("rag_project"))

    assert result["passed"] is True
    assert result["checks"]["doctor_ready"] is True
    assert result["checks"]["health_endpoint"] is True
    assert result["checks"]["web_viewer"] is True
    assert result["checks"]["config_endpoint"] is True
    assert result["checks"]["example_request"] is True
    assert result["checks"]["diagnosis_endpoint"] is True
    assert result["summary"]["evaluated_samples"] >= 1
