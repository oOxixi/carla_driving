from __future__ import annotations

from .metrics import ScenarioRecorder
from .safety_supervisor import SafetySupervisor
from .scenario_runner import ScenarioRunner


def main() -> None:
    recorder = ScenarioRecorder("logs")
    supervisor = SafetySupervisor()

    command = {
        "schema_version": "1.0",
        "command_id": "cmd_4679fc8e",
        "source_text": "进入隧道了，减速哈。",
        "intent": "SLOW_DOWN",
        "parameters": {"mode": "RELATIVE", "action": "DECELERATE"},
        "asr_confidence": None,
        "intent_confidence": 0.95,
        "status": "valid",
        "ambiguity_type": "NONE",
        "confirm_required": False,
        "errors": [],
        "warnings": [],
        "confidence": 0.95,
        "e2e_latency_ms": 135.0,
    }
    recorder.log_command(command)

    decision = supervisor.arbitrate(
        raw_control={"steer": 0.0, "throttle": 0.25, "brake": 0.0},
        vehicle_state={"frame": 1, "sim_time_s": 0.05, "speed_mps": 6.0, "front_distance_m": 30.0},
        command=command,
        risk={"ttc_s": 10.0, "desired_gap_m": 12.0, "emergency_brake_requested": False},
        watchdog_alerts=[],
    )
    recorder.log_frame(frame=1, final_control=decision.final_control.to_dict(), safety_override=decision.safety_override, reason=decision.reason)

    runner = ScenarioRunner(recorder)
    result = runner.run("S05", "basic", lambda: {
        "status": "SUCCEEDED",
        "collision_count": 0,
        "red_light_violation_count": 0,
        "route_deviation_count": 0,
        "unfinished_task_count": 0,
        "safety_override_count": 1 if decision.safety_override else 0,
        "command_count": 1,
        "e2e_latency_ms": 135.0,
    })
    report = recorder.write_score_report([result])
    print("D fake integration finished. See logs/result.json and logs/score_report.json")


if __name__ == "__main__":
    main()
