from __future__ import annotations

import pytest

from car_control_C import (
    ConservativeSensorFusion,
    SafetyStateParameters,
    VisualObservation,
)


def test_rgb_and_lidar_fuse_class_distance_and_tracker_ttc() -> None:
    fusion = ConservativeSensorFusion()
    summary = fusion.update(
        frame=10,
        sim_time_s=1.0,
        ego_speed_mps=8.0,
        front_distance_m=12.0,
        lidar_valid=True,
        lead_speed_mps=2.0,
        lead_speed_source="TRACKED_LEAD_SPEED",
        visual=VisualObservation(10, True, "pedestrian", 0.92, "RGB_ONNX"),
    )

    assert summary.object_class == "PEDESTRIAN"
    assert summary.front_distance_m == 12.0
    assert summary.closing_speed_mps == 6.0
    assert summary.ttc_s == 2.0
    assert summary.fused_valid
    assert summary.recommended_action == "SLOW_DOWN"
    assert summary.to_dict()["schema_version"] == "1.0"


def test_temporal_lidar_difference_computes_low_ttc_without_actor_truth() -> None:
    fusion = ConservativeSensorFusion()
    fusion.update(frame=1, sim_time_s=0.0, ego_speed_mps=8.0,
                  front_distance_m=10.0, lidar_valid=True)
    summary = fusion.update(frame=2, sim_time_s=0.1, ego_speed_mps=8.0,
                            front_distance_m=9.0, lidar_valid=True)

    assert summary.closing_speed_mps == pytest.approx(10.0)
    assert summary.ttc_s == pytest.approx(0.9)
    assert summary.recommended_action == "EMERGENCY_BRAKE"
    assert summary.source_by_field["closing_speed_mps"] == "LIDAR_TEMPORAL_DIFFERENCE"


def test_missing_visual_semantics_are_explicit_and_not_invented() -> None:
    summary = ConservativeSensorFusion().update(
        frame=3,
        sim_time_s=0.15,
        ego_speed_mps=4.0,
        front_distance_m=20.0,
        lidar_valid=True,
        lead_speed_mps=4.0,
        visual=VisualObservation.unavailable(3),
    )

    assert not summary.visual_valid
    assert summary.object_class is None
    assert not summary.fused_valid
    assert summary.fusion_mode == "LIDAR_ONLY"


def test_low_confidence_visual_result_is_invalid_not_a_guessed_class() -> None:
    summary = ConservativeSensorFusion(SafetyStateParameters(visual_confidence_threshold=0.8)).update(
        frame=4,
        sim_time_s=0.2,
        ego_speed_mps=2.0,
        front_distance_m=None,
        lidar_valid=True,
        visual=VisualObservation(4, True, "vehicle", 0.3),
    )

    assert not summary.visual_valid
    assert summary.object_class is None
    assert summary.fusion_mode == "NO_OBSTACLE"


def test_invalid_lidar_and_visual_range_conflict_fail_closed() -> None:
    fusion = ConservativeSensorFusion()
    missing_lidar = fusion.update(
        frame=5, sim_time_s=0.25, ego_speed_mps=3.0,
        front_distance_m=None, lidar_valid=False,
        visual=VisualObservation.unavailable(5),
    )
    assert missing_lidar.fail_closed
    assert missing_lidar.reason == "lidar_invalid"
    assert fusion.fail_closed_control().brake == 1.0

    fusion.reset()
    conflict = fusion.update(
        frame=6, sim_time_s=0.3, ego_speed_mps=3.0,
        front_distance_m=None, lidar_valid=True,
        visual=VisualObservation(6, True, "pedestrian", 0.95),
    )
    assert conflict.fail_closed
    assert conflict.reason == "visual_hazard_without_range"


def test_frame_alignment_and_episode_reset_are_strict() -> None:
    fusion = ConservativeSensorFusion()
    fusion.update(frame=1, sim_time_s=1.0, ego_speed_mps=0.0,
                  front_distance_m=None, lidar_valid=True)
    with pytest.raises(ValueError, match="strictly increasing"):
        fusion.update(frame=1, sim_time_s=1.1, ego_speed_mps=0.0,
                      front_distance_m=None, lidar_valid=True)
    fusion.reset()
    summary = fusion.update(frame=1, sim_time_s=0.0, ego_speed_mps=0.0,
                            front_distance_m=None, lidar_valid=True)
    assert summary.recommended_action == "KEEP_SPEED"


def test_invalid_sensor_contracts_are_rejected() -> None:
    with pytest.raises(ValueError, match="must not carry semantic"):
        VisualObservation(1, False, "vehicle", 0.5)
    with pytest.raises(ValueError, match="same frame"):
        ConservativeSensorFusion().update(
            frame=2, sim_time_s=0.1, ego_speed_mps=1.0,
            front_distance_m=None, lidar_valid=True,
            visual=VisualObservation.unavailable(1),
        )
    with pytest.raises(ValueError, match="must not carry range"):
        ConservativeSensorFusion().update(
            frame=2, sim_time_s=0.1, ego_speed_mps=1.0,
            front_distance_m=5.0, lidar_valid=False,
        )
