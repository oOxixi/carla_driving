import json
from pathlib import Path


def test_sensor_adapter_builds_auditable_alignment_record() -> None:
    from car_control_C.sensor_adapter import SensorFrameStamp, build_sensor_audit

    audit = build_sensor_audit(
        frame_id=42,
        sim_time_s=12.5,
        stamps={
            "rgb": SensorFrameStamp(frame_id=42, timestamp_s=12.50),
            "lidar": SensorFrameStamp(frame_id=42, timestamp_s=12.52),
        },
        extrinsics={
            "rgb": {"x_m": 1.2, "y_m": 0.0, "z_m": 1.6, "yaw_deg": 0.0},
        },
    )

    payload = audit.to_dict()
    assert payload["frame_id"] == 42
    assert payload["max_frame_delta"] == 0
    assert payload["max_time_delta_s"] == 0.02
    assert payload["alignment_ok"] is True
    assert payload["extrinsics"]["rgb"]["z_m"] == 1.6


def test_rgb_pipeline_reports_top_k_and_latency_budget() -> None:
    from car_control_C.rgb_pipeline import RgbDetection, summarize_rgb_pipeline

    summary = summarize_rgb_pipeline(
        frame_id=7,
        detections=[
            RgbDetection("person", 0.51, (0.4, 0.3, 0.6, 0.8), "RGB_ONNX_OBJECT_DETECTOR"),
            RgbDetection("car", 0.90, (0.1, 0.2, 0.3, 0.7), "RGB_ONNX_OBJECT_DETECTOR"),
            RgbDetection("truck", 0.30, (0.2, 0.2, 0.4, 0.6), "RGB_ONNX_OBJECT_DETECTOR"),
        ],
        top_k=2,
        latency_ms_samples=(12.0, 18.0, 29.0),
    )

    payload = summary.to_dict()
    assert [item["class_name"] for item in payload["top_k"]] == ["car", "person"]
    assert payload["p95_latency_ms"] == 29.0
    assert payload["p95_within_30ms"] is True
    assert payload["jump_guard"] == "low_frequency_detection_high_frequency_tracking"


def test_fusion_tracker_keeps_target_id_stable_and_exports_risk() -> None:
    from car_control_C.fusion_tracker import PerceptionTarget, StableTargetTracker

    tracker = StableTargetTracker()
    first = tracker.update(PerceptionTarget("person", 8.0, 0.0, 0.82, "RGB_LIDAR", x_m=8.0, y_m=0.2))
    second = tracker.update(PerceptionTarget("person", 7.6, 0.0, 0.80, "RGB_LIDAR", x_m=7.6, y_m=0.1))

    assert first.target_id == second.target_id
    assert second.ttc_s == 1.9
    assert second.risk_level == "CAUTION"
    assert second.to_dict()["source"] == "RGB_LIDAR"


def test_perception_state_example_is_b_d_readable() -> None:
    path = Path(__file__).resolve().parents[1] / "perception_state.json"
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "1.0"
    assert payload["frame_id"] >= 0
    assert payload["modality_valid"]["rgb"] in {True, False}
    assert payload["objects"][0]["target_id"].startswith("C-")
    assert "min_ttc_s" in payload["risk"]
    assert payload["consumer_note"] == "B/D can consume this state without reading raw sensors."


def test_fault_injection_script_names_required_faults() -> None:
    path = Path(__file__).resolve().parents[1] / "fault_injection.sh"
    text = path.read_text(encoding="utf-8")

    for token in ("camera_blackout", "radar_dropout", "lidar_missing_frame", "false_positive", "false_negative", "latency_noise"):
        assert token in text
    assert "tools/validate_c_role.py" in text
    assert "tools/check_sensor_stability.py" in text
