from __future__ import annotations

from types import SimpleNamespace

import pytest

from integration.carla_perception import LIDAR_SENSOR_ID, RGB_SENSOR_ID
from integration.sensor_stability import (
    SensorFrameCounter,
    SensorProbeResult,
    map_contract_name,
    selected_sensor_specs,
)


def test_selects_only_requested_low_resource_sensor() -> None:
    specs = selected_sensor_specs("rgb", "low")

    assert tuple(spec.sensor_id for spec in specs) == (RGB_SENSOR_ID,)
    assert specs[0].attributes["image_size_x"] == "400"


def test_both_mode_preserves_rgb_then_lidar_order() -> None:
    specs = selected_sensor_specs("both", "default")

    assert tuple(spec.sensor_id for spec in specs) == (
        RGB_SENSOR_ID,
        LIDAR_SENSOR_ID,
    )
    assert all(spec.continuous for spec in specs)


@pytest.mark.parametrize("mode", ["", "camera", "all"])
def test_rejects_unknown_sensor_mode(mode: str) -> None:
    with pytest.raises(ValueError, match="unknown sensor mode"):
        selected_sensor_specs(mode, "low")


def test_map_contract_name_accepts_full_carla_paths() -> None:
    assert map_contract_name("/Game/Carla/Maps/Town03") == "Town03"
    assert map_contract_name(r"\Game\Carla\Maps\Town03/") == "Town03"


def test_counter_waits_for_same_frame_from_both_sensors() -> None:
    counter = SensorFrameCounter((RGB_SENSOR_ID, LIDAR_SENSOR_ID))
    counter.callback(RGB_SENSOR_ID)(SimpleNamespace(frame=42))

    assert not counter.wait_for_frame(
        (RGB_SENSOR_ID, LIDAR_SENSOR_ID), 42, timeout_s=0,
    )

    counter.callback(LIDAR_SENSOR_ID)(SimpleNamespace(frame=42))
    assert counter.wait_for_frame(
        (RGB_SENSOR_ID, LIDAR_SENSOR_ID), 42, timeout_s=0,
    )
    assert counter.counts() == {RGB_SENSOR_ID: 1, LIDAR_SENSOR_ID: 1}
    assert counter.frame_bounds() == {
        RGB_SENSOR_ID: (42, 42),
        LIDAR_SENSOR_ID: (42, 42),
    }


def test_counter_deduplicates_frames_and_records_invalid_callbacks() -> None:
    counter = SensorFrameCounter((RGB_SENSOR_ID,))
    callback = counter.callback(RGB_SENSOR_ID)

    callback(SimpleNamespace(frame=7))
    callback(SimpleNamespace(frame=7))
    callback(SimpleNamespace(frame="7"))
    callback(SimpleNamespace())

    assert counter.counts() == {RGB_SENSOR_ID: 1}
    assert counter.invalid_callbacks() == {RGB_SENSOR_ID: 2}


def test_counter_validates_constructor_and_wait_arguments() -> None:
    with pytest.raises(ValueError, match="unique"):
        SensorFrameCounter(("rgb", "rgb"))
    counter = SensorFrameCounter(("rgb",))
    with pytest.raises(KeyError, match="unknown sensor"):
        counter.wait_for_frame(("lidar",), 1, timeout_s=0)
    with pytest.raises(ValueError, match="non-negative integer"):
        counter.wait_for_frame(("rgb",), -1, timeout_s=0)
    with pytest.raises(ValueError, match="finite"):
        counter.wait_for_frame(("rgb",), 1, timeout_s=float("nan"))


def test_probe_result_is_machine_readable_json() -> None:
    result = SensorProbeResult(
        success=True,
        reason="ok",
        map_name="/Game/Carla/Maps/Town03",
        mode="rgb",
        profile="low",
        requested_frames=2,
        aligned_frames=2,
        callback_counts={RGB_SENSOR_ID: 2},
        frame_bounds={RGB_SENSOR_ID: (10, 11)},
        invalid_callbacks={RGB_SENSOR_ID: 0},
        duration_s=0.1,
    )

    text = result.to_json()
    assert '"success": true' in text
    assert '"aligned_frames": 2' in text
