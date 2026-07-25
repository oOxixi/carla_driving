from __future__ import annotations

import json
from pathlib import Path

from tools.build_multimodal_dataset import build_dataset, deterministic_split
from tools.validate_multimodal_dataset import validate_dataset_files


def test_deterministic_split_keeps_group_together() -> None:
    first = deterministic_split("seq-a", "D03", 7)
    assert first == deterministic_split("seq-a", "D03", 7)
    assert first in {"train", "val", "test"}


def test_builder_hashes_media_writes_splits_and_produces_valid_records(
    tmp_path: Path,
) -> None:
    (tmp_path / "media").mkdir()
    (tmp_path / "media" / "rgb.jpg").write_bytes(b"rgb")
    (tmp_path / "media" / "lidar.npy").write_bytes(b"lidar")
    capture = {
        "frame": 10,
        "sim_time_s": 0.5,
        "sequence_id": "town03_d03_seed7",
        "scenario_id": "D03_front_vehicle_brake",
        "seed": 7,
        "difficulty": "advanced",
        "rgb_path": "media/rgb.jpg",
        "lidar_path": "media/lidar.npy",
        "synchronized": True,
        "language": {
            "command_id": "cmd-1",
            "transcript": "跟车前进",
            "normalized_text": "保持车道并跟车",
            "asr_confidence": 0.96,
            "intent": "START",
            "parameters": {},
            "ambiguity": "none",
        },
        "vehicle": {
            "speed_mps": 4.0,
            "lane_id": 1,
            "route_progress": 0.2,
            "x_m": 1.0,
            "y_m": 2.0,
            "yaw_deg": 0.0,
        },
        "environment": {
            "weather": "clear",
            "lighting": "day",
            "traffic_light_state": "none",
        },
        "perception": {
            "visual_valid": True,
            "lidar_valid": True,
            "detected_objects": [{
                "track_id": "lead-1",
                "class_name": "car",
                "confidence": 0.9,
                "distance_m": 8.0,
                "sources": ["rgb", "lidar"],
            }],
        },
        "qwen": {
            "request_id": "req-1",
            "response": {
                "action": "SLOW_DOWN",
                "confidence": 0.91,
                "requires_confirmation": False,
                "reason_zh": "前车距离不足",
            },
        },
        "safety": {
            "override": True,
            "override_reason": "front_gap",
            "risk_level": "high",
            "ttc_s": 2.1,
            "minimum_gap_m": 8.0,
        },
        "control": {
            "final_action": "SLOW_DOWN",
            "throttle": 0.0,
            "brake": 0.4,
            "steer": 0.0,
        },
        "expected": {
            "action": "SLOW_DOWN",
            "task_success": True,
            "collision": False,
            "red_light_violation": False,
            "route_completed": False,
        },
        "quality": {
            "annotation_status": "double_review",
            "eligible_for_training": True,
            "eligible_for_score": True,
            "flags": [],
        },
        "latency_ms": {
            "asr": 20.0,
            "perception": 25.0,
            "fusion": 2.0,
            "decision": 80.0,
            "safety": 1.0,
            "end_to_end": 128.0,
        },
    }
    manifest = tmp_path / "capture.jsonl"
    manifest.write_text(json.dumps(capture, ensure_ascii=False) + "\n", encoding="utf-8")
    output = tmp_path / "built"

    report = build_dataset(
        [manifest],
        dataset_root=tmp_path,
        output_root=output,
        defaults={
            "sequence_id": "unused",
            "scenario_id": "unused",
            "seed": 0,
            "git_commit": "6eb269a",
            "config_sha256": "a" * 64,
        },
    )

    assert report["records"] == 1
    jsonl_files = [output / "records" / f"{split}.jsonl" for split in ("train", "val", "test")]
    assert validate_dataset_files(jsonl_files, dataset_root=tmp_path, check_files=True) == []
    generated = next(
        json.loads(line)
        for path in jsonl_files
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    )
    assert generated["decision"]["requested_actions"] == [{"action": "SLOW_DOWN"}]
    assert generated["sensors"]["rgb_front"]["sha256"]
    assert generated["quality"]["eligible_for_score"] is True
