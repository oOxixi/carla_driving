"""CARLA-free numerical validation for the member-3 generalization policy."""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from car_control_A import LongitudinalRequest, RuntimeVehicleState
from car_control_B import PurePursuitController, RouteReference, VehiclePose
from car_control_C import LongitudinalController
from car_control_D import SafetySupervisor
from strategy_config import DEFAULT_STRATEGY, dynamic_safety_distance


def main() -> None:
    speeds_kmh = (10, 20, 30, 40)
    curvatures = {"straight": 0.0, "gentle_curve": 0.02, "sharp_curve": 0.08}
    matrix: list[dict[str, object]] = []
    prior_caution = -1.0
    for speed_kmh in speeds_kmh:
        speed_mps = speed_kmh / 3.6
        base = dynamic_safety_distance(
            ego_speed_mps=speed_mps,
            closing_speed_mps=speed_mps,
            actor_type="VEHICLE",
        )
        assert base.caution_distance_m > prior_caution
        assert base.emergency_distance_m <= base.caution_distance_m
        prior_caution = base.caution_distance_m
        for road_name, curvature in curvatures.items():
            for actor_type in ("VEHICLE", "PEDESTRIAN", "OBSTACLE"):
                envelope = dynamic_safety_distance(
                    ego_speed_mps=speed_mps,
                    closing_speed_mps=speed_mps,
                    curvature_per_m=curvature,
                    actor_type=actor_type,
                    sensor_margin_scale=1.0,
                )
                matrix.append({
                    "speed_kmh": speed_kmh,
                    "road": road_name,
                    "actor_type": actor_type,
                    "caution_distance_m": round(envelope.caution_distance_m, 3),
                    "emergency_distance_m": round(envelope.emergency_distance_m, 3),
                })

    reference = RouteReference([(float(index), 0.0) for index in range(80)])
    lateral_checks = []
    for speed_kmh in speeds_kmh:
        output = PurePursuitController().step(
            VehiclePose(0.0, 1.0, 0.0, speed_kmh / 3.6), reference,
        )
        assert output.status == "OK"
        assert -1.0 <= output.steer <= 1.0
        lateral_checks.append({
            "speed_kmh": speed_kmh,
            "lookahead_m": round(output.lookahead_distance_m, 3),
            "steer": round(output.steer, 4),
        })

    longitudinal_checks = []
    for speed_kmh in speeds_kmh:
        speed_mps = speed_kmh / 3.6
        for road_name, curvature in curvatures.items():
            state = RuntimeVehicleState(
                1, 1.0, speed_mps, 0.0, 0.0, 0.0, 0.0, "lane-1",
            )
            controller = LongitudinalController()
            output = controller.step(
                LongitudinalRequest(state, 40.0 / 3.6, curvature), 0.05,
            )
            if curvature > 0.0:
                assert output.target_speed_mps <= math.sqrt(
                    DEFAULT_STRATEGY.longitudinal.max_lateral_accel_mps2 / curvature
                ) + 1e-9
            assert controller.speed_planner.last_plan is not None
            longitudinal_checks.append({
                "speed_kmh": speed_kmh,
                "road": road_name,
                "safe_target_speed_mps": round(output.target_speed_mps, 3),
                "limiting_constraint": controller.speed_planner.last_plan.limiting_constraint,
            })

    supervisor = SafetySupervisor()
    fault_categories = {
        "qwen_or_command": supervisor.arbitrate(
            {"throttle": 0.2, "brake": 0.0, "steer": 0.0}, {},
            {"schema_version": "1.0", "command_id": "x", "source_text": "?", "intent": "UNKNOWN"},
        ).reason_category,
        "perception": supervisor.arbitrate(
            {"throttle": 0.2, "brake": 0.0, "steer": 0.0},
            {"speed_mps": float("nan")},
        ).reason_category,
        "watchdog": supervisor.arbitrate(
            {"throttle": 0.2, "brake": 0.0, "steer": 0.0}, {},
            watchdog_alerts=("CONTROL_HEARTBEAT_TIMEOUT",),
        ).reason_category,
        "route_or_control": supervisor.arbitrate(
            {"throttle": 0.2, "brake": 0.0, "steer": 0.1},
            {"speed_mps": 8.0, "route_deviation_m": 3.0},
        ).reason_category,
    }
    assert fault_categories == {
        "qwen_or_command": "QWEN_OR_COMMAND",
        "perception": "PERCEPTION",
        "watchdog": "WATCHDOG",
        "route_or_control": "ROUTE_OR_LATERAL_CONTROL",
    }

    print(json.dumps({
        "status": "passed",
        "strategy_schema_version": DEFAULT_STRATEGY.schema_version,
        "distance_matrix_cases": len(matrix),
        "distance_matrix": matrix,
        "lateral_checks": lateral_checks,
        "longitudinal_checks": longitudinal_checks,
        "fault_reason_categories": fault_categories,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
