#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

DATASET_VERSION = "teacher_distill_v0.2_d1_pinned"
TEACHER_PROFILE = "b1-pinned-teacher-v1"
EXPECTED_MODEL_ID = "Qwen/Qwen3.5-2B"
EXPECTED_MODEL_REVISION = "15852e8c16360a2fea060d615a32b45270f8a8fc"
EXPECTED_ARTIFACT_SHA256 = "4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa"
EXPECTED_BASELINE_GIT_SHA = "a05c8b76efcd4c176965223c661f40b153cb1836"
DEFAULT_TARGET_VALID = 200
MAX_TARGETS = 8
NO_TARGET_INDEX = 8


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, 1):
            if not raw.strip():
                continue
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: expected JSON object")
            rows.append(value)
    return rows


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")


def count_jsonl(path: Path) -> int:
    return len(read_jsonl(path))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def current_head(repo: Path) -> str:
    return git(repo, "rev-parse", "HEAD")


def current_branch(repo: Path) -> str:
    return git(repo, "branch", "--show-current")


def verify_tracked_file_matches_head(
    repo: Path,
    relative_path: str,
) -> dict[str, Any]:
    worktree_path = repo / relative_path

    if not worktree_path.is_file():
        raise RuntimeError(f"required tracked file missing: {relative_path}")

    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", relative_path],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    if tracked.returncode != 0:
        raise RuntimeError(
            f"formal collection requires Git-tracked file: {relative_path}"
        )

    head_blob = subprocess.run(
        ["git", "show", f"HEAD:{relative_path}"],
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    if head_blob.returncode != 0:
        raise RuntimeError(
            f"cannot read HEAD version of {relative_path}"
        )

    worktree_bytes = worktree_path.read_bytes()
    head_bytes = head_blob.stdout

    worktree_sha256 = hashlib.sha256(worktree_bytes).hexdigest()
    head_sha256 = hashlib.sha256(head_bytes).hexdigest()

    if worktree_bytes != head_bytes:
        raise RuntimeError(
            f"formal collection code differs from HEAD: {relative_path}; "
            "commit the exact collector before collecting formal data"
        )

    return {
        "path": relative_path,
        "sha256": worktree_sha256,
        "head_sha256": head_sha256,
        "matches_head": True,
    }


def load_registry(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def teacher_health(service_url: str) -> dict[str, Any]:
    with urllib.request.urlopen(service_url.rstrip("/") + "/health", timeout=10) as r:
        data = json.loads(r.read().decode("utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("Teacher health payload is not an object")

    checks = {
        "status": data.get("status") == "READY",
        "production_ready": data.get("production_ready") is True,
        "model_id": data.get("model_id") == EXPECTED_MODEL_ID,
        "qwen_mode": data.get("qwen_mode") == "planner_v2",
    }
    for key, ok in checks.items():
        print(f"TEACHER_{key.upper()}={'PASS' if ok else 'FAIL'}")
    if not all(checks.values()):
        raise RuntimeError("Pinned Teacher health/identity gate failed")
    return data


def load_teacher_manifest(repo: Path) -> dict[str, Any]:
    path = repo / "challenge" / "teacher_baseline_manifest.json"
    data = read_json(path)

    expected = {
        "git_sha": EXPECTED_BASELINE_GIT_SHA,
        "model_id": EXPECTED_MODEL_ID,
        "model_revision": EXPECTED_MODEL_REVISION,
        "artifact_fingerprint_sha256": EXPECTED_ARTIFACT_SHA256,
    }
    bad = {
        k: {"expected": v, "actual": data.get(k)}
        for k, v in expected.items()
        if data.get(k) != v
    }
    if bad:
        raise RuntimeError(
            "teacher_baseline_manifest.json does not match pinned Teacher: "
            + json.dumps(bad, ensure_ascii=False)
        )
    print("TEACHER_MANIFEST_GATE=PASS")
    return data


def runner_preflight(runner_python: str, repo: Path) -> dict[str, str]:
    code = (
        "import sys, carla; "
        "print(sys.executable); "
        "print(carla.__file__)"
    )
    result = subprocess.run(
        [runner_python, "-c", code],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Configured runner Python cannot import CARLA:\n" + result.stderr
        )
    lines = [x.strip() for x in result.stdout.splitlines() if x.strip()]
    if len(lines) < 2:
        raise RuntimeError("Runner Python preflight returned unexpected output")
    print("RUNNER_PYTHON=" + lines[0])
    print("CARLA_MODULE=" + lines[1])
    print("CARLA_IMPORT=PASS")
    return {"python": lines[0], "carla_module": lines[1]}


def carla_port_preflight(host: str, port: int) -> None:
    import socket
    with socket.create_connection((host, port), timeout=3):
        pass
    print("CARLA_PORT=PASS")


def sort_key(row: dict[str, str]) -> tuple[int, int, str]:
    p = row.get("scenario_path", "").lower()
    priority = int(any(
        token in p
        for token in (
            "/complex/", "/advanced/", "/challenge/",
            "pedestrian", "brake", "red_light", "obstacle",
            "avoid", "lane_change", "multi_target", "route_deviation",
        )
    ))
    variant = int(row.get("source_bucket", "").upper() == "VARIANT")
    return (-priority, -variant, row.get("scenario_path", ""))


def build_positive_plan(registry: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = [
        row for row in registry
        if row.get("policy_class") == "TRAIN_POSITIVE"
    ]
    rows.sort(key=sort_key)
    return rows


def write_plan(plan: list[dict[str, str]], out_dir: Path) -> None:
    write_json(out_dir / "d1_collection_plan.json", plan)
    if plan:
        with (out_dir / "d1_collection_plan.csv").open(
            "w", encoding="utf-8-sig", newline=""
        ) as f:
            writer = csv.DictWriter(f, fieldnames=list(plan[0].keys()))
            writer.writeheader()
            writer.writerows(plan)


def load_run_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"schema_version": "1.0", "runs": {}}
    state = read_json(path)
    if not isinstance(state.get("runs"), dict):
        raise RuntimeError("run_state.json has invalid runs object")
    return state


def save_run_state(path: Path, state: dict[str, Any]) -> None:
    write_json(path, state)


def log_files_for_scenario(log_dir: Path, scenario_id: str) -> list[str]:
    return sorted(str(p) for p in log_dir.glob(f"{scenario_id}_*.jsonl"))


def run_scenario(
    *,
    repo: Path,
    runner_python: str,
    scenario_path: str,
    service_url: str,
    log_dir: Path,
    image_prefix: str,
    host: str,
    port: int,
    timeout_ms: int,
) -> int:
    cmd = [
        runner_python,
        "-m", "integration.carla_runner",
        "--host", host,
        "--port", str(port),
        "--scenario-file", scenario_path,
        "--qwen-service-url", service_url,
        "--qwen-mode", "planner_v2",
        "--qwen-timeout-ms", str(timeout_ms),
        "--qwen-queue-size", "1",
        "--qwen-image-root", str(repo),
        "--qwen-image-prefix", image_prefix,
        "--log-dir", str(log_dir),
    ]
    print()
    print("=" * 78)
    print("RUN_SCENARIO=" + scenario_path)
    print("=" * 78)
    return subprocess.run(cmd, cwd=repo, check=False).returncode


def collect_from_logs(
    *,
    repo: Path,
    python: str,
    log_dir: Path,
    dataset_dir: Path,
) -> tuple[int, int]:
    logs = sorted(log_dir.glob("*.jsonl"))
    accepted = dataset_dir / "d1_valid_raw.jsonl"
    rejected = dataset_dir / "d1_rejected_raw.jsonl"
    if not logs:
        return 0, 0

    cmd = [
        python,
        "challenge/dataset/collector.py",
        "--repo-root", str(repo),
    ]
    for log in logs:
        cmd += ["--input-log", str(log)]
    cmd += [
        "--output", str(accepted),
        "--rejected-output", str(rejected),
        "--dataset-version", DATASET_VERSION,
    ]
    rc = subprocess.run(cmd, cwd=repo, check=False).returncode
    if rc != 0:
        raise RuntimeError("collector.py failed")
    return count_jsonl(accepted), count_jsonl(rejected)


def referenced_target_ids(plan: dict[str, Any]) -> list[str]:
    result: list[str] = []
    for step in plan.get("steps") or []:
        if not isinstance(step, dict):
            continue
        target = step.get("target")
        if not isinstance(target, dict):
            continue
        tid = target.get("target_id")
        if isinstance(tid, str) and tid:
            result.append(tid)
    return result


def primary_sample_class(sample: dict[str, Any]) -> str:
    sc = sample.get("sample_class")
    if isinstance(sc, dict):
        value = sc.get("primary")
    else:
        value = sc
    normalized = str(value or "NORMAL").strip().lower()
    if normalized not in {"normal", "complex", "safety_critical"}:
        raise ValueError(f"unsupported sample_class: {value!r}")
    return normalized


def enrich_canonical(
    sample: dict[str, Any],
    *,
    collection_head: str,
    teacher_manifest: dict[str, Any],
    registry_by_scenario: dict[str, dict[str, str]],
) -> dict[str, Any]:
    out = json.loads(json.dumps(sample))
    meta = out.setdefault("metadata", {})

    # Preserve the pre-existing ambiguous field for compatibility but add
    # explicit provenance fields with unambiguous semantics.
    old_teacher_git_sha = meta.get("teacher_git_sha")
    if old_teacher_git_sha and old_teacher_git_sha != EXPECTED_BASELINE_GIT_SHA:
        meta.setdefault("legacy_collector_teacher_git_sha", old_teacher_git_sha)

    meta["teacher_baseline_git_sha"] = EXPECTED_BASELINE_GIT_SHA
    meta["collection_repo_git_sha"] = collection_head
    meta["teacher_model_id"] = EXPECTED_MODEL_ID
    meta["teacher_model_revision"] = EXPECTED_MODEL_REVISION
    meta["teacher_model_artifact_sha256"] = EXPECTED_ARTIFACT_SHA256
    meta["teacher_profile"] = TEACHER_PROFILE
    meta["dataset_version"] = DATASET_VERSION
    meta["sample_class"] = primary_sample_class(out)

    scenario_id = str(meta.get("scenario_id") or "")
    registry_row = registry_by_scenario.get(scenario_id)

    if registry_row is None:
        raise RuntimeError(
            f"sample scenario_id is absent from registry: {scenario_id!r}"
        )

    source_bucket = str(
        registry_row.get("source_bucket") or ""
    ).upper()

    if source_bucket not in {"SEEN", "VARIANT", "UNSEEN"}:
        raise RuntimeError(
            f"invalid source_bucket for {scenario_id}: {source_bucket!r}"
        )

    registry_scenario_path = str(
        registry_row.get("scenario_path") or ""
    )

    if not registry_scenario_path:
        raise RuntimeError(
            f"registry scenario_path missing for {scenario_id}"
        )

    if registry_scenario_path.startswith("scenarios/"):
        canonical_scenario_path = registry_scenario_path
    else:
        canonical_scenario_path = "scenarios/" + registry_scenario_path

    meta["source_bucket"] = source_bucket
    meta["policy_class"] = str(
        registry_row.get("policy_class") or ""
    )
    meta["scenario_config_path"] = canonical_scenario_path

    runtime = out.setdefault("teacher_runtime", {})
    if isinstance(runtime, dict):
        runtime["teacher_baseline_git_sha"] = EXPECTED_BASELINE_GIT_SHA
        runtime["collection_repo_git_sha"] = collection_head
        runtime["model_id"] = EXPECTED_MODEL_ID
        runtime["model_revision"] = EXPECTED_MODEL_REVISION
        runtime["model_artifact_sha256"] = EXPECTED_ARTIFACT_SHA256
        runtime["teacher_profile"] = TEACHER_PROFILE
        runtime["qwen_mode"] = "planner_v2"

    return out


def student_view_or_reason(
    sample: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    request = sample.get("model_request")
    plan = sample.get("teacher_plan")
    if not isinstance(request, dict):
        return None, "MODEL_REQUEST_MISSING"
    if not isinstance(plan, dict):
        return None, "MANEUVER_PLAN_MISSING"

    raw_targets = request.get("targets")
    if not isinstance(raw_targets, list):
        raw_targets = []

    ids: list[str] = []
    for target in raw_targets:
        if not isinstance(target, dict):
            continue
        tid = target.get("target_id")
        if isinstance(tid, str):
            ids.append(tid)

    positions = {tid: idx for idx, tid in enumerate(ids)}
    refs = referenced_target_ids(plan)

    missing = [tid for tid in refs if tid not in positions]
    if missing:
        return None, "TEACHER_TARGET_ABSENT_RAW_REQUEST"

    outside = [tid for tid in refs if positions[tid] >= MAX_TARGETS]
    if outside:
        return None, "TARGET_OUTSIDE_TOPK"

    adapted_request = json.loads(json.dumps(request))
    adapted_request["targets"] = raw_targets[:MAX_TARGETS]

    meta = dict(sample.get("metadata") or {})
    meta["sample_class"] = primary_sample_class(sample)
    meta["student_contract"] = "student_v0_r3"
    meta["student_max_targets"] = MAX_TARGETS
    meta["student_no_target_index"] = NO_TARGET_INDEX
    meta["raw_target_count"] = len(raw_targets)
    meta["student_target_count"] = len(adapted_request["targets"])

    view = {
        "sample_id": sample.get("sample_id"),
        "input": adapted_request,
        "teacher": {"maneuver_plan": plan},
        "visual_input": sample.get("visual_input"),
        "quality": sample.get("quality"),
        "closed_loop_quality": sample.get("closed_loop_quality"),
        "sample_class": sample.get("sample_class"),
        "metadata": meta,
    }
    return view, None


def rebuild_outputs(
    *,
    raw_path: Path,
    dataset_dir: Path,
    collection_head: str,
    teacher_manifest: dict[str, Any],
    registry_by_scenario: dict[str, dict[str, str]],
) -> dict[str, int]:
    canonical_rows: list[dict[str, Any]] = []
    student_rows: list[dict[str, Any]] = []
    quarantine_rows: list[dict[str, Any]] = []

    reasons: Counter[str] = Counter()

    for raw in read_jsonl(raw_path):
        sample = enrich_canonical(
            raw,
            collection_head=collection_head,
            teacher_manifest=teacher_manifest,
            registry_by_scenario=registry_by_scenario,
        )
        canonical_rows.append(sample)

        view, reason = student_view_or_reason(sample)
        if reason is None:
            assert view is not None
            student_rows.append(view)
        else:
            reasons[reason] += 1
            quarantine_rows.append({
                "sample_id": sample.get("sample_id"),
                "reason": reason,
                "canonical_sample": sample,
            })

    write_jsonl(dataset_dir / "d1_valid.jsonl", canonical_rows)
    write_jsonl(dataset_dir / "d1_student_eligible.jsonl", student_rows)
    write_jsonl(dataset_dir / "d1_quarantine.jsonl", quarantine_rows)

    stats = {
        "canonical_valid": len(canonical_rows),
        "student_eligible": len(student_rows),
        "quarantined": len(quarantine_rows),
    }
    write_json(
        dataset_dir / "student_contract_report.json",
        {
            **stats,
            "max_targets": MAX_TARGETS,
            "no_target_index": NO_TARGET_INDEX,
            "quarantine_reasons": dict(sorted(reasons.items())),
            "policy": {
                "canonical_raw_targets": "PRESERVED_LOSSLESS",
                "student_view_targets": "FIRST_8_IN_ORIGINAL_ORDER",
                "target_outside_top8": "QUARANTINE_NOT_NO_TARGET",
                "target_absent_raw_request": "QUARANTINE",
            },
        },
    )
    return stats


def validate_canonical(repo: Path, python: str, path: Path) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        return
    rc = subprocess.run(
        [python, "challenge/dataset/validate_dataset.py", str(path)],
        cwd=repo,
        check=False,
    ).returncode
    if rc != 0:
        raise RuntimeError("validate_dataset.py failed")
    print("CANONICAL_VALIDATION=PASS")


def capture_provenance(
    *,
    repo: Path,
    out_path: Path,
    health: dict[str, Any],
    teacher_manifest: dict[str, Any],
    runner_info: dict[str, str],
    service_url: str,
    registry_path: Path,
    collector_identity: dict[str, Any] | None,
    config_id: str,
    formal_code_gate: bool,
) -> None:
    head = current_head(repo)
    payload = {
        "schema_version": "1.0",
        "dataset_version": DATASET_VERSION,
        "teacher_profile": TEACHER_PROFILE,
        "teacher_baseline_git_sha": EXPECTED_BASELINE_GIT_SHA,
        "collection_repo_git_sha": head,
        "collection_branch": current_branch(repo),
        "teacher_model_id": EXPECTED_MODEL_ID,
        "teacher_model_revision": EXPECTED_MODEL_REVISION,
        "teacher_model_artifact_sha256": EXPECTED_ARTIFACT_SHA256,
        "teacher_mode": "planner_v2",
        "teacher_service_url": service_url,
        "teacher_health_snapshot": health,
        "teacher_manifest_snapshot": teacher_manifest,
        "runner": runner_info,
        "registry_path": str(registry_path),
        "registry_sha256": sha256_file(registry_path),
        "collector_identity": collector_identity,
        "formal_code_gate": formal_code_gate,
        "config_id": config_id,
        "student_contract": {
            "name": "student_v0_r3",
            "max_steps": 4,
            "max_targets": MAX_TARGETS,
            "no_target_index": NO_TARGET_INDEX,
        },
        "legacy_data_policy": (
            "Legacy unpinned D1/Smoke artifacts are excluded from this formal "
            "pinned dataset and are not counted toward its target."
        ),
    }
    write_json(out_path, payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--registry",
        default="artifacts/b1_d1_registry_v3/scenario_registry_v3.csv",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/b1_d1_pinned",
    )
    parser.add_argument(
        "--target-valid",
        type=int,
        default=DEFAULT_TARGET_VALID,
    )
    parser.add_argument(
        "--qwen-service-url",
        default="http://127.0.0.1:18004",
    )
    parser.add_argument(
        "--runner-python",
        default="/home/dcase_task2/miniconda3/envs/voice/bin/python",
    )
    parser.add_argument("--carla-host", default="127.0.0.1")
    parser.add_argument("--carla-port", type=int, default=2000)
    parser.add_argument("--qwen-timeout-ms", type=int, default=5000)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--allow-uncommitted-code",
        action="store_true",
        help=(
            "Development/testing only. Formal B1 collection must omit this "
            "flag so the exact collector must match Git HEAD."
        ),
    )
    parser.add_argument(
        "--max-scenarios",
        type=int,
        default=None,
        help="Run at most N not-yet-completed scenario runs (for staged validation).",
    )
    args = parser.parse_args()

    if args.target_valid < 1:
        raise SystemExit("--target-valid must be >=1")
    if args.max_scenarios is not None and args.max_scenarios < 1:
        raise SystemExit("--max-scenarios must be >=1")

    repo = Path(__file__).resolve().parents[2]
    registry_path = (repo / args.registry).resolve()
    out = (repo / args.output_dir).resolve()
    logs = out / "logs"
    images = out / "qwen_images"
    dataset = out / "dataset"
    plan_dir = out / "plan"
    for d in (logs, images, dataset, plan_dir):
        d.mkdir(parents=True, exist_ok=True)

    print("DATASET_VERSION=" + DATASET_VERSION)
    print("TEACHER_PROFILE=" + TEACHER_PROFILE)
    print("REPO_HEAD=" + current_head(repo))
    print("REPO_BRANCH=" + current_branch(repo))

    teacher_manifest = load_teacher_manifest(repo)
    health = teacher_health(args.qwen_service_url)
    runner_info = runner_preflight(args.runner_python, repo)
    carla_port_preflight(args.carla_host, args.carla_port)

    collector_relpath = "challenge/dataset/collect_d1_200.py"

    if args.allow_uncommitted_code:
        collector_path = repo / collector_relpath
        collector_identity = {
            "path": collector_relpath,
            "sha256": sha256_file(collector_path),
            "matches_head": None,
            "development_override": True,
        }
        formal_code_gate = False
        print("FORMAL_CODE_GATE=BYPASSED_FOR_DEVELOPMENT")
    else:
        collector_identity = verify_tracked_file_matches_head(
            repo,
            collector_relpath,
        )
        formal_code_gate = True
        print("FORMAL_CODE_GATE=PASS")

    config_payload = {
        "dataset_version": DATASET_VERSION,
        "teacher_profile": TEACHER_PROFILE,
        "teacher_model_revision": EXPECTED_MODEL_REVISION,
        "teacher_model_artifact_sha256": EXPECTED_ARTIFACT_SHA256,
        "registry_sha256": sha256_file(registry_path),
        "qwen_mode": "planner_v2",
        "qwen_timeout_ms": args.qwen_timeout_ms,
        "qwen_queue_size": 1,
        "student_max_steps": 4,
        "student_max_targets": MAX_TARGETS,
        "student_no_target_index": NO_TARGET_INDEX,
    }
    config_id = canonical_json_sha256(config_payload)[:20]

    print("COLLECTOR_SHA256=" + collector_identity["sha256"])
    print("REGISTRY_SHA256=" + sha256_file(registry_path))
    print("CONFIG_ID=" + config_id)

    capture_provenance(
        repo=repo,
        out_path=out / "provenance_manifest.json",
        health=health,
        teacher_manifest=teacher_manifest,
        runner_info=runner_info,
        service_url=args.qwen_service_url,
        registry_path=registry_path,
        collector_identity=collector_identity,
        config_id=config_id,
        formal_code_gate=formal_code_gate,
    )

    registry = load_registry(registry_path)

    registry_by_scenario: dict[str, dict[str, str]] = {}
    for row in registry:
        scenario_id = str(row.get("scenario_id") or "")
        if not scenario_id:
            continue
        if scenario_id in registry_by_scenario:
            raise RuntimeError(
                f"duplicate scenario_id in registry: {scenario_id}"
            )
        registry_by_scenario[scenario_id] = row

    plan = build_positive_plan(registry)
    write_plan(plan, plan_dir)

    declared_commands = sum(
        int(row.get("command_count") or 0)
        for row in plan
    )
    print("TRAIN_POSITIVE_SCENARIOS=" + str(len(plan)))
    print("TRAIN_POSITIVE_DECLARED_COMMANDS=" + str(declared_commands))
    print("TARGET_VALID=" + str(args.target_valid))

    if args.target_valid > declared_commands:
        print(
            "TARGET_CAPACITY_WARNING=target exceeds declared commands in the "
            "current TRAIN_POSITIVE registry; additional distinct collection "
            "policy/expansion may be required."
        )

    if args.dry_run:
        print("D1_PINNED_DRY_RUN=PASS")
        return 0

    state_path = out / "run_state.json"
    state = load_run_state(state_path)
    state["dataset_version"] = DATASET_VERSION
    state["collection_repo_git_sha"] = current_head(repo)
    state["teacher_model_revision"] = EXPECTED_MODEL_REVISION
    state["teacher_model_artifact_sha256"] = EXPECTED_ARTIFACT_SHA256

    raw_valid_path = dataset / "d1_valid_raw.jsonl"
    accepted, rejected = collect_from_logs(
        repo=repo,
        python=args.runner_python,
        log_dir=logs,
        dataset_dir=dataset,
    )
    if raw_valid_path.is_file():
        stats = rebuild_outputs(
            raw_path=raw_valid_path,
            dataset_dir=dataset,
            collection_head=current_head(repo),
            teacher_manifest=teacher_manifest,
            registry_by_scenario=registry_by_scenario,
        )
    else:
        stats = {"canonical_valid": 0, "student_eligible": 0, "quarantined": 0}

    print("INITIAL_CANONICAL_VALID=" + str(stats["canonical_valid"]))
    print("INITIAL_STUDENT_ELIGIBLE=" + str(stats["student_eligible"]))
    print("INITIAL_REJECTED=" + str(rejected))

    launched = 0
    process_failures: list[str] = []

    for row in plan:
        if stats["canonical_valid"] >= args.target_valid:
            break
        if args.max_scenarios is not None and launched >= args.max_scenarios:
            break

        scenario_path = row.get("scenario_path", "")
        scenario_id = row.get("scenario_id", "")
        if not scenario_path or not scenario_id:
            raise RuntimeError("registry TRAIN_POSITIVE row missing scenario path/id")

        scenario_file = Path(scenario_path)
        if not scenario_file.is_absolute():
            direct = repo / scenario_file
            under_scenarios = repo / "scenarios" / scenario_file

            if direct.is_file():
                scenario_file = direct
            elif under_scenarios.is_file():
                scenario_file = under_scenarios
            else:
                raise FileNotFoundError(
                    f"scenario file not found: {scenario_path}; "
                    f"checked {direct} and {under_scenarios}"
                )

        scenario_path_for_runner = str(scenario_file.relative_to(repo))

        # Resume is run-level, keyed by exact scenario path. A scenario is marked
        # completed only after the runner process itself has finished. We do not
        # skip merely because one accepted sample with the same scenario_id exists.
        run_entry = state["runs"].get(scenario_path)
        if (
            isinstance(run_entry, dict)
            and run_entry.get("status") == "COMPLETED"
            and run_entry.get("returncode") == 0
            and run_entry.get("log_files")
        ):
            print("SKIP_COMPLETED_RUN=" + scenario_path)
            continue

        before = set(log_files_for_scenario(logs, scenario_id))
        started_at = time.time()
        rc = run_scenario(
            repo=repo,
            runner_python=args.runner_python,
            scenario_path=scenario_path_for_runner,
            service_url=args.qwen_service_url,
            log_dir=logs,
            image_prefix=str(images.relative_to(repo)),
            host=args.carla_host,
            port=args.carla_port,
            timeout_ms=args.qwen_timeout_ms,
        )
        launched += 1

        after = set(log_files_for_scenario(logs, scenario_id))
        new_logs = sorted(after - before)

        state["runs"][scenario_path] = {
            "scenario_id": scenario_id,
            "status": "COMPLETED" if rc == 0 else "FAILED",
            "returncode": rc,
            "started_unix_s": started_at,
            "finished_unix_s": time.time(),
            "log_files": new_logs or sorted(after),
            "declared_command_count": int(row.get("command_count") or 0),
            "source_bucket": row.get("source_bucket"),
            "policy_class": row.get("policy_class"),
        }
        save_run_state(state_path, state)

        if rc != 0:
            process_failures.append(scenario_path)
            print("SCENARIO_PROCESS_FAILED=" + scenario_path)

        accepted, rejected = collect_from_logs(
            repo=repo,
            python=args.runner_python,
            log_dir=logs,
            dataset_dir=dataset,
        )
        stats = rebuild_outputs(
            raw_path=raw_valid_path,
            dataset_dir=dataset,
            collection_head=current_head(repo),
            teacher_manifest=teacher_manifest,
            registry_by_scenario=registry_by_scenario,
        )

        print("CURRENT_CANONICAL_VALID=" + str(stats["canonical_valid"]))
        print("CURRENT_STUDENT_ELIGIBLE=" + str(stats["student_eligible"]))
        print("CURRENT_QUARANTINED=" + str(stats["quarantined"]))
        print("CURRENT_REJECTED=" + str(rejected))
        time.sleep(0.25)

    final_valid = dataset / "d1_valid.jsonl"
    validate_canonical(repo, args.runner_python, final_valid)

    summary = {
        "dataset_version": DATASET_VERSION,
        "teacher_profile": TEACHER_PROFILE,
        "teacher_model_revision": EXPECTED_MODEL_REVISION,
        "teacher_model_artifact_sha256": EXPECTED_ARTIFACT_SHA256,
        "collection_repo_git_sha": current_head(repo),
        "target_valid": args.target_valid,
        "train_positive_scenarios_in_plan": len(plan),
        "train_positive_declared_commands": declared_commands,
        "scenario_runs_launched_this_invocation": launched,
        "canonical_valid": stats["canonical_valid"],
        "student_eligible": stats["student_eligible"],
        "quarantined": stats["quarantined"],
        "collector_rejected": rejected,
        "process_failures": process_failures,
        "target_reached": stats["canonical_valid"] >= args.target_valid,
        "status": (
            "TARGET_REACHED"
            if stats["canonical_valid"] >= args.target_valid
            else "NEEDS_EXTENSION"
        ),
    }
    write_json(out / "d1_summary.json", summary)

    print()
    print("=" * 78)
    print("B1 D1 PINNED SUMMARY")
    print("=" * 78)
    for key, value in summary.items():
        if key == "process_failures":
            continue
        print(f"{key.upper()}={value}")
    for item in process_failures:
        print("FAILED_SCENARIO=" + item)

    return 0 if not process_failures else 3


if __name__ == "__main__":
    raise SystemExit(main())
