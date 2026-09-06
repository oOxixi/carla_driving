from __future__ import annotations

from types import SimpleNamespace

import pytest

from integration.canonical_bridge import (
    control_command_to_voice_envelope,
    perception_frame_to_state,
    voice_envelope_to_driving_command,
)
from integration.contracts import DetectedObject, PerceptionFrame


def test_voice_complex_intent_becomes_canonical_deadline_request() -> None:
    command = voice_envelope_to_driving_command({
        "schema_version": "1.0",
        "command_id": "voice-1",
        "source_text": "跟随前车",
        "intent": "FOLLOW_ROUTE",
        "parameters": {},
        "confidence": 0.95,
        "intent_confidence": 0.95,
        "status": "valid",
        "ambiguity_type": "NONE",
        "confirm_required": True,
        "valid_duration_s": 3.0,
    }, received_at_ns=100)
    assert command["intent"] == "FOLLOW"
    assert command["deadline_ns"] == 3_000_000_100
    assert command["requires_confirmation"] is True


def test_directional_lane_change_keeps_declared_intent_and_direction() -> None:
    command = voice_envelope_to_driving_command({
        "command_id": "lane-left",
        "source_text": "向左变道",
        "intent": "CHANGE_LANE_LEFT",
        "parameters": {"speed": 12, "unit": "km/h"},
        "confidence": 0.95,
        "valid_duration_s": 30.0,
    }, received_at_ns=100)

    assert command["intent"] == "CHANGE_LANE"
    assert command["parameters"]["direction"] == "LEFT"
    assert command["parameters"]["target_speed_mps"] == pytest.approx(12 / 3.6)


def test_scenario_target_actor_alias_is_preserved_for_qwen_binding() -> None:
    command = voice_envelope_to_driving_command({
        "command_id": "avoid-bike",
        "source_text": "避让右前方非机动车",
        "intent": "AVOID_OBSTACLE",
        "parameters": {
            "target_actor_id": "bicycle_right",
            "direction": "LEFT",
        },
        "confidence": 0.98,
        "valid_duration_s": 30.0,
    }, received_at_ns=100)

    assert command["intent"] == "AVOID_OBSTACLE"
    assert command["parameters"]["target_id"] == "bicycle_right"
    assert command["parameters"]["direction"] == "LEFT"


def test_pedestrian_yield_remains_a_yield_at_the_canonical_boundary() -> None:
    command = voice_envelope_to_driving_command({
        "command_id": "yield-pedestrian",
        "source_text": "前方行人横穿，减速让行，安全后继续",
        "intent": "YIELD",
        "parameters": {"target_actor_id": "crossing_pedestrian"},
        "confidence": 0.98,
        "valid_duration_s": 60.0,
    }, received_at_ns=100)

    assert command["intent"] == "YIELD"
    assert command["parameters"]["target_id"] == "crossing_pedestrian"


def test_legacy_perception_becomes_schema_valid_state_with_explicit_missing_radar() -> None:
    scene = PerceptionFrame(
        10, 0.5, lead_distance_m=10.0, lead_speed_mps=1.0,
        detected_objects=(DetectedObject(2, "car", 0.9, (0.4, 0.3, 0.6, 0.8), 10.0),),
    )
    state = perception_frame_to_state(
        scene, SimpleNamespace(speed_mps=5.0),
        captured_at_ns=1000, perception_mode="sensors",
    )
    assert state["objects"][0]["class"] == "vehicle"
    assert state["objects"][0]["ttc_s"] == pytest.approx(2.5)
    assert state["risk_level"] == "HIGH"
    assert state["modality_valid"]["radar"] is False
    assert state["sync"]["missing_modalities"] == ["RADAR"]
    assert state["objects"][0]["track_id"] == "legacy-vehicle-000"


def test_sensor_acquisition_failure_is_stale_and_explicitly_invalid() -> None:
    state = perception_frame_to_state(
        PerceptionFrame(11, 0.55), SimpleNamespace(speed_mps=0.0),
        captured_at_ns=1001, perception_mode="sensor_failure",
    )
    assert state["stale"] is True
    assert state["sync"]["within_tolerance"] is False
    assert state["modality_valid"] == {
        "rgb": False, "radar": False, "lidar": False, "vehicle_state": True,
    }
    assert state["degraded_reason_codes"] == ["SENSOR_ACQUISITION_FAILURE"]


def test_aligned_radar_mode_marks_all_live_modalities_valid() -> None:
    state = perception_frame_to_state(
        PerceptionFrame(12, 0.6), SimpleNamespace(speed_mps=0.0),
        captured_at_ns=1002, perception_mode="sensors_radar",
    )
    assert state["modality_valid"] == {
        "rgb": True, "radar": True, "lidar": True, "vehicle_state": True,
    }
    assert state["sync"]["missing_modalities"] == []
    assert state["degraded_reason_codes"] == []


def test_qwen_follow_plan_maps_to_existing_deterministic_longitudinal_runtime() -> None:
    envelope = control_command_to_voice_envelope({
        "command_id": "voice-1",
        "behavior": "FOLLOW",
        "target": {"target_speed_mps": 3.0},
        "confidence": 0.95,
        "reason_code": "UNIQUE_TARGET",
        "issued_at_ns": 100,
        "deadline_ns": 1_000_000_100,
    }, source_text="跟随前车")
    assert envelope["intent"] == "SLOW_DOWN"
    assert envelope["parameters"] == {"speed": 3.0, "unit": "m/s"}


def test_compiled_qwen_yield_maps_to_bounded_longitudinal_slow_down() -> None:
    envelope = control_command_to_voice_envelope({
        "command_id": "yield-pedestrian",
        "path_type": "SLOW",
        "source": "QWEN_DECISION_PLAN",
        "behavior": "YIELD",
        "target": {"target_speed_mps": 30.0 / 3.6},
        "confidence": 0.95,
        "reason_code": "PEDESTRIAN_CROSSING",
        "issued_at_ns": 100,
        "deadline_ns": 10_000_000_100,
    }, source_text="前方行人横穿，减速让行")

    assert envelope["intent"] == "SLOW_DOWN"
    assert envelope["parameters"] == {
        "speed": pytest.approx(30.0 / 3.6),
        "unit": "m/s",
    }


def test_uncompiled_yield_still_fails_closed() -> None:
    with pytest.raises(ValueError, match="cannot execute"):
        control_command_to_voice_envelope({
            "command_id": "yield-unvalidated",
            "behavior": "YIELD",
            "target": {"target_speed_mps": 3.0},
            "confidence": 0.95,
            "reason_code": "MODEL",
            "issued_at_ns": 100,
            "deadline_ns": 1_000_000_100,
        }, source_text="让行")


def test_unsupported_slow_manoeuvre_fails_closed_instead_of_inventing_steer() -> None:
    with pytest.raises(ValueError, match="cannot execute"):
        control_command_to_voice_envelope({
            "command_id": "voice-1",
            "behavior": "CHANGE_LANE_LEFT",
            "target": {"target_speed_mps": 3.0},
            "confidence": 0.95,
            "reason_code": "MODEL",
            "issued_at_ns": 100,
            "deadline_ns": 1_000_000_100,
        }, source_text="向左变道")
