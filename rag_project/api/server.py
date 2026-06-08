from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from rag_project.diagnostics.batch import (
    evidence_chunks_from_payload,
    run_batch_diagnosis_dataset,
)
from rag_project.diagnostics.dataset import diagnostic_dataset_from_payload


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    body = handler.rfile.read(length).decode("utf-8")
    return json.loads(body)


def create_handler():
    class BadmintonRAGHandler(BaseHTTPRequestHandler):
        server_version = "BadmintonRAG/0.1"

        def log_message(self, format: str, *args: object) -> None:
            return

        def do_GET(self) -> None:
            if self.path == "/health":
                _json_response(self, 200, {"status": "ok", "service": "BadmintonRAG"})
                return
            _json_response(self, 404, {"error": "not_found", "path": self.path})

        def do_POST(self) -> None:
            if self.path != "/diagnose/batch":
                _json_response(self, 404, {"error": "not_found", "path": self.path})
                return

            try:
                payload = _read_json(self)
                dataset_payload = payload.get("dataset")
                if not isinstance(dataset_payload, dict):
                    raise ValueError("dataset object is required")
                evidence_payload = payload.get("evidence_chunks") or []
                if not isinstance(evidence_payload, list):
                    raise ValueError("evidence_chunks must be a list")

                dataset = diagnostic_dataset_from_payload(dataset_payload)
                evidence_chunks = evidence_chunks_from_payload(evidence_payload) if evidence_payload else None
                result = run_batch_diagnosis_dataset(
                    dataset,
                    evidence_chunks=evidence_chunks,
                    retrieval_backend=str(payload.get("retrieval_backend") or "keyword"),
                    use_llm=bool(payload.get("llm", False)),
                )
                _json_response(self, 200, result)
            except json.JSONDecodeError as exc:
                _json_response(self, 400, {"error": "invalid_json", "message": str(exc)})
            except (KeyError, TypeError, ValueError) as exc:
                _json_response(self, 400, {"error": "bad_request", "message": str(exc)})

    return BadmintonRAGHandler


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the BadmintonRAG HTTP API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), create_handler())
    print(f"BadmintonRAG API listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
