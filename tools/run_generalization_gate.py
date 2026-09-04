#!/usr/bin/env python3
"""Build and validate deterministic in-memory scenario perturbations."""
from __future__ import annotations

import argparse
from contextlib import nullcontext
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
    parser.add_argument(
        "--kind", choices=("all", "variant", "unseen"), default="all",
        help="keep same-map variants, cross-map unseen cases, or both",
    )
    parser.add_argument(
        "--output-dir",
        help="write concrete reproducible scenario JSON files instead of temporary files",
    )
    parser.add_argument(
        "--max-per-scenario", type=int,
        help="bound emitted cases per base scenario after --kind filtering",
    )
    args = parser.parse_args()
    if args.max_per_scenario is not None and args.max_per_scenario < 1:
        parser.error("--max-per-scenario must be positive")
    matrix = load_generalization_matrix(args.matrix)
    paths = _scenario_paths(args.scenario, args.holdout, matrix)
    failures: list[dict[str, str]] = []
    validated = 0
    if args.output_dir:
        output_root = Path(args.output_dir).expanduser().resolve()
        output_root.mkdir(parents=True, exist_ok=True)
        output_context = nullcontext(str(output_root))
    else:
        output_context = tempfile.TemporaryDirectory(prefix="carla-generalization-")
    emitted_variant = emitted_unseen = 0
    with output_context as directory:
        root = Path(directory)
        for source in paths:
            raw = json.loads(source.read_text(encoding="utf-8"))
            emitted_for_source = 0
            for case in matrix.cases(str(raw.get("scenario_id", source.stem))):
                variant = perturb_scenario(raw, case)
                case_kind = str(
                    variant.get("extensions", {})
                    .get("generalization_case", {})
                    .get("kind", "variant")
                )
                if args.kind != "all" and case_kind != args.kind:
                    continue
                if (
                    args.max_per_scenario is not None
                    and emitted_for_source >= args.max_per_scenario
                ):
                    break
                target = root / f"{case.case_id}.json"
                target.write_text(
                    json.dumps(variant, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                try:
                    ScenarioSpec.load(target)
                except Exception as error:
                    failures.append({
                        "case_id": case.case_id,
                        "error": f"{type(error).__name__}: {error}",
                    })
                else:
                    validated += 1
                    emitted_for_source += 1
                    if case_kind == "unseen":
                        emitted_unseen += 1
                    else:
                        emitted_variant += 1
    result = {
        "status": "PASS" if not failures else "FAIL",
        "base_scenarios": len(paths),
        "validated_variants": validated,
        "failed_variants": len(failures),
        "matrix": str(matrix.source_path),
        "holdout": args.holdout,
        "kind": args.kind,
        "variant_cases": emitted_variant,
        "unseen_cases": emitted_unseen,
        "output_dir": str(output_root) if args.output_dir else None,
        "failures": failures[:20],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
