from __future__ import annotations

import pytest

from integration.carla_perception import (
    DEMO_SENSOR_SPECS,
    LIDAR_SENSOR_ID,
    LOW_RESOURCE_SENSOR_SPECS,
    RADAR_SENSOR_ID,
    RGB_SENSOR_ID,
    sensor_specs_for_profile,
)


def test_low_profile_preserves_required_exact_frame_sensors() -> None:
    specs = sensor_specs_for_profile("low")
    continuous = {item.sensor_id: item for item in specs if item.continuous}

    assert specs is LOW_RESOURCE_SENSOR_SPECS
    assert set(continuous) == {RGB_SENSOR_ID, LIDAR_SENSOR_ID, RADAR_SENSOR_ID}
    assert continuous[RGB_SENSOR_ID].attributes["sensor_tick"] == "0.05"
    assert continuous[LIDAR_SENSOR_ID].attributes["sensor_tick"] == "0.05"
    assert continuous[RADAR_SENSOR_ID].attributes["sensor_tick"] == "0.05"


def test_low_profile_reduces_gpu_and_lidar_load() -> None:
    specs = sensor_specs_for_profile("LOW")
    by_id = {item.sensor_id: item for item in specs}

    assert int(by_id[RGB_SENSOR_ID].attributes["image_size_x"]) == 400
    assert int(by_id[RGB_SENSOR_ID].attributes["image_size_y"]) == 225
    assert int(by_id[LIDAR_SENSOR_ID].attributes["channels"]) == 16
    assert int(by_id[LIDAR_SENSOR_ID].attributes["points_per_second"]) == 112000
    assert int(by_id[RADAR_SENSOR_ID].attributes["points_per_second"]) == 1500


def test_demo_profile_uses_hd_rgb_and_low_load_ranging_sensors() -> None:
    specs = sensor_specs_for_profile("demo")
    by_id = {item.sensor_id: item for item in specs}

    assert specs is DEMO_SENSOR_SPECS
    assert int(by_id[RGB_SENSOR_ID].attributes["image_size_x"]) == 1280
    assert int(by_id[RGB_SENSOR_ID].attributes["image_size_y"]) == 720
    assert int(by_id[LIDAR_SENSOR_ID].attributes["channels"]) == 16
    assert int(by_id[RADAR_SENSOR_ID].attributes["points_per_second"]) == 1500


def test_unknown_sensor_profile_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown sensor profile"):
        sensor_specs_for_profile("fast-but-undefined")
