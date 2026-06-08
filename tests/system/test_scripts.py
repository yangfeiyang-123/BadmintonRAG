from pathlib import Path


def test_windows_scripts_exist_and_call_expected_modules():
    scripts = {
        "bootstrap.ps1": "rag_project.system.bootstrap bootstrap",
        "smoke.ps1": "rag_project.system.bootstrap smoke",
        "serve.ps1": "rag_project.api.server",
        "test.ps1": "pytest",
    }

    for script_name, expected in scripts.items():
        path = Path("scripts") / script_name
        assert path.exists(), f"{path} should exist"
        text = path.read_text(encoding="utf-8")
        assert ".venv" in text
        assert expected in text
