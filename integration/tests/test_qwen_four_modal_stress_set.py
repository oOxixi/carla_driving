from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

from tools.build_qwen_four_modal_stress_set import VARIANTS, build
from tools.build_four_modal_cases_v2 import _canonical_command
from tools.four_modal_metrics import summarize_records


def _jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_builder_labels_visual_and_detector_stress_without_losing_modalities(
    tmp_path: Path,
) -> None:
    collection = tmp_path / "collection"
    (collection / "images").mkdir(parents=True)
    (collection / "lidar").mkdir()
    Image.new("RGB", (100, 60), color=(100, 120, 140)).save(
        collection / "images" / "scene.png"
    )
    np.save(
        collection / "lidar" / "scene.npy",
        np.array([[8.0, 0.0, 0.0, 1.0]], dtype=np.float32),
    )
    _jsonl(collection / "scenes.jsonl", [{
        "scene_id": "scene-1",
        "seed": 1,
        "map": "Carla/Maps/Town03_Opt",
        "weather_profile": "clear_day",
        "rgb_ref": "images/scene.png",
        "lidar_ref": "lidar/scene.npy",
        "lidar_point_count": 1,
    }])
    _jsonl(collection / "cases.jsonl", [{
        "case_id": "case-1",
        "rgb_ref": "images/scene.png",
        "voice_command": "减速并跟随正前方的车辆",
        "scene_state": {"ego_speed_mps": 3.0},
        "perception": {
            "detected_objects": [{
                "track_id": "vehicle-1",
                "class": "vehicle",
                "relation": "center_ahead",
                "bbox_xyxy_norm": [0.4, 0.3, 0.6, 0.8],
            }],
            "lidar_summary": {
                "valid": True,
                "point_count": 1,
                "front_corridor_min_m": 8.0,
                "source": "raw_carla_lidar",
            },
        },
        "expected": {
            "actions": ["SLOW_DOWN"],
            "requires_confirmation": False,
            "target_track_id": "vehicle-1",
        },
    }])

    output = tmp_path / "stress"
    report = build(collection, output)
    rows = [
        json.loads(line)
        for line in (output / "cases.jsonl").read_text(
            encoding="utf-8",
        ).splitlines()
    ]

    assert report["case_count"] == len(VARIANTS)
    assert report["all_cases_have_four_modal_contract"] is True
    assert {row["category"] for row in rows} == set(VARIANTS)
    assert all(Path(output / row["rgb_ref"]).is_file() for row in rows)
    assert all(row["perception"]["lidar_summary"]["raw_sha256"] for row in rows)
    detector_miss = next(
        row for row in rows if row["category"] == "detector_miss"
    )
    assert detector_miss["expected"]["requires_confirmation"] is True
    assert detector_miss["expected"]["safety_expectation"] == (
        "fail_closed_on_missing_target"
    )
    assert detector_miss["perception"]["detected_objects"] == []
    assert detector_miss["perception"]["detector_fault"] == {
        "kind": "miss",
        "removed_track_ids": ["vehicle-1"],
        "target_class": "vehicle",
        "target_relation": "center_ahead",
    }


def test_summary_separates_unanswerable_safety_faults() -> None:
    base = {
        "category": "baseline",
        "status": "READY",
        "expected": {},
        "checks": {
            "action": True,
            "confirmation": True,
            "target_association": True,
            "all": True,
            "safety": True,
        },
        "decision": {"target_track_id": "vehicle-1"},
        "target_grounding": {
            "status": "MATCHED",
            "qwen_target_track_id": "vehicle-1",
        },
        "latency_ms": {
            "voice": 100.0,
            "qwen": 2000.0,
            "post_qwen_control": 1.0,
            "audio_to_final_control": 2101.0,
        },
    }
    safety_fault = {
        **base,
        "category": "detector_miss",
        "status": "ERROR",
        "expected": {
            "safety_expectation": "fail_closed_on_missing_target",
        },
        "checks": {
            "action": False,
            "confirmation": False,
            "target_association": False,
            "all": False,
            "safety": True,
        },
    }
    metrics = summarize_records([base, safety_fault])

    assert metrics["answerable_joint_accuracy"] == 1.0
    assert metrics["answerable_target_association_accuracy"] == 1.0
    assert metrics["raw_qwen_target_association_accuracy"] == 1.0
    assert metrics["safety_fault_fail_closed_accuracy"] == 1.0
    assert metrics["full_chain_contract_accuracy"] == 1.0


def test_canonical_command_uses_observed_relation_and_distance() -> None:
    assert _canonical_command({
        "class": "pedestrian",
        "relation": "far_ahead",
        "distance_m": 27.65,
    }) == "减速并避让距离约28米的行人"
    assert _canonical_command({
        "class": "vehicle",
        "relation": "left_adjacent",
        "distance_m": 14.0,
    }) == "减速并跟随左侧相邻车道的车辆"
