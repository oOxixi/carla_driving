import pytest

from integration.perception_stage import (
    ObservationAuthority,
    audit_control_sources,
    classify_observation_source,
)


@pytest.mark.parametrize(
    ("source", "authority"),
    [
        ("RGB_ONNX_LIDAR_FRONT_CORRIDOR", ObservationAuthority.SENSOR),
        ("RADAR_LIDAR_ASSOCIATED_RADIAL_VELOCITY", ObservationAuthority.SENSOR),
        ("CARLA_MAP_SPEED_LIMIT", ObservationAuthority.MAP),
        ("SCENARIO_CONFIG_TRUTH", ObservationAuthority.ORACLE),
        ("CARLA_TRUTH_LIDAR_ASSOCIATED_ACTOR", ObservationAuthority.ORACLE),
        ("VIRTUAL_ACCEPTANCE_TRUTH", ObservationAuthority.SYNTHETIC),
    ],
)
def test_source_authority_is_explicit(source: str, authority: ObservationAuthority) -> None:
    assert classify_observation_source(source) is authority


def test_strict_sensor_control_rejects_oracle_and_virtual_fields() -> None:
    audit = audit_control_sources(
        {
            "lead_distance_m": "LIDAR_FRONT_CORRIDOR",
            "lead_speed_mps": "CARLA_TRUTH_LIDAR_ASSOCIATED_ACTOR",
            "traffic_light": "VIRTUAL_ACCEPTANCE_TRUTH",
            "speed_limit_mps": "CARLA_MAP_SPEED_LIMIT",
        },
        strict_sensor_mode=True,
    )
    assert audit.forbidden_control_fields == ("lead_speed_mps", "traffic_light")
    assert audit.control_clean is False


def test_diagnostic_modes_keep_oracle_data_auditable_without_rejecting_it() -> None:
    audit = audit_control_sources(
        {"lead_distance_m": "SCENARIO_CONFIG_TRUTH"},
        strict_sensor_mode=False,
    )
    assert audit.control_clean
    assert audit.authority_by_field["lead_distance_m"] == "ORACLE"

