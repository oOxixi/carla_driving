#!/usr/bin/env python3
"""Audit the nine formal CARLA acceptance JSONL logs without dependencies."""

from __future__ import annotations

from collections import Counter
import glob
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
EXPECTED_FRAMES = {"S01": 600, "D03": 700, "D08": 500}


def audit(path: Path) -> dict[str, object]:
    records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    counts = Counter(record["record_type"] for record in records)
    frames = [record for record in records if record["record_type"] == "frame"]
    scenario_group = path.relative_to(ROOT).parts[0]
    expected_frames = EXPECTED_FRAMES[scenario_group]

    assert counts == {
        "run_start": 1,
        "command": 1,
        "frame": expected_frames,
        "feedback": 1,
        "run_complete": 1,
    }, counts
    frame_numbers = [record["frame"] for record in frames]
    assert frame_numbers == list(range(frame_numbers[0], frame_numbers[0] + expected_frames))
    sim_times = [record["sim_time_s"] for record in frames]
    assert all(right > left for left, right in zip(sim_times, sim_times[1:]))
    assert all(
        record["frame"]
        == record["vehicle"]["frame"]
        == record["scene"]["frame"]
        == record["c_safety_state"]["frame"]
        for record in frames
    )
    assert not any(record["scene"]["collision"] for record in frames)
    assert not any(record["scene"]["red_light_violation"] for record in frames)
    onnx_detector_frames = sum(
        record["perception_sources"].get("detected_objects")
        == "RGB_ONNX_OBJECT_DETECTOR"
        for record in frames
    )
    assert onnx_detector_frames == expected_frames

    terminal = next(record for record in records if record["record_type"] == "run_complete")
    summary = terminal["summary"]
    assert summary["status"] == "SUCCEEDED"
    assert summary["acceptance"]["passed"] is True
    assert summary["collision_count"] == 0
    assert summary["red_light_violation_count"] == 0

    safety_overrides = sum(bool(record["safety"]["override"]) for record in frames)
    assert safety_overrides == summary["safety_override_frames"]
    provenance_matches = None
    if scenario_group == "D03":
        provenance_matches = sum(
            record["perception_sources"].get("lead_distance_m")
            == "RGB_ONNX_LIDAR_FRONT_CORRIDOR"
            for record in frames
        )
        assert provenance_matches == 683
    elif scenario_group == "D08":
        provenance_matches = sum(
            record["perception_sources"].get("traffic_light")
            == "CARLA_SCENARIO_TRAFFIC_LIGHT_ACTOR_STOP_WAYPOINT"
            and record["perception_sources"].get("distance_to_stop_line_m")
            == "CARLA_SCENARIO_TRAFFIC_LIGHT_ACTOR_STOP_WAYPOINT"
            for record in frames
        )
        assert provenance_matches == 500

    return {
        "file": str(path.relative_to(ROOT)),
        "frames": len(frames),
        "frame_bounds": [frame_numbers[0], frame_numbers[-1]],
        "strictly_increasing_sim_time": True,
        "cross_layer_frame_match": True,
        "collision_frames": 0,
        "red_light_violation_frames": 0,
        "onnx_detector_frames": onnx_detector_frames,
        "safety_override_frames": safety_overrides,
        "provenance_matches": provenance_matches,
        "terminal_status": summary["status"],
    }


def main() -> None:
    patterns = ("S01/run_*/*.jsonl", "D03/run_*/*.jsonl", "D08/run_*/*.jsonl")
    paths = sorted(
        Path(name)
        for pattern in patterns
        for name in glob.glob(str(ROOT / pattern))
    )
    assert len(paths) == 9, f"expected nine formal logs, found {len(paths)}"
    results = [audit(path) for path in paths]
    for result in results:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    print(json.dumps({
        "audit": "PASS",
        "formal_runs": len(results),
        "total_frames": sum(int(result["frames"]) for result in results),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
