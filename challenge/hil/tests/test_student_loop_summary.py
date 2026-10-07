"""The closed-loop summariser must read the runner's own evidence schema."""
from __future__ import annotations

import json
from pathlib import Path

from ..carla.summarise_student_loop import _aggregate, summarise


def _write_run(root: Path, scenario: str, *, status: str, difficulty: str, behaviors: list[str],
               oracle: str) -> None:
    log_dir = root / scenario / "logs"
    log_dir.mkdir(parents=True)
    frames = []
    for index in range(6):
        frames.append({
            "record_type": "frame",
            "sim_time_s": index * 0.05,
            "speed_mps": 4.0 + 0.1 * index,
            "vehicle": {"yaw_deg": 0.5 * index, "lane_id": "1"},
            "final_control": {"throttle": 0.3, "brake": 0.0, "steer": 0.01 * index},
            "lateral": {"cross_track_error_m": 0.01 * index},
            "latency": {
                "sensor_to_control_ms": 40.0 + index,
                "sensor_to_decision_ms": 39.0 + index,
                "decision_ms": 1.0,
                "perception_acquire_ms": 60.0,
                "simulator_tick_ms": 15.0,
            },
        })
    (log_dir / f"{scenario}_run.jsonl").write_text(
        "\n".join(json.dumps(item) for item in frames) + "\n", encoding="utf-8",
    )
    summary = {
        "scenario_id": scenario,
        "difficulty": difficulty,
        "status": status,
        "score": {"final_score": 25.0 if status == "SUCCEEDED" else 20.0},
        "completion": status == "SUCCEEDED",
        "collision_count": 0,
        "red_light_violation_count": 0,
        "route_deviation_count": 0,
        "serious_route_deviation": False,
        "safety_override_frames": 2,
        "latency": {"sensor_to_control_p95_ms": 45.0, "decision_p95_ms": 1.0},
        "acceptance": {
            "checks": [{"key": "must_no_collision", "status": "PASS"}],
            "failed_keys": [] if status == "SUCCEEDED" else ["target_speed_kph"],
            "metrics": {
                "extension_acceptance": {
                    "passed": oracle == "PASS",
                    "failed_keys": [] if oracle == "PASS" else ["expected_target_actor_id"],
                    "checks": [
                        {"key": "oracle_expected_behaviors", "status": oracle,
                         "actual": behaviors, "required": behaviors},
                    ],
                    "evidence": {"qwen_behaviors": behaviors},
                }
            },
        },
    }
    (log_dir / f"{scenario}_run.summary.json").write_text(
        json.dumps(summary), encoding="utf-8",
    )


def test_aggregate_reads_acceptance_latency_and_comfort(tmp_path: Path) -> None:
    _write_run(tmp_path, "ACC_B01_start_keep_lane", status="SUCCEEDED",
               difficulty="basic", behaviors=["KEEP_LANE"], oracle="PASS")
    _write_run(tmp_path, "ACC_A03_pedestrian_crossing", status="FAILED",
               difficulty="advanced", behaviors=["KEEP_LANE"], oracle="PASS")
    _write_run(tmp_path, "ACC_C01_heavy_rain_fog", status="SUCCEEDED",
               difficulty="challenge", behaviors=["SLOW_DOWN"], oracle="FAIL")

    report = summarise(tmp_path)
    aggregate = _aggregate(report)

    assert aggregate["per_group"]["basic"]["completion_rate"] == 1.0
    assert aggregate["per_group"]["advanced"]["completion_rate"] == 0.0
    assert aggregate["oracle_alignment"] == {
        "checked": 3, "passed": 2, "failed_scenarios": ["ACC_C01_heavy_rain_fog"],
    }
    assert aggregate["extension_acceptance"]["passed"] == 2
    assert aggregate["latency_ms"]["per_frame_sensor_to_control_ms"]["n"] == 18
    assert aggregate["latency_ms"]["per_frame_sensor_to_control_ms"]["max"] == 45.0
    assert aggregate["safety"]["collisions"] == 0
    assert aggregate["comfort"]["max_abs_cross_track_error_m"]["max"] == 0.05
    # 30/40/30 weighting from the rules, with basic=1.0 advanced=0.0 challenge=1.0
    assert round(aggregate["scoring_proxy"]["weighted_completion_rate"], 6) == 0.6
    assert aggregate["scoring_proxy"]["task_completion_score_out_of_15"] == 9.0


def test_latency_is_pooled_across_frames_not_across_run_percentiles(tmp_path: Path) -> None:
    _write_run(tmp_path, "ACC_B01_start_keep_lane", status="SUCCEEDED",
               difficulty="basic", behaviors=["KEEP_LANE"], oracle="PASS")
    _write_run(tmp_path, "ACC_B02_set_speed_20", status="FAILED",
               difficulty="basic", behaviors=["SET_SPEED"], oracle="PASS")
    aggregate = _aggregate(summarise(tmp_path))
    pooled = aggregate["latency_ms"]["per_frame_sensor_to_control_ms"]
    assert pooled["n"] == 12  # 6 frames x 2 runs
    assert pooled["p50"] == 43.0  # six samples per run, duplicated across two runs
    assert pooled["max"] == 45.0
