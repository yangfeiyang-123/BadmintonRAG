import http.client
import json
import threading
from http.server import HTTPServer

from rag_project.api.server import create_handler


def _sample(sample_id: str, outcome_label: str, trunk_peak: float):
    return {
        "sample_id": sample_id,
        "action_type": "forehand_clear",
        "outcome_label": outcome_label,
        "time": [0.0, 0.1, 0.2, 0.3],
        "events": {"backswing_start": 0.0, "acceleration_start": 0.1, "impact": 0.2, "follow_through_end": 0.3},
        "joint_angles": {
            "trunk_rotation": [0.0, 20.0, trunk_peak, 35.0],
            "shoulder_internal_rotation": [5.0, 20.0, 35.0, 30.0],
            "elbow_flexion": [100.0, 90.0, 70.0, 80.0],
            "wrist_extension": [10.0, 18.0, 28.0, 22.0],
            "forearm_pronation": [0.0, 10.0, 30.0, 32.0],
        },
        "muscle_activation": {
            "external_oblique": [0.1, 0.5, 0.8, 0.3],
            "anterior_deltoid": [0.1, 0.3, 0.5, 0.2],
            "triceps_brachii": [0.1, 0.2, 0.6, 0.3],
            "forearm_pronator_group": [0.1, 0.2, 0.7, 0.4],
        },
    }


def _dataset():
    return {
        "dataset_id": "api_forehand_clear",
        "action_type": "forehand_clear",
        "correct_samples": [
            _sample("correct_001", "low_speed", 42.0),
            _sample("correct_002", "low_speed", 44.0),
        ],
        "eval_samples": [_sample("eval_001", "ball_high_not_far", 25.0)],
    }


def _evidence_chunks():
    return [
        {
            "chunk_id": "CLEAR_ZHAO_LOWER_LIMB::1",
            "source_id": "CLEAR_ZHAO_LOWER_LIMB",
            "title": "Lower Limb Movement on the Backcourt Forehand Clear Stroke",
            "source_class": "full_text_html",
            "artifact_path": "zhao.html",
            "text": "Forehand clear uses lower limb movement and trunk coordination.",
            "token_count": 8,
            "evidence_level": "direct_biomechanics_forehand_clear",
            "score": 2.0,
        }
    ]


def _start_server():
    server = HTTPServer(("127.0.0.1", 0), create_handler())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _request(server, method, path, payload=None):
    conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    conn.request(method, path, body=body, headers=headers)
    response = conn.getresponse()
    data = json.loads(response.read().decode("utf-8"))
    conn.close()
    return response.status, data


def test_health_endpoint_returns_service_status():
    server, thread = _start_server()
    try:
        status, data = _request(server, "GET", "/health")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert status == 200
    assert data == {"status": "ok", "service": "BadmintonRAG"}


def test_diagnose_batch_endpoint_returns_structured_reports():
    server, thread = _start_server()
    try:
        status, data = _request(
            server,
            "POST",
            "/diagnose/batch",
            {
                "dataset": _dataset(),
                "retrieval_backend": "keyword",
                "evidence_chunks": _evidence_chunks(),
            },
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert status == 200
    assert data["summary"]["dataset_id"] == "api_forehand_clear"
    assert data["summary"]["retrieval_backend"] == "keyword"
    assert data["reports"][0]["sample_id"] == "eval_001"
    assert data["reports"][0]["evidence"][0]["source_id"] == "CLEAR_ZHAO_LOWER_LIMB"
    assert data["reports"][0]["correction_plan"]
