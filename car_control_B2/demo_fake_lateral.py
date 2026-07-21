"""No-CARLA smoke demo for B.

Run from repository root:
    python -m car_control_B.demo_fake_lateral
"""

from __future__ import annotations

import math

from .pure_pursuit import PurePursuitController, PurePursuitParams
from .schemas import RouteReference, VehiclePose


def straight_path(length_m: int = 60):
    return [(float(x), 0.0) for x in range(length_m)]


def curved_path():
    # quarter-like gentle arc
    return [(float(i), 0.04 * (float(i) ** 2) / 10.0) for i in range(60)]


def run_case(title: str, pose: VehiclePose, points):
    controller = PurePursuitController(PurePursuitParams(max_steer_delta_per_step=1.0))
    ref = RouteReference(points_xy_m=points, target_speed_mps=5.0)
    out = controller.step(pose, ref)
    print(title)
    print("pose=", pose)
    print("steer=%.3f cte=%.3f heading=%.3f target=%s reason=%s" % (out.steer, out.cross_track_error_m, out.heading_error_rad, out.target_point_xy_m, out.reason))
    print("-" * 60)


def main() -> None:
    run_case("center on straight: steer should be near 0", VehiclePose(0.0, 0.0, 0.0, 5.0), straight_path())
    run_case("vehicle left of path: CARLA steer should be positive/right", VehiclePose(0.0, 1.0, 0.0, 5.0), straight_path())
    run_case("vehicle right of path: CARLA steer should be negative/left", VehiclePose(0.0, -1.0, 0.0, 5.0), straight_path())
    run_case("gentle left curve ahead: steer should be negative/left under CARLA sign", VehiclePose(0.0, 0.0, 0.0, 5.0), curved_path())


if __name__ == "__main__":
    main()
