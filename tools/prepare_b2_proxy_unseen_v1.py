#!/usr/bin/env python3
"""Freeze a prospective 240-slot B2 proxy acquisition before inference."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import sys
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from challenge.benchmark.case_manifest import (  # noqa: E402
    normalized_request_sha256,
    source_text_sha256,
)
from challenge.benchmark.policy_manifest import (  # noqa: E402
    build_policy_manifest,
    canonical_policy_manifest_json,
    load_benchmark_policy_config,
    policy_manifest_sha256,
)
from integration.generalization_gate import (  # noqa: E402
    PerturbationCase,
    perturb_scenario,
)
from integration.scenario_execution import ScenarioSpec  # noqa: E402


DEFAULT_DESIGN = Path(
    "challenge/benchmark/b2_proxy_unseen_v1/acquisition_design.json"
)


class FreezeError(RuntimeError):
    """Raised when the prospective benchmark cannot be frozen safely."""


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_json(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _canonical_json_line(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _write_json(path: Path, value: Any) -> str:
    payload = _canonical_json(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return _sha256_bytes(payload)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise FreezeError(f"cannot read JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise FreezeError(f"{path} must contain a JSON object")
    return value


def _resolve(repo: Path, value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (repo / path).resolve()


def _read_jsonl(paths: Iterable[Path]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for path in paths:
        if not path.is_file():
            raise FreezeError(f"exposure source is missing: {path}")
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            1,
        ):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise FreezeError(f"{path}:{line_number} is not an object")
            result.append(value)
    return result


def _metadata(record: Mapping[str, Any]) -> Mapping[str, Any]:
    value = record.get("metadata")
    return value if isinstance(value, Mapping) else {}


def _visual(record: Mapping[str, Any]) -> Mapping[str, Any]:
    value = record.get("visual_input")
    return value if isinstance(value, Mapping) else {}


def _identity_sets(rows: Iterable[dict[str, Any]]) -> dict[str, set[str | int]]:
    result: dict[str, set[str | int]] = {
        "sample_id": set(),
        "scenario_id": set(),
        "group_key": set(),
        "rgb_sha256": set(),
        "source_text_sha256": set(),
        "normalized_request_sha256": set(),
        "seed": set(),
    }
    for row in rows:
        metadata = _metadata(row)
        visual = _visual(row)
        request = row.get("model_request")
        values: dict[str, Any] = {
            "sample_id": row.get("sample_id"),
            "scenario_id": metadata.get("scenario_id"),
            "group_key": metadata.get("group_key"),
            "rgb_sha256": visual.get("rgb_sha256"),
            "seed": metadata.get("seed"),
        }
        for field, value in values.items():
            if isinstance(value, (str, int)) and not isinstance(value, bool):
                if not isinstance(value, str) or value.strip():
                    result[field].add(value)
        if isinstance(request, Mapping):
            result["source_text_sha256"].add(
                source_text_sha256(request.get("source_text"))
            )
            result["normalized_request_sha256"].add(
                normalized_request_sha256(row)
            )
    return result


def _set_digest(values: Iterable[str | int]) -> str:
    payload = json.dumps(
        sorted(str(value) for value in values),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256_bytes(payload)


def _git_sha(repo: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _verify_candidate(repo: Path, design: Mapping[str, Any]) -> dict[str, Any]:
    candidate = design.get("candidate")
    if not isinstance(candidate, Mapping):
        raise FreezeError("design.candidate must be an object")
    paths = {
        key: _resolve(repo, str(candidate[key]))
        for key in (
            "weights_path",
            "onnx_path",
            "export_evidence_path",
            "handoff_path",
            "adapter_path",
        )
    }
    for label, path in paths.items():
        if not path.is_file():
            raise FreezeError(f"candidate {label} is missing: {path}")

    actual_weights = _sha256_file(paths["weights_path"])
    actual_onnx = _sha256_file(paths["onnx_path"])
    actual_adapter = _sha256_file(paths["adapter_path"])
    if actual_weights != candidate.get("weights_sha256"):
        raise FreezeError("candidate weights SHA256 mismatch")
    if actual_onnx != candidate.get("onnx_sha256"):
        raise FreezeError("candidate ONNX SHA256 mismatch")
    if actual_adapter != candidate.get("adapter_sha256"):
        raise FreezeError("candidate Adapter SHA256 mismatch")

    export = _read_json(paths["export_evidence_path"])
    if export.get("status") != "PASS":
        raise FreezeError("ONNX export evidence is not PASS")
    if export.get("weights_sha256") != actual_weights:
        raise FreezeError("export evidence does not bind candidate weights")
    if export.get("onnx_sha256") != actual_onnx:
        raise FreezeError("export evidence does not bind candidate ONNX")
    handoff = _read_json(paths["handoff_path"])
    identity = handoff.get("candidate_identity")
    if not isinstance(identity, Mapping):
        raise FreezeError("handoff candidate_identity is missing")
    for field in ("model_id", "config_id", "dataset_version", "weights_sha256"):
        expected_field = (
            "training_dataset_version" if field == "dataset_version" else field
        )
        if identity.get(field) != candidate.get(expected_field):
            raise FreezeError(f"handoff candidate {field} mismatch")

    return {
        "model_id": candidate["model_id"],
        "config_id": candidate["config_id"],
        "training_dataset_version": candidate["training_dataset_version"],
        "weights_sha256": actual_weights,
        "onnx_sha256": actual_onnx,
        "adapter_contract_id": candidate["adapter_contract_id"],
        "adapter_sha256": actual_adapter,
        "handoff_sha256": _sha256_file(paths["handoff_path"]),
        "export_evidence_sha256": _sha256_file(paths["export_evidence_path"]),
    }


def _derive_seed(
    freeze_id: str,
    cohort: str,
    slot_id: str,
    forbidden: set[int],
    allocated: set[int],
) -> int:
    for attempt in range(1000):
        payload = f"{freeze_id}|{cohort}|{slot_id}|{attempt}".encode("utf-8")
        seed = int.from_bytes(hashlib.sha256(payload).digest()[:4], "big") & 0x7FFFFFFF
        if seed not in forbidden and seed not in allocated:
            allocated.add(seed)
            return seed
    raise FreezeError(f"cannot derive a unique seed for {slot_id}")


def _commands(scenario: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw = scenario.get("commands")
    if not isinstance(raw, list) or not raw:
        raise FreezeError("scenario must contain at least one command")
    if not all(isinstance(item, Mapping) for item in raw):
        raise FreezeError("scenario commands must be objects")
    return list(raw)


def _materialize_scenario(
    raw: Mapping[str, Any],
    *,
    freeze_id: str,
    cohort: str,
    slot_id: str,
    seed: int,
    repeat_index: int,
    axes: Mapping[str, Any],
    base_path: str,
) -> dict[str, Any]:
    base_id = str(raw.get("scenario_id", "")).strip()
    if not base_id:
        raise FreezeError(f"base scenario lacks scenario_id: {base_path}")
    weather_values = list(axes["weather"])
    longitudinal = list(axes["actor_longitudinal_offset_m"])
    lateral = list(axes["actor_lateral_offset_m"])
    speed = list(axes["actor_speed_scale"])
    brake = list(axes["brake_time_offset_s"])
    pedestrian = list(axes["pedestrian_start_offset_s"])
    case_id = f"B2P1_{cohort.upper()}_{slot_id}_{base_id}"

    if cohort == "seen":
        scenario = copy.deepcopy(dict(raw))
        scenario["scenario_id"] = case_id
        scenario["seed"] = seed
    else:
        perturbation = PerturbationCase(
            case_id=case_id,
            map_name=str(raw.get("map")),
            weather=str(weather_values[repeat_index % len(weather_values)]),
            seed=seed,
            fixed_delta_s=float(
                (raw.get("runtime") or {}).get("fixed_delta_seconds", 0.05)
            ),
            actor_longitudinal_offset_m=float(
                longitudinal[repeat_index % len(longitudinal)]
            ),
            actor_lateral_offset_m=float(lateral[repeat_index % len(lateral)]),
            actor_speed_scale=float(speed[repeat_index % len(speed)]),
            brake_time_offset_s=float(brake[repeat_index % len(brake)]),
            pedestrian_start_offset_s=float(
                pedestrian[repeat_index % len(pedestrian)]
            ),
            actor_count_scale=1.0,
            target_lane_relation="CURRENT",
            sensor_condition="nominal",
        )
        scenario = perturb_scenario(raw, perturbation)
        generalization = (
            scenario.setdefault("extensions", {})
            .setdefault("generalization_case", {})
        )
        generalization["kind"] = cohort

    extensions = scenario.setdefault("extensions", {})
    if not isinstance(extensions, dict):
        raise FreezeError(f"{base_path}: extensions must be an object")
    commands = _commands(scenario)
    command_ordinal = repeat_index % len(commands)
    extensions["b2_benchmark_case"] = {
        "freeze_id": freeze_id,
        "cohort": cohort,
        "slot_id": slot_id,
        "base_scenario_id": base_id,
        "base_scenario_path": base_path,
        "command_ordinal": command_ordinal,
        "selection_rule": "EXACT_PREDECLARED_COMMAND_ORDINAL",
    }
    return scenario


def _validate_base_membership(
    *,
    cohort: str,
    base_id: str,
    exposed_scenario_ids: set[str | int],
) -> bool:
    """Enforce the frozen template-exposure rule for one cohort base."""

    in_exposure = base_id in exposed_scenario_ids
    if cohort in {"seen", "variant"} and not in_exposure:
        raise FreezeError(
            f"{cohort} base scenario is absent from governed exposure: {base_id}"
        )
    if cohort == "unseen" and in_exposure:
        raise FreezeError(
            f"unseen base scenario appears in governed exposure: {base_id}"
        )
    if cohort not in {"seen", "variant", "unseen"}:
        raise FreezeError(f"unsupported cohort: {cohort}")
    return in_exposure


def _scenario_payload(scenario: Mapping[str, Any]) -> bytes:
    return _canonical_json(dict(scenario))


def _build_exposure(
    repo: Path,
    design: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, set[str | int]]]:
    raw_sources = design.get("exposure_jsonl")
    if not isinstance(raw_sources, Mapping):
        raise FreezeError("design.exposure_jsonl must be an object")
    all_rows: list[dict[str, Any]] = []
    partitions: dict[str, Any] = {}
    for partition, values in raw_sources.items():
        if not isinstance(values, list) or not values:
            raise FreezeError(f"exposure partition {partition} must be non-empty")
        paths = [_resolve(repo, str(value)) for value in values]
        rows = _read_jsonl(paths)
        all_rows.extend(rows)
        identities = _identity_sets(rows)
        partitions[str(partition)] = {
            "row_count": len(rows),
            "files": [
                {
                    "path": path.relative_to(repo).as_posix(),
                    "sha256": _sha256_file(path),
                    "size_bytes": path.stat().st_size,
                }
                for path in paths
            ],
            "unique_counts": {
                key: len(value) for key, value in identities.items()
            },
            "set_digests": {
                key: _set_digest(value) for key, value in identities.items()
            },
        }
    combined = _identity_sets(all_rows)
    return {
        "schema_version": "1.0",
        "partitions": partitions,
        "combined_row_count": len(all_rows),
        "combined_unique_counts": {
            key: len(value) for key, value in combined.items()
        },
        "combined_set_digests": {
            key: _set_digest(value) for key, value in combined.items()
        },
    }, combined


def freeze(args: argparse.Namespace) -> dict[str, Any]:
    repo = Path(args.repo_root).resolve()
    design_path = _resolve(repo, args.design)
    output = _resolve(repo, args.output)
    staging = output.with_name(output.name + ".tmp")
    if output.exists() or staging.exists():
        raise FreezeError("output or temporary freeze directory already exists")
    design = _read_json(design_path)
    freeze_id = str(design.get("freeze_id", "")).strip()
    if not freeze_id:
        raise FreezeError("freeze_id is missing")

    candidate = _verify_candidate(repo, design)
    policy_config_path = _resolve(repo, str(design["policy_config_path"]))
    policy_config = load_benchmark_policy_config(policy_config_path)
    policy_manifest = build_policy_manifest(policy_config)
    policy_payload = canonical_policy_manifest_json(policy_manifest)
    policy_sha = policy_manifest_sha256(policy_manifest)
    exposure_report, exposed = _build_exposure(repo, design)

    cohorts = design.get("cohorts")
    axes = design.get("variant_axes")
    expected = design.get("expected_slots")
    if not isinstance(cohorts, Mapping) or not isinstance(axes, Mapping):
        raise FreezeError("cohorts and variant_axes must be objects")
    if not isinstance(expected, Mapping):
        raise FreezeError("expected_slots must be an object")
    samples_per_base = int(design.get("samples_per_base", 0))
    if samples_per_base < 1:
        raise FreezeError("samples_per_base must be positive")

    staging.mkdir(parents=True)
    slots: list[dict[str, Any]] = []
    scenario_ids: set[str] = set()
    allocated_seeds: set[int] = set()
    forbidden_seeds = {
        int(value) for value in exposed["seed"] if isinstance(value, int)
    }
    base_membership: dict[str, bool] = {}
    validation_failures: list[dict[str, str]] = []
    try:
        scenario_root = staging / "scenarios"
        scenario_root.mkdir()
        for cohort in ("seen", "variant", "unseen"):
            base_paths = cohorts.get(cohort)
            if not isinstance(base_paths, list) or not base_paths:
                raise FreezeError(f"cohort {cohort} must list base scenarios")
            for base_index, base_value in enumerate(base_paths):
                base_path = _resolve(repo, str(base_value))
                raw = _read_json(base_path)
                base_id = str(raw.get("scenario_id", "")).strip()
                in_exposure = _validate_base_membership(
                    cohort=cohort,
                    base_id=base_id,
                    exposed_scenario_ids=exposed["scenario_id"],
                )
                base_membership[base_id] = in_exposure
                commands = _commands(raw)
                for repeat_index in range(samples_per_base):
                    sequence = len(slots)
                    slot_id = f"{sequence:03d}"
                    seed = _derive_seed(
                        freeze_id,
                        cohort,
                        slot_id,
                        forbidden_seeds,
                        allocated_seeds,
                    )
                    scenario = _materialize_scenario(
                        raw,
                        freeze_id=freeze_id,
                        cohort=cohort,
                        slot_id=slot_id,
                        seed=seed,
                        repeat_index=repeat_index,
                        axes=axes,
                        base_path=base_path.relative_to(repo).as_posix(),
                    )
                    scenario_id = str(scenario["scenario_id"])
                    if scenario_id in scenario_ids or scenario_id in exposed["scenario_id"]:
                        raise FreezeError(f"scenario_id collision: {scenario_id}")
                    scenario_ids.add(scenario_id)
                    payload = _scenario_payload(scenario)
                    relative = Path("scenarios") / f"{scenario_id}.json"
                    target = staging / relative
                    target.write_bytes(payload)
                    try:
                        ScenarioSpec.load(target)
                    except Exception as error:  # noqa: BLE001 - preserve audit detail
                        validation_failures.append(
                            {
                                "slot_id": slot_id,
                                "scenario_id": scenario_id,
                                "error": f"{type(error).__name__}: {error}",
                            }
                        )
                    command_ordinal = repeat_index % len(commands)
                    slots.append(
                        {
                            "slot_id": slot_id,
                            "cohort": cohort,
                            "base_index": base_index,
                            "base_scenario_id": base_id,
                            "base_scenario_path": base_path.relative_to(repo).as_posix(),
                            "scenario_id": scenario_id,
                            "scenario_path": relative.as_posix(),
                            "scenario_sha256": _sha256_bytes(payload),
                            "template_id": "b2tpl_" + _sha256_bytes(payload)[:24],
                            "seed": seed,
                            "command_ordinal": command_ordinal,
                            "selection_rule": "FIRST_QUALITY_VALID_RUN_EXACT_COMMAND_ORDINAL",
                        }
                    )

        counts = Counter(str(slot["cohort"]) for slot in slots)
        expected_counts = {
            key: int(expected[key]) for key in ("seen", "variant", "unseen")
        }
        if dict(counts) != expected_counts:
            raise FreezeError(
                f"cohort counts do not match design: {dict(counts)} != {expected_counts}"
            )
        if len(slots) != int(expected["total"]):
            raise FreezeError("total acquisition slot count mismatch")
        if validation_failures:
            raise FreezeError(
                f"{len(validation_failures)} materialized scenarios failed validation"
            )

        slots_payload = b"".join(_canonical_json_line(slot) for slot in slots)
        (staging / "acquisition_slots.jsonl").write_bytes(slots_payload)
        scenario_manifest = {
            "schema_version": "1.0",
            "freeze_id": freeze_id,
            "slot_count": len(slots),
            "cohort_counts": dict(sorted(counts.items())),
            "unique_seed_count": len(allocated_seeds),
            "seed_overlap_with_governed_data": 0,
            "unique_scenario_id_count": len(scenario_ids),
            "scenario_id_overlap_with_governed_data": 0,
            "all_scenarios_schema_valid": True,
            "base_scenario_exposure": base_membership,
            "slots_sha256": _sha256_bytes(slots_payload),
            "scenario_set_digest": _set_digest(
                slot["scenario_sha256"] for slot in slots
            ),
        }
        _write_json(staging / "scenario_manifest.json", scenario_manifest)
        _write_json(staging / "exposure_inventory.json", exposure_report)
        (staging / "policy_manifest.json").write_bytes(policy_payload)
        _write_json(staging / "candidate_freeze.json", candidate)
        shutil.copyfile(design_path, staging / "acquisition_design.json")

        freeze_lock = {
            "schema_version": "1.0",
            "freeze_id": freeze_id,
            "status": "ACQUISITION_AND_POLICY_FROZEN_AWAITING_COLLECTION",
            "benchmark_case_status": "NOT_YET_COLLECTED",
            "formal_gate_decision": False,
            "executor_role": "A2_ACTING_AS_B2_PROXY",
            "independence_model": "PROSPECTIVE_TEMPORAL_HOLDOUT",
            "evaluation_git_sha": _git_sha(repo),
            "candidate": candidate,
            "policy_manifest_sha256": policy_sha,
            "acquisition_design_sha256": _sha256_file(
                staging / "acquisition_design.json"
            ),
            "acquisition_slots_sha256": _sha256_file(
                staging / "acquisition_slots.jsonl"
            ),
            "scenario_manifest_sha256": _sha256_file(
                staging / "scenario_manifest.json"
            ),
            "exposure_inventory_sha256": _sha256_file(
                staging / "exposure_inventory.json"
            ),
            "slot_count": len(slots),
            "cohort_counts": dict(sorted(counts.items())),
            "collection_requirements": design["collection_requirements"],
            "next_transition": (
                "Collect exact frozen slots with exact pinned Teacher v4; "
                "then run post-collection leakage and quality preflight before any Student inference."
            ),
            "fail_closed_blockers": [
                "FRESH_240_CASES_NOT_COLLECTED",
                "EXACT_TEACHER_V4_SERVICE_NOT_REACHABLE_FROM_CURRENT_HOST",
                "CARLA_RUNTIME_NOT_AVAILABLE_ON_CURRENT_HOST",
                "CASE_MANIFEST_AND_CASE_SET_DIGEST_NOT_YET_ISSUED",
            ],
        }
        _write_json(staging / "FREEZE_LOCK.json", freeze_lock)

        names = sorted(
            path.relative_to(staging).as_posix()
            for path in staging.rglob("*")
            if path.is_file() and path.name != "SHA256SUMS"
        )
        lines = [f"{_sha256_file(staging / name)}  {name}" for name in names]
        (staging / "SHA256SUMS").write_text(
            "\n".join(lines) + "\n",
            encoding="ascii",
            newline="\n",
        )
        staging.replace(output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    return {
        "status": "ACQUISITION_AND_POLICY_FROZEN_AWAITING_COLLECTION",
        "output": str(output),
        "freeze_id": freeze_id,
        "slots": len(slots),
        "cohort_counts": dict(sorted(Counter(slot["cohort"] for slot in slots).items())),
        "policy_manifest_sha256": policy_sha,
        "freeze_lock_sha256": _sha256_file(output / "FREEZE_LOCK.json"),
        "formal_gate_decision": False,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repo-root", default=".")
    result.add_argument("--design", default=str(DEFAULT_DESIGN))
    result.add_argument("--output", required=True)
    return result


def main() -> int:
    try:
        result = freeze(parser().parse_args())
    except (FreezeError, OSError, ValueError, KeyError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
