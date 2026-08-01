from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from integration.offline_replay import load_replay_manifest, run_replay_manifest


def _vehicle() -> dict[str, object]:
    return {
        "speed_mps": 4.0,
        "x_m": 0.0,
        "y_m": 0.0,
        "z_m": 0.0,
        "yaw_deg": 0.0,
        "lane_id": "1",
    }


def _write_manifest(path: Path, records: list[dict[str, object]]) -> Path:
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )
    return path


def test_invalid_qwen_response_fails_closed_through_d(tmp_path: Path) -> None:
    rgb = np.zeros((8, 12, 3), dtype=np.uint8)
    np.save(tmp_path / "rgb.npy", rgb)
    lidar = np.array([
        [5.0, -0.2, 0.0, 1.0],
        [5.1, 0.0, 0.0, 1.0],
        [5.2, 0.2, 0.0, 1.0],
    ], dtype=np.float32)
    np.save(tmp_path / "lidar.npy", lidar)
    manifest = _write_manifest(tmp_path / "replay.jsonl", [{
        "schema_version": "1.0",
        "frame": 1,
        "sim_time_s": 0.05,
        "vehicle": _vehicle(),
        "rgb_path": "rgb.npy",
        "lidar_path": "lidar.npy",
        "perception": {
            "detected_objects": [{
                "class_id": 2,
                "class_name": "car",
                "confidence": 0.9,
                "bbox_xyxy_norm": [0.4, 0.3, 0.6, 0.8],
            }],
        },
        "qwen": {
            "voice_command": "继续行驶",
            "response": {
                "action": "KEEP_LANE",
                "confidence": 0.9,
                "requires_confirmation": False,
                "throttle": 1.0,
            },
        },
        "expected": {
            "qwen_status": "ERROR",
            "safety_override": True,
            "safety_reason": "WATCHDOG_ALERT",
            "min_brake": 1.0,
            "max_throttle": 0.0,
            "min_detection_count": 1,
            "lead_distance_range_m": [4.9, 5.2],
            "rgb_loaded": True,
            "lidar_loaded": True,
        },
    }])

    report = run_replay_manifest(manifest)

    assert report.passed
    result = report.results[0]
    assert result.qwen_status == "ERROR"
    assert result.watchdog_alerts == ("QWEN_ERROR",)
    assert result.brake == 1.0
    assert result.throttle == 0.0


def test_valid_qwen_response_reaches_runtime_boundary(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path / "replay.jsonl", [{
        "schema_version": "1.0",
        "frame": 10,
        "sim_time_s": 0.5,
        "vehicle": {
            **_vehicle(),
            "speed_mps": 0.0,
        },
        "perception": {},
        "qwen": {
            "voice_command": "速度设为每秒三米",
            "response": {
                "action": "SET_SPEED",
                "target_speed_mps": 3.0,
                "confidence": 0.95,
                "requires_confirmation": False,
                "decision_source": "RECORDED_QWEN",
            },
        },
        "expected": {
            "qwen_status": "READY",
            "safety_override": False,
            "max_throttle": 1.0,
        },
    }])

    report = run_replay_manifest(manifest)

    assert report.passed
    assert report.results[0].qwen_status == "READY"
    assert report.results[0].throttle > 0.0


def test_manifest_requires_increasing_frame_and_simulation_time(tmp_path: Path) -> None:
    record = {
        "schema_version": "1.0",
        "frame": 1,
        "sim_time_s": 0.05,
        "vehicle": _vehicle(),
    }
    manifest = _write_manifest(tmp_path / "bad.jsonl", [record, record])

    with pytest.raises(ValueError, match="must increase"):
        load_replay_manifest(manifest)


def test_dataset_paths_cannot_escape_manifest_directory(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.npy"
    np.save(outside, np.zeros((2, 2, 3), dtype=np.uint8))
    manifest = _write_manifest(tmp_path / "bad-path.jsonl", [{
        "schema_version": "1.0",
        "frame": 1,
        "sim_time_s": 0.05,
        "vehicle": _vehicle(),
        "rgb_path": "../outside.npy",
    }])

    with pytest.raises(ValueError, match="inside the dataset"):
        run_replay_manifest(manifest)
