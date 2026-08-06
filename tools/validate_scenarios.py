import json
from pathlib import Path

REQUIRED_TOP = [
    "schema_version", "scenario_id", "category", "official_level",
    "map", "weather", "seed", "runtime", "ego_spawn",
    "route", "commands", "expected"
]

VALID_CATEGORIES = {
    "smoke", "lateral_B", "safety_D", "regression",
    "qwen_routing", "qwen_fullchain", "qwen_faults",
}
VALID_LEVELS = {"basic", "advanced", "challenge"}

def validate_one(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = []

    for key in REQUIRED_TOP:
        if key not in data:
            errors.append(f"missing key: {key}")

    if data.get("category") not in VALID_CATEGORIES:
        errors.append(f"invalid category: {data.get('category')}")

    if data.get("official_level") not in VALID_LEVELS:
        errors.append(f"invalid official_level: {data.get('official_level')}")

    route = data.get("route", {})
    points = route.get("points_xy_m", [])
    if not isinstance(points, list) or len(points) < 2:
        errors.append("route.points_xy_m must have at least 2 points")

    commands = data.get("commands", [])
    if not isinstance(commands, list) or len(commands) < 1:
        errors.append("commands must have at least 1 command")

    runtime = data.get("runtime", {})
    if runtime.get("duration_s", 0) <= 0:
        errors.append("runtime.duration_s must be positive")

    qwen_expected = data.get("qwen_expected")
    qwen_fault = data.get("qwen_fault")
    if data.get("category", "").startswith("qwen_"):
        if not isinstance(qwen_expected, dict):
            errors.append("qwen_* categories require qwen_expected")
        else:
            required_qwen = {
                "route", "min_calls", "max_calls", "expected_behaviors",
                "expected_terminal", "allowed_replans", "forbidden_low_level_fields",
            }
            missing = sorted(required_qwen - set(qwen_expected))
            if missing:
                errors.append("qwen_expected missing: " + ", ".join(missing))
            minimum = qwen_expected.get("min_calls", -1)
            maximum = qwen_expected.get("max_calls", -1)
            if type(minimum) is not int or type(maximum) is not int or not 0 <= minimum <= maximum:
                errors.append("qwen_expected calls must satisfy 0 <= min_calls <= max_calls")
            if qwen_expected.get("forbidden_low_level_fields") is not True:
                errors.append("qwen_expected.forbidden_low_level_fields must be true")
    if qwen_fault is not None:
        if data.get("category") != "qwen_faults":
            errors.append("qwen_fault is allowed only in qwen_faults scenarios")
        elif not isinstance(qwen_fault, dict):
            errors.append("qwen_fault must be an object")
        elif qwen_fault.get("type") == "TIMEOUT":
            delay_ms = qwen_fault.get("delay_ms")
            if type(delay_ms) not in (int, float) or isinstance(delay_ms, bool) or delay_ms <= 0:
                errors.append("TIMEOUT qwen_fault requires positive delay_ms")
        elif qwen_fault.get("type") == "LOW_LEVEL_FIELD":
            if qwen_fault.get("field") not in {
                "throttle", "brake", "steer", "steering_angle", "wheel_angle", "torque",
            }:
                errors.append("LOW_LEVEL_FIELD qwen_fault has invalid field")
            value = qwen_fault.get("value")
            if type(value) not in (int, float) or isinstance(value, bool):
                errors.append("LOW_LEVEL_FIELD qwen_fault value must be numeric")
        else:
            errors.append("unsupported qwen_fault.type")

    return errors

def main():
    root = Path(__file__).resolve().parents[1] / "scenarios"
    metadata_files = {"index.json", "matrix.json", "scenario_schema.json"}
    files = [p for p in root.rglob("*.json") if p.name not in metadata_files]
    total = 0
    failed = 0

    for path in sorted(files):
        total += 1
        errors = validate_one(path)
        if errors:
            failed += 1
            print(f"[FAIL] {path.relative_to(root)}")
            for e in errors:
                print(f"  - {e}")
        else:
            print(f"[OK]   {path.relative_to(root)}")

    print(f"\nchecked={total}, failed={failed}")
    if failed:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
