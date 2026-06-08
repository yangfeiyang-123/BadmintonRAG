import json
import subprocess
import sys
from pathlib import Path

from rag_project.system.audit import audit_system


def test_audit_system_reports_core_domains_and_commands():
    report = audit_system(Path("rag_project"))

    assert report["overall_status"] in {"ready_for_real_csv_trial", "incomplete"}
    domains = report["domains"]
    for name in [
        "literature_sources",
        "rag_retrieval",
        "diagnostic_engine",
        "simulation_data_contract",
        "trial_run",
        "api",
        "web_viewer",
        "llm_optional",
        "windows_scripts",
    ]:
        assert name in domains
        assert "status" in domains[name]
        assert "evidence" in domains[name]

    assert report["verification_commands"]
    assert any("pytest" in command for command in report["verification_commands"])
    assert any("run-csv.ps1" in command for command in report["verification_commands"])
    assert any("audit.ps1" in evidence for evidence in domains["windows_scripts"]["evidence"])
    assert isinstance(report["gaps"], list)


def test_audit_cli_prints_json_report():
    completed = subprocess.run(
        [sys.executable, "-m", "rag_project.system.audit", "--root", "rag_project"],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["project"] == "BadmintonRAG"
    assert "domains" in payload
    assert "verification_commands" in payload
