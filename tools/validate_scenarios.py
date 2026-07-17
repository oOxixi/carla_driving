import json
from pathlib import Path

REQUIRED_TOP = [
    "schema_version", "scenario_id", "category", "official_level",
    "map", "weather", "seed", "runtime", "ego_spawn",
    "route", "commands", "expected"
]

VALID_CATEGORIES = {"smoke", "lateral_B", "safety_D", "regression"}
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

    return errors

def main():
    root = Path(__file__).resolve().parents[1] / "scenarios"
    files = [p for p in root.rglob("*.json") if p.name not in {"index.json", "scenario_schema.json"}]
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
