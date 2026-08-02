from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from perception import (
    Extrinsics,
    FusionTracker,
    Modality,
    Observation,
    RGBDetection,
    RGBPipeline,
    RGBPipelineConfig,
    SensorRecorder,
    SensorReplayer,
    SensorSample,
    SensorSynchronizer,
)
from perception.fault_injection import inject_observation_fault, inject_sensor_fault


def _synchronizer_frame(frame: int = 10, *, invalid: Modality | None = None):
    sync = SensorSynchronizer(tolerance_ms=20.0, max_age_ms=100.0)
    stamp = 1_000_000_000
    for index, modality in enumerate(Modality):
        sample = SensorSample(modality, frame, frame * 0.05, stamp + index * 1_000_000, {"ok": True})
        if modality is invalid:
            sample = sample.invalidated(f"{modality.value}_TEST_FAILURE")
        sync.push(sample)
    return sync.align(
        reference_frame_id=frame,
        reference_sim_time_s=frame * 0.05,
        reference_captured_at_ns=stamp,
        now_ns=stamp + 10_000_000,
    )


def test_extrinsics_transform_points_and_vectors() -> None:
    transform = Extrinsics((1.0, 2.0, 0.0), yaw_deg=90.0)
    assert transform.transform_point((1.0, 0.0, 0.0)) == pytest.approx((1.0, 3.0, 0.0))
    assert transform.rotate_vector((1.0, 0.0, 0.0)) == pytest.approx((0.0, 1.0, 0.0))


def test_synchronizer_requires_same_frame_and_exposes_invalidity() -> None:
    aligned = _synchronizer_frame(invalid=Modality.RADAR)
    assert aligned.stale
    assert not aligned.within_tolerance
    assert aligned.modality_valid[Modality.RADAR] is False
    assert "RADAR_TEST_FAILURE" in aligned.degraded_reason_codes

    sync = SensorSynchronizer()
    sync.push(SensorSample(Modality.RGB, 9, 0.45, 1_000, {}))
    missing = sync.align(reference_frame_id=10, reference_sim_time_s=0.5, reference_captured_at_ns=2_000, now_ns=2_100)
    assert set(missing.missing_modalities) == set(Modality)
    assert missing.stale


def test_sensor_record_and_replay_preserve_frame_and_array(tmp_path: Path) -> None:
    path = tmp_path / "sensor.jsonl"
    sample = SensorSample(Modality.RGB, 1, 0.05, 100, np.zeros((2, 3, 3), dtype=np.uint8))
    with SensorRecorder(path) as recorder:
        recorder.record(sample)
    replayed = tuple(SensorReplayer(path))
    assert len(replayed) == 1
    assert replayed[0].frame_id == 1
    assert np.array_equal(replayed[0].payload, sample.payload)


def test_rgb_low_rate_detection_keeps_stable_track_id_between_frames() -> None:
    calls = []

    def detector(_image):
        calls.append(True)
        return (RGBDetection("vehicle", 0.9, (0.4, 0.3, 0.6, 0.8)),)

    pipeline = RGBPipeline(detector, config=RGBPipelineConfig(
        input_width=64, input_height=32, detection_interval_frames=3,
    ))
    image = np.zeros((100, 200, 3), dtype=np.uint8)
    first = pipeline.process(image, frame_id=1)
    second = pipeline.process(image, frame_id=2)
    third = pipeline.process(image, frame_id=4)
    assert len(calls) == 2
    assert first[0].track_id == second[0].track_id == third[0].track_id
    assert second[0].detected_this_frame is False
    assert third[0].detected_this_frame is True


def test_fusion_associates_modalities_stabilizes_id_and_computes_ttc() -> None:
    tracker = FusionTracker()
    aligned = _synchronizer_frame()
    observations = (
        Observation(Modality.RGB, "vehicle", (10.2, 0.1, 0.0), (1.0, 0.0, 0.0), 0.8, bbox_xyxy_norm=(0.4, 0.4, 0.6, 0.8)),
        Observation(Modality.RADAR, "vehicle", (10.0, 0.0, 0.0), (1.0, 0.0, 0.0), 0.95),
        Observation(Modality.LIDAR, "vehicle", (9.9, -0.1, 0.0), (1.0, 0.0, 0.0), 0.9),
    )
    first = tracker.update(aligned, observations, ego_speed_mps=5.0, speed_limit_mps=8.33)
    second_aligned = _synchronizer_frame(frame=11)
    second = tracker.update(second_aligned, tuple(reversed(observations)), ego_speed_mps=5.0, speed_limit_mps=8.33)
    assert len(first.objects) == 1
    assert first.objects[0].track_id == second.objects[0].track_id
    assert set(first.objects[0].sources) == {Modality.RGB, Modality.RADAR, Modality.LIDAR}
    assert first.ttc_s == pytest.approx(2.5, abs=0.1)
    assert first.risk_level == "HIGH"
    assert first.perception_state["objects"][0]["track_id"].startswith("fused-")


def test_fault_injection_never_marks_failed_modality_normal() -> None:
    rgb = SensorSample(Modality.RGB, 1, 0.05, 100, np.ones((2, 2, 3), dtype=np.uint8))
    black = inject_sensor_fault(rgb, "camera_blackout")
    assert black.valid is False and black.error_code == "RGB_BLACKOUT"
    assert np.count_nonzero(black.payload) == 0
    radar = SensorSample(Modality.RADAR, 1, 0.05, 100, np.ones((2, 3)))
    dropped = inject_sensor_fault(radar, "radar_dropout")
    assert dropped.valid is False and dropped.payload is None

    observations = (Observation(Modality.RGB, "vehicle", (10.0, 0.0, 0.0), (0.0, 0.0, 0.0), 0.9),)
    assert inject_observation_fault(observations, "missed_detection") == ()
    assert len(inject_observation_fault(observations, "false_positive", seed=1)) == 2


def test_fusion_outputs_unknown_risk_when_sensor_frame_is_invalid() -> None:
    aligned = _synchronizer_frame(invalid=Modality.LIDAR)
    result = FusionTracker().update(aligned, (), ego_speed_mps=3.0)
    assert result.risk_level == "UNKNOWN"
    assert result.perception_state["stale"] is True
    assert result.perception_state["modality_valid"]["lidar"] is False
