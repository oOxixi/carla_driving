from argparse import Namespace

from integration.day20.carla_control_adapter import CarlaControlAdapter
from integration.day20.day20_intent_executor import IntentControlOutput


class FakeControl:
    def __init__(self, *, throttle, brake, steer):
        self.throttle = throttle
        self.brake = brake
        self.steer = steer


class FakeVehicle:
    def __init__(self, speed_mps=0.0):
        self.speed_mps = speed_mps
        self.applied = []

    def get_velocity(self):
        return Namespace(x=self.speed_mps, y=0.0, z=-9.8)

    def get_transform(self):
        return Namespace(
            location=Namespace(x=1.0, y=2.0, z=0.0),
            rotation=Namespace(yaw=0.0),
        )

    def apply_control(self, control):
        self.applied.append(control)


def _adapter():
    return CarlaControlAdapter(control_factory=FakeControl)


def test_day20_ego_control_is_always_applied_after_d_arbitration():
    vehicle = FakeVehicle()
    target = IntentControlOutput(target_speed_kmh=20.0)

    result = _adapter().apply(
        vehicle,
        target,
        scene_state={
            "frame_id": 10,
            "ego": {"lane_id": 1},
            "objects": [{"direction": "front", "distance_m": 3.0}],
        },
    )

    assert result["raw_control"]["throttle"] > 0.0
    assert result["safety_override"] is True
    assert result["safety_reason"] == "EMERGENCY_FRONT_OBSTACLE_TOO_CLOSE"
    assert vehicle.applied[-1].throttle == 0.0
    assert vehicle.applied[-1].brake == 1.0


def test_day20_speed_uses_planar_velocity_and_safe_control_passes_through():
    vehicle = FakeVehicle(speed_mps=5.0)
    target = IntentControlOutput(target_speed_kmh=20.0)

    result = _adapter().apply(
        vehicle,
        target,
        scene_state={"frame_id": 11, "ego": {"lane_id": 1}, "objects": []},
    )

    assert result["current_speed_kmh"] == 18.0
    assert result["safety_override"] is False
    assert vehicle.applied[-1].throttle == 0.35
    assert vehicle.applied[-1].brake == 0.0
