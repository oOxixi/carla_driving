#!/usr/bin/env python3
"""Build and validate deterministic in-memory scenario perturbations."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integration.generalization_gate import (  # noqa: E402
    GeneralizationMatrix,
    load_generalization_matrix,
    perturb_scenario,
)
from integration.scenario_execution import ScenarioSpec  # noqa: E402


def _scenario_paths(
    values: list[str], holdout: bool, matrix: GeneralizationMatrix,
) -> tuple[Path, ...]:
    if holdout:
        return tuple((ROOT / item).resolve() for item in matrix.holdout_scenarios)
    if values:
        return tuple(Path(item).expanduser().resolve() for item in values)
    return tuple(sorted((ROOT / "scenarios" / "official_competition").glob("*.json")))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", nargs="*", help="base scenario JSON; defaults to official competition scenarios")
    parser.add_argument("--matrix", help="generalization matrix JSON")
    parser.add_argument("--holdout", action="store_true", help="validate only the frozen holdout set")
    args = parser.parse_args()
    matrix = load_generalization_matrix(args.matrix)
    paths = _scenario_paths(args.scenario, args.holdout, matrix)
    failures: list[dict[str, str]] = []
    validated = 0
    with tempfile.TemporaryDirectory(prefix="carla-generalization-") as directory:
        root = Path(directory)
        for source in paths:
            raw = json.loads(source.read_text(encoding="utf-8"))
            for case in matrix.cases(str(raw.get("scenario_id", source.stem))):
                variant = perturb_scenario(raw, case)
                target = root / f"{case.case_id}.json"
                target.write_text(json.dumps(variant, ensure_ascii=False), encoding="utf-8")
                try:
                    ScenarioSpec.load(target)
                except Exception as error:
                    failures.append({
                        "case_id": case.case_id,
                        "error": f"{type(error).__name__}: {error}",
                    })
                else:
                    validated += 1
    result = {
        "status": "PASS" if not failures else "FAIL",
        "base_scenarios": len(paths),
        "validated_variants": validated,
        "failed_variants": len(failures),
        "matrix": str(matrix.source_path),
        "holdout": args.holdout,
        "failures": failures[:20],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
