"""Offline acceptance demo: voice-envelope -> A/B/C/D -> final control.

Run with: ``python -m integration.demo_offline``.  It has no CARLA or ASR
dependency and is therefore the first container smoke test.
"""
from __future__ import annotations

from car_control_A import RuntimeVehicleState
from car_control_A.routing import RouteReference
from car_control_B.pure_pursuit import PurePursuitController

from .contracts import PerceptionFrame
from .runtime_loop import ControlRuntime


def main() -> None:
    runtime = ControlRuntime(PurePursuitController())
    command = {"schema_version": "1.0", "command_id": "demo-speed", "source_text": "速度设为18公里每小时",
               "intent": "SET_SPEED", "parameters": {"speed": 18, "unit": "km/h"}, "asr_confidence": 0.99,
               "intent_confidence": 0.99, "confidence": 0.99, "status": "valid", "ambiguity_type": "NONE",
               "confirm_required": False, "errors": [], "warnings": []}
    runtime.submit_voice(command, now_s=0.05)
    vehicle = RuntimeVehicleState(1, 0.05, 0.0, 0.0, 0.0, 0.0, 0.0, "1")
    scene = PerceptionFrame(1, 0.05)
    route = RouteReference(((0.0, 0.0), (10.0, 0.0), (20.0, 0.0)), 0.0, 5.0)
    result = runtime.step(vehicle, scene, route, dt_s=0.05)
    print({"final_control": result.final_control.to_dict(), "safety_reason": result.safety_reason,
           "safety_override": result.safety_override})


if __name__ == "__main__":
    main()
