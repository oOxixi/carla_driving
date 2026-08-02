from __future__ import annotations

import json
from threading import Thread
from urllib.request import Request, urlopen

from integration.qwen_boundary import QwenInputContext
from integration.qwen_service_client import QwenServiceClient
from qwen_service.runtime import QwenServiceRuntime
from qwen_service.server import create_server


class _ReadyAdapter:
    def infer(self, _context: object) -> dict[str, object]:
        return {
            "action": "SET_SPEED",
            "confidence": 1.0,
            "requires_confirmation": False,
            "target_speed_mps": 5.0,
        }


def _get_json(url: str) -> tuple[int, dict[str, object]]:
    with urlopen(url, timeout=2.0) as response:
        return response.status, json.loads(response.read())


def test_http_service_exposes_health_infer_and_metrics() -> None:
    runtime = QwenServiceRuntime(
        _ReadyAdapter(),
        model_name="test-qwen",
        gpu_stats=lambda: {"available": False},
    )
    server = create_server(runtime, host="127.0.0.1", port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    payload = {
        "schema_version": "1.0",
        "request_id": "req-http",
        "frame": 1,
        "sim_time_s": 0.05,
        "voice_command": "以每秒五米行驶",
        "rgb_ref": None,
        "scene_state": {"traffic_light": "GREEN"},
        "perception": {"detected_objects": []},
        "safety_state": {"recommended_action": "KEEP"},
    }
    try:
        health_status, health = _get_json(f"{base_url}/health")
        request = Request(
            f"{base_url}/infer",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=2.0) as response:
            infer_status = response.status
            inferred = json.loads(response.read())
        metrics_status, metrics = _get_json(f"{base_url}/metrics")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2.0)
        runtime.close()

    assert health_status == 200
    assert health == {
        "schema_version": "1.0",
        "status": "READY",
        "model": "test-qwen",
        "max_concurrency": 1,
        "in_flight": 0,
    }
    assert infer_status == 200
    assert inferred["status"] == "READY"
    assert inferred["decision"]["target_speed_mps"] == 5.0
    assert metrics_status == 200
    assert metrics["requests"]["succeeded"] == 1


def test_repository_client_calls_service_with_frozen_qwen_context() -> None:
    runtime = QwenServiceRuntime(
        _ReadyAdapter(),
        model_name="test-qwen",
        gpu_stats=lambda: {"available": False},
    )
    server = create_server(runtime, host="127.0.0.1", port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = QwenServiceClient(
        f"http://127.0.0.1:{server.server_port}",
        timeout_s=2.0,
    )
    context = QwenInputContext(
        request_id="req-client",
        frame=2,
        sim_time_s=0.1,
        voice_command="以每秒五米行驶",
        rgb_ref=None,
        scene_state={"traffic_light": "GREEN"},
        perception={"detected_objects": []},
        safety_state={"recommended_action": "KEEP"},
    )
    try:
        decision = client.infer(context)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2.0)
        runtime.close()

    assert decision == {
        "action": "SET_SPEED",
        "confidence": 1.0,
        "requires_confirmation": False,
        "target_speed_mps": 5.0,
    }
