"""Compare maneuver plan speeds with applied longitudinal targets and telemetry."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from statistics import median


def read_jsonl(file):
    return [json.loads(line) for line in file.read_text(encoding="utf-8").splitlines() if line.strip()]


def kmh(value):
    return None if value is None else round(value * 3.6, 3)


def summarize(folder):
    event_files = list((folder / "evidence").glob("*.jsonl"))
    if len(event_files) != 1:
        return {"error": "missing or ambiguous evidence", "evidence_files": len(event_files)}
    rows = read_jsonl(event_files[0])
    models = [r["payload"]["orchestration"] for r in rows if r.get("phase") == "RESOLVE"]
    submission = [r["payload"]["orchestration"]["model_request"] for r in rows if r.get("phase") == "SUBMIT"]
    if len(submission) != 1 or len(models) != 1:
        return {"error": "missing or ambiguous request", "submissions": len(submission), "resolutions": len(models)}
    cid = submission[0]["command_id"]
    if models[0]["command_id"] != cid:
        raise ValueError("Unmatched resolution")
    plan = models[0].get("decision_plan") or {}
    request = submission[0]
    ref = request.get("rgb_ref")
    image = (folder.parent / ref).resolve() if ref else None
    if image is not None and not image.is_relative_to(folder.resolve()):
        raise ValueError("RGB does not belong to this arm")
    steps = plan.get("steps", [])
    phases = [r["payload"] for r in rows if r.get("phase") == "MANEUVER_EVENT" and r.get("command_id") == cid]
    frames = [r for r in rows if r.get("record_type") == "frame"]
    phases_by_step = []
    for i, step in enumerate(steps):
        begin = next((x for x in phases if x["event_type"] == "qwen_step_started" and x["step_id"] == step["step_id"]), None)
        following = next((x for x in phases if x["event_type"] == "qwen_step_started"
                          and i + 1 < len(steps) and x["step_id"] == steps[i + 1]["step_id"]), None)
        completed = next((x for x in phases if x["event_type"] == "qwen_step_completed" and x["step_id"] == step["step_id"]), None)
        at = [x for x in frames if begin and x["sim_time_s"] > begin["now_s"]
              and (not following or x["sim_time_s"] <= following["now_s"])
              and (not completed or x["sim_time_s"] <= completed["now_s"])]
        actual = [x["vehicle"]["speed_mps"] for x in at]
        targets = [(x.get("longitudinal") or {}).get("target_speed_mps") for x in at]
        phases_by_step.append({
            "behavior": step["behavior"], "plan_target_kmh": kmh(step["target"]["target_speed_mps"]),
            "started_s": None if begin is None else begin["now_s"],
            "completed_s": None if completed is None else completed["now_s"], "frames": len(at),
            "actual_kmh_median": kmh(median(actual)) if actual else None,
            "actual_kmh_max": kmh(max(actual)) if actual else None,
            "control_targets_kmh": sorted({kmh(v) for v in targets if v is not None}),
        })
    terminal = [r for r in phases if r["event_type"] == "qwen_terminal"]
    last = next((r["summary"] for r in reversed(rows) if r.get("record_type") == "run_complete"), {})
    return {"model_id": plan.get("model_id"), "request_frame": request["scene_summary"]["frame_id"],
            "rgb_sha256": sha256(image.read_bytes()).hexdigest() if image and image.is_file() else None,
            "disposition": models[0]["disposition"], "reason": models[0]["reason_code"],
            "feedback": models[0]["feedback"], "steps": phases_by_step, "terminal": terminal,
            "route_status": last.get("status"), "collisions": last.get("collision_count"),
            "unplanned_lane_invasions": last.get("lane_invasion_count")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    a = parser.parse_args()
    report = {p.name: summarize(p) for p in sorted(a.run.iterdir()) if (p / "runner.log").exists()}
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    with (a.run / "phase_summary.json").open("x", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
