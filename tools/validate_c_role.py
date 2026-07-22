"""Generate member C's deterministic pre-CARLA acceptance evidence.

This exercises the production C fusion/runtime code with deterministic inputs
and writes the distance/TTC examples, STOP curve, frozen parameter table, and
sensor-failure injection results requested by the 7/24 control-group plan.
"""

from __future__ import annotations

from dataclasses import asdict
import argparse
import csv
import json
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from car_control_A import RuntimeVehicleState  # noqa: E402
from car_control_A.routing import RouteReference  # noqa: E402
from car_control_B.pure_pursuit import PurePursuitController  # noqa: E402
from car_control_C import (  # noqa: E402
    ConservativeSensorFusion,
    LongitudinalParameters,
    SafetyStateParameters,
    VisualObservation,
)
from integration import ControlRuntime, PerceptionFrame  # noqa: E402


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError("CSV evidence must contain at least one row")
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _distance_ttc_samples() -> list[dict[str, object]]:
    fusion = ConservativeSensorFusion()
    rows: list[dict[str, object]] = []
    samples = (
        (1, 0.05, 30.0, 6.0),
        (2, 0.10, 20.0, 5.0),
        (3, 0.15, 12.0, 4.0),
        (4, 0.20, 7.0, 2.0),
        (5, 0.25, 4.0, 0.0),
    )
    for frame, sim_time_s, distance_m, lead_speed_mps in samples:
        summary = fusion.update(
            frame=frame,
            sim_time_s=sim_time_s,
            ego_speed_mps=8.0,
            front_distance_m=distance_m,
            lidar_valid=True,
            lead_speed_mps=lead_speed_mps,
            lead_speed_source="LIDAR_TRACKER_RELATIVE_SPEED",
            visual=VisualObservation(frame, True, "vehicle", 0.93, "RGB_DETECTOR_SAMPLE"),
        )
        rows.append({
            "frame": frame,
            "sim_time_s": sim_time_s,
            "front_distance_m": distance_m,
            "ego_speed_mps": 8.0,
            "lead_speed_mps": lead_speed_mps,
            "closing_speed_mps": summary.closing_speed_mps,
            "ttc_s": summary.ttc_s,
            "visual_class": summary.object_class,
            "visual_valid": summary.visual_valid,
            "lidar_valid": summary.lidar_valid,
            "fusion_mode": summary.fusion_mode,
            "recommended_action": summary.recommended_action,
            "reason": summary.reason,
        })
    return rows


def _voice_stop() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "command_id": "c-validation-stop",
        "source_text": "停车",
        "intent": "STOP",
        "parameters": {},
        "asr_confidence": 0.99,
        "intent_confidence": 0.99,
        "confidence": 0.99,
        "status": "valid",
        "ambiguity_type": "NONE",
        "confirm_required": False,
        "errors": [],
        "warnings": [],
        "valid_duration_s": 20.0,
    }


def _stop_curve() -> list[dict[str, object]]:
    dt_s = 0.05
    runtime = ControlRuntime(PurePursuitController(), default_speed_mps=8.0)
    runtime.submit_voice(_voice_stop(), now_s=0.0)
    route = RouteReference(((0.0, 0.0), (100.0, 0.0), (200.0, 0.0)), 0.0, 8.0)
    speed_mps = 8.0
    x_m = 0.0
    rows: list[dict[str, object]] = []
    hold_frames = 0
    for frame in range(1, 401):
        sim_time_s = frame * dt_s
        vehicle = RuntimeVehicleState(frame, sim_time_s, speed_mps, x_m, 0.0, 0.0, 0.0, "1")
        result = runtime.step(
            vehicle, PerceptionFrame(frame, sim_time_s), route, dt_s=dt_s,
        )
        control = result.final_control
        acceleration_mps2 = 2.5 * control.throttle - 5.0 * control.brake
        next_speed = max(0.0, speed_mps + acceleration_mps2 * dt_s)
        x_m += 0.5 * (speed_mps + next_speed) * dt_s
        rows.append({
            "frame": frame,
            "sim_time_s": round(sim_time_s, 4),
            "speed_mps": round(speed_mps, 6),
            "distance_travelled_m": round(x_m, 6),
            "target_speed_mps": None if result.longitudinal is None else result.longitudinal.target_speed_mps,
            "throttle": control.throttle,
            "brake": control.brake,
            "longitudinal_state": None if result.longitudinal is None else result.longitudinal.state,
            "safety_override": result.safety_override,
            "safety_reason": result.safety_reason,
        })
        speed_mps = next_speed
        hold_frames = hold_frames + 1 if float(rows[-1]["speed_mps"]) <= 0.15 and control.brake >= 0.55 else 0
        if hold_frames >= 20:
            break
    return rows


def _fault_injection() -> list[dict[str, object]]:
    fusion = ConservativeSensorFusion()
    invalid_lidar = fusion.update(
        frame=1, sim_time_s=0.05, ego_speed_mps=5.0,
        front_distance_m=None, lidar_valid=False,
        visual=VisualObservation.unavailable(1),
    )
    invalid_lidar_control = fusion.fail_closed_control()
    fusion.reset()
    range_conflict = fusion.update(
        frame=2, sim_time_s=0.10, ego_speed_mps=5.0,
        front_distance_m=None, lidar_valid=True,
        visual=VisualObservation(2, True, "pedestrian", 0.98, "RGB_DETECTOR_SAMPLE"),
    )
    conflict_control = fusion.fail_closed_control()
    fusion.reset()
    visual_missing = fusion.update(
        frame=3, sim_time_s=0.15, ego_speed_mps=5.0,
        front_distance_m=15.0, lidar_valid=True, lead_speed_mps=4.0,
        visual=VisualObservation.unavailable(3),
    )
    return [
        {
            "case": "lidar_invalid", "visual_valid": invalid_lidar.visual_valid,
            "lidar_valid": invalid_lidar.lidar_valid, "action": invalid_lidar.recommended_action,
            "reason": invalid_lidar.reason, "throttle": invalid_lidar_control.throttle,
            "brake": invalid_lidar_control.brake,
            "pass": invalid_lidar.fail_closed and invalid_lidar_control.brake == 1.0,
        },
        {
            "case": "rgb_hazard_without_lidar_range", "visual_valid": range_conflict.visual_valid,
            "lidar_valid": range_conflict.lidar_valid, "action": range_conflict.recommended_action,
            "reason": range_conflict.reason, "throttle": conflict_control.throttle,
            "brake": conflict_control.brake,
            "pass": range_conflict.fail_closed and conflict_control.brake == 1.0,
        },
        {
            "case": "rgb_detector_unavailable_lidar_valid", "visual_valid": visual_missing.visual_valid,
            "lidar_valid": visual_missing.lidar_valid, "action": visual_missing.recommended_action,
            "reason": visual_missing.reason, "throttle": None, "brake": None,
            "pass": visual_missing.object_class is None and visual_missing.fusion_mode == "LIDAR_ONLY",
        },
    ]


def validate(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    distance_rows = _distance_ttc_samples()
    stop_rows = _stop_curve()
    fault_rows = _fault_injection()
    _write_csv(output_dir / "front_distance_ttc_samples.csv", distance_rows)
    _write_csv(output_dir / "stop_curve.csv", stop_rows)
    (output_dir / "fault_injection.json").write_text(
        json.dumps(fault_rows, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8",
    )

    stopped_rows = [row for row in stop_rows if float(row["speed_mps"]) <= 0.15]
    stop_time_s = None if not stopped_rows else stopped_rows[0]["sim_time_s"]
    hold_tail = stop_rows[-20:]
    checks = {
        "distance_ttc_has_emergency_transition": any(
            row["recommended_action"] == "EMERGENCY_BRAKE" for row in distance_rows
        ),
        "stop_reached_within_8s": stop_time_s is not None and float(stop_time_s) <= 8.0,
        "stop_hold_maintained_for_20_frames": len(hold_tail) == 20 and all(
            float(row["speed_mps"]) <= 0.15 and float(row["throttle"]) == 0.0
            and float(row["brake"]) >= 0.55 for row in hold_tail
        ),
        "all_fault_injections_pass": all(bool(row["pass"]) for row in fault_rows),
    }
    report = {
        "schema_version": "1.0",
        "scope": "member_C_pre_CARLA_deterministic_acceptance",
        "limitations": [
            "This is a deterministic controller/fusion validation, not a live CARLA road test.",
            "RGB semantics are injected for this deterministic curve; ONNX decoding and bridge failure behaviour are covered separately by integration tests.",
        ],
        "upstream_sync": {
            "repository": "https://github.com/oOxixi/carla_driving",
            "main_observed_commit": "42ce0500150e5b3f150d987cfb225c8e33f9a0f0",
            "rgb_onnx_source_commit": "ef7950a408e7fe4a647f23f2e667e377066612a1",
        },
        "parameters": {
            "longitudinal": asdict(LongitudinalParameters()),
            "safety_state": asdict(SafetyStateParameters()),
        },
        "metrics": {
            "stop_time_s": stop_time_s,
            "stop_distance_m": stop_rows[-1]["distance_travelled_m"],
            "stop_curve_frames": len(stop_rows),
            "minimum_sample_ttc_s": min(
                float(row["ttc_s"]) for row in distance_rows if row["ttc_s"] is not None
            ),
        },
        "checks": checks,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "files": {
            "front_distance_ttc_samples": "front_distance_ttc_samples.csv",
            "stop_curve": "stop_curve.csv",
            "fault_injection": "fault_injection.json",
        },
    }
    (output_dir / "summary.json").write_text(
        json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path,
        default=REPOSITORY_ROOT / "artifacts" / "C_role_validation",
    )
    args = parser.parse_args()
    report = validate(args.output_dir.resolve())
    print(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
