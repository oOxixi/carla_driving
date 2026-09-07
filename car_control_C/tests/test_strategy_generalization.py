from __future__ import annotations

import math
import unittest

from car_control_A import LongitudinalRequest, RuntimeVehicleState
from car_control_B import PurePursuitController, RouteReference, VehiclePose
from car_control_C import LongitudinalController
from car_control_D import SafetySupervisor
from strategy_config import DEFAULT_STRATEGY, dynamic_safety_distance


class StrategyGeneralizationTests(unittest.TestCase):
    def test_dynamic_distance_grows_with_speed_and_risk_context(self) -> None:
        speeds = [value / 3.6 for value in (10.0, 20.0, 30.0, 40.0)]
        envelopes = [
            dynamic_safety_distance(
                ego_speed_mps=speed,
                closing_speed_mps=speed,
                actor_type="VEHICLE",
            )
            for speed in speeds
        ]
        self.assertEqual(
            [item.caution_distance_m for item in envelopes],
            sorted(item.caution_distance_m for item in envelopes),
        )
        for envelope in envelopes:
            self.assertLessEqual(envelope.emergency_distance_m, envelope.caution_distance_m)

        base = dynamic_safety_distance(
            ego_speed_mps=speeds[2], closing_speed_mps=speeds[2], actor_type="VEHICLE",
        )
        vru = dynamic_safety_distance(
            ego_speed_mps=speeds[2], closing_speed_mps=speeds[2], actor_type="PEDESTRIAN",
        )
        curve = dynamic_safety_distance(
            ego_speed_mps=speeds[2], closing_speed_mps=speeds[2],
            curvature_per_m=0.08, actor_type="VEHICLE",
        )
        uncertain = dynamic_safety_distance(
            ego_speed_mps=speeds[2], closing_speed_mps=speeds[2],
            actor_type="VEHICLE", sensor_margin_scale=1.5,
        )
        self.assertGreater(vru.caution_distance_m, base.caution_distance_m)
        self.assertGreater(curve.caution_distance_m, base.caution_distance_m)
        self.assertGreater(uncertain.caution_distance_m, base.caution_distance_m)

    def test_lateral_gain_scheduling_uses_speed_curvature_and_error(self) -> None:
        controller = PurePursuitController()
        reference = RouteReference(
            [(float(index), 0.0) for index in range(50)], curvature_per_m=0.0,
        )
        low = controller._lookahead(10.0 / 3.6)
        high = controller._lookahead(40.0 / 3.6)
        sharp = controller._lookahead(40.0 / 3.6, 0.08, 0.8, 0.2)
        self.assertGreater(high, low)
        self.assertLess(sharp, high)

        for speed_kmh in (10.0, 20.0, 30.0, 40.0):
            output = PurePursuitController().step(
                VehiclePose(0.0, 1.0, 0.0, speed_kmh / 3.6), reference,
            )
            self.assertTrue(-1.0 <= output.steer <= 1.0)
            self.assertTrue(
                DEFAULT_STRATEGY.lateral.min_lookahead_m
                <= output.lookahead_distance_m
                <= DEFAULT_STRATEGY.lateral.max_lookahead_m
            )

    def test_safe_target_speed_obeys_curvature_and_explains_constraint(self) -> None:
        speed = 30.0 / 3.6
        state = RuntimeVehicleState(1, 1.0, speed, 0.0, 0.0, 0.0, 0.0, "lane-1")
        request = LongitudinalRequest(
            state, 40.0 / 3.6, 0.08,
        )
        controller = LongitudinalController()
        output = controller.step(request, 0.05)
        curve_cap = math.sqrt(
            DEFAULT_STRATEGY.longitudinal.max_lateral_accel_mps2 / 0.08
        )
        self.assertLessEqual(output.target_speed_mps, curve_cap)
        self.assertIsNotNone(controller.speed_planner.last_plan)
        self.assertEqual(
            controller.speed_planner.last_plan.safe_target_speed_mps,
            output.target_speed_mps,
        )
        self.assertEqual(
            controller.speed_planner.last_plan.limiting_constraint,
            "road_curvature",
        )

    def test_supervisor_exposes_reason_category_and_dynamic_thresholds(self) -> None:
        speed = 40.0 / 3.6
        envelope = dynamic_safety_distance(
            ego_speed_mps=speed, closing_speed_mps=speed, actor_type="PEDESTRIAN",
        )
        decision = SafetySupervisor().arbitrate(
            {"throttle": 0.3, "brake": 0.0, "steer": 0.0},
            {
                "speed_mps": speed,
                "front_distance_m": envelope.emergency_distance_m * 0.9,
                "front_actor_type": "PEDESTRIAN",
            },
            risk={"ttc_s": envelope.emergency_distance_m * 0.9 / speed},
        )
        self.assertTrue(decision.safety_override)
        self.assertEqual(decision.reason_category, "SAFETY_POLICY")
        self.assertIn("dynamic_safety_distance", decision.risk_metrics)

        sensor_failure = SafetySupervisor().arbitrate(
            {"throttle": 0.2, "brake": 0.0, "steer": 0.0},
            {"speed_mps": 2.0},
            watchdog_alerts=("D_PERCEPTION_INVALID",),
        )
        self.assertEqual(sensor_failure.reason_category, "PERCEPTION")


if __name__ == "__main__":
    unittest.main()
