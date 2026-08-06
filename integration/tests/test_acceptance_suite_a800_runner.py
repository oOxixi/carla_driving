from __future__ import annotations

import json

from tools.run_acceptance_suite_a800 import parse_run, warm_qwen_service


def test_parse_run_reads_frame_latency_field(tmp_path) -> None:
    rows = [
        {"record_type": "frame", "latency": {"sensor_to_control_ms": 12.5}},
        {"record_type": "qwen_trajectory", "latency": {"sensor_to_trajectory_ms": 98.0}},
        {"record_type": "run_complete", "summary": {"status": "SUCCEEDED"}},
    ]
    path = tmp_path / "run.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    console = "\n".join([
        json.dumps({
            "record_type": "qwen_scenario_acceptance", "passed": True,
            "checks": {"behaviors": True}, "failures": [],
        }),
        json.dumps({
            "record_type": "scenario_extension_acceptance", "passed": True,
            "failed_keys": [], "checks": [{
                "key": "expected_target_actor_id", "status": "PASS",
            }],
        }),
    ])
    parsed = parse_run(tmp_path, console)
    assert parsed["sensor_ready_to_control_ms"]["count"] == 1
    assert parsed["sensor_ready_to_control_ms"]["mean"] == 12.5
    assert parsed["official_sensor_to_trajectory_ms"]["count"] == 1
    assert parsed["official_sensor_to_trajectory_ms"]["mean"] == 98.0
    assert parsed["alignment_checks"] == [
        {"key": "expected_behaviors", "passed": True},
        {"key": "expected_target_actor_id", "passed": True},
    ]
    assert parsed["alignment_passed"] is True


def test_zero_warmup_does_not_touch_service(tmp_path) -> None:
    assert warm_qwen_service(project=tmp_path, base_url="http://invalid", count=0)["count"] == 0
