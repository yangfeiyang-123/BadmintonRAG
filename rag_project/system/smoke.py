from __future__ import annotations

import argparse
import http.client
import json
import threading
from http.server import HTTPServer
from pathlib import Path
from typing import Any

from rag_project.api.server import create_handler
from rag_project.system.bootstrap import doctor_system


def _json_request(port: int, method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    conn.request(method, path, body=body, headers=headers)
    response = conn.getresponse()
    data = json.loads(response.read().decode("utf-8"))
    conn.close()
    return response.status, data


def _text_request(port: int, path: str) -> tuple[int, str]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request("GET", path)
    response = conn.getresponse()
    body = response.read().decode("utf-8")
    conn.close()
    return response.status, body


def smoke_system(root: Path | None = None) -> dict[str, object]:
    project_root = root or Path(__file__).resolve().parents[1]
    checks: dict[str, bool] = {}
    summary: dict[str, object] = {}
    details: dict[str, object] = {}

    doctor = doctor_system(project_root)
    checks["doctor_ready"] = bool(doctor["ready"])
    details["doctor"] = doctor

    server = HTTPServer(("127.0.0.1", 0), create_handler())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_port

        health_status, health = _json_request(port, "GET", "/health")
        checks["health_endpoint"] = health_status == 200 and health.get("status") == "ok"

        viewer_status, viewer_html = _text_request(port, "/")
        checks["web_viewer"] = viewer_status == 200 and "report-output" in viewer_html and "BadmintonRAG" in viewer_html

        example_status, example = _json_request(port, "GET", "/examples/api_batch_request.json")
        checks["example_request"] = example_status == 200 and isinstance(example.get("dataset"), dict)

        diagnosis_status, diagnosis = _json_request(port, "POST", "/diagnose/batch", example)
        checks["diagnosis_endpoint"] = (
            diagnosis_status == 200
            and bool(diagnosis.get("reports"))
            and bool(diagnosis["reports"][0].get("correction_plan"))
        )
        summary = dict(diagnosis.get("summary") or {})
    finally:
        server.shutdown()
        thread.join(timeout=5)

    return {
        "passed": all(checks.values()),
        "checks": checks,
        "summary": summary,
        "details": details,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an end-to-end BadmintonRAG smoke test.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(smoke_system(args.root), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
