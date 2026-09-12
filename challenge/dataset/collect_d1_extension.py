#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, subprocess, time
from pathlib import Path

from challenge.dataset import collect_d1_200 as base

EXTENSION_DATASET_VERSION = "teacher_distill_v0.2_d1_pinned_extension"
EXTENSION_TYPE = "SEED_VARIANT"
ALLOWED_BUCKETS = {"SEEN", "VARIANT"}
ALLOWED_POLICY = "TRAIN_POSITIVE"

def canonical_json_sha256(value) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def verify_plan(path: Path):
    plan = base.read_json(path)
    expected = plan.get("plan_canonical_sha256")
    body = dict(plan)
    body.pop("plan_canonical_sha256", None)
    actual = canonical_json_sha256(body)
    if expected != actual:
        raise RuntimeError(f"plan hash mismatch expected={expected} actual={actual}")
    rows = plan.get("plan")
    if not isinstance(rows, list):
        raise RuntimeError("plan list missing")
    seen = set()
    for r in rows:
        eid = str(r.get("extension_id") or "")
        if not eid or eid in seen:
            raise RuntimeError(f"bad extension_id {eid!r}")
        seen.add(eid)
        if r.get("extension_type") != EXTENSION_TYPE:
            raise RuntimeError(f"unsupported extension_type: {eid}")
        if r.get("policy_class") != ALLOWED_POLICY:
            raise RuntimeError(f"protected policy leaked: {eid}")
        if str(r.get("source_bucket") or "").upper() not in ALLOWED_BUCKETS:
            raise RuntimeError(f"protected source bucket leaked: {eid}")
    return plan

def run_seed_variant(repo: Path, runner_python: str, scenario_path: str, seed: int,
                     service_url: str, log_dir: Path, image_prefix: str,
                     host: str, port: int, timeout_ms: int) -> int:
    cmd = [
        runner_python, "-m", "integration.carla_runner",
        "--host", host, "--port", str(port),
        "--scenario-file", scenario_path,
        "--seed", str(seed),
        "--qwen-service-url", service_url,
        "--qwen-mode", "planner_v2",
        "--qwen-timeout-ms", str(timeout_ms),
        "--qwen-queue-size", "1",
        "--qwen-image-root", str(repo),
        "--qwen-image-prefix", image_prefix,
        "--log-dir", str(log_dir),
    ]
    print("=" * 78)
    print(f"RUN_EXTENSION={scenario_path} seed={seed}")
    print("=" * 78)
    return subprocess.run(cmd, cwd=repo, check=False).returncode

def collect_one_log(repo: Path, runner_python: str, log_path: Path, tmp_dir: Path, eid: str):
    accepted = tmp_dir / f"{eid}.accepted.jsonl"
    rejected = tmp_dir / f"{eid}.rejected.jsonl"
    rc = subprocess.run([
        runner_python, "challenge/dataset/collector.py",
        "--repo-root", str(repo),
        "--input-log", str(log_path),
        "--output", str(accepted),
        "--rejected-output", str(rejected),
        "--dataset-version", EXTENSION_DATASET_VERSION,
    ], cwd=repo, check=False).returncode
    if rc != 0:
        raise RuntimeError(f"collector.py failed for {eid}")
    return base.read_jsonl(accepted), base.read_jsonl(rejected)

def append_jsonl(path: Path, rows):
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default="artifacts/b1_d1_extension_plan/d1_extension_plan_formal.json")
    ap.add_argument("--registry", default="artifacts/b1_d1_registry_final/scenario_registry_v3.csv")
    ap.add_argument("--base-dataset", default="artifacts/b1_d1_pinned_formal/dataset/d1_valid.jsonl")
    ap.add_argument("--base-provenance", default="artifacts/b1_d1_pinned_formal/provenance_manifest.json")
    ap.add_argument("--teacher-artifact-manifest", default="artifacts/b1_teacher_pinned/teacher_model_manifest_latest.json")
    ap.add_argument("--output-dir", default="artifacts/b1_d1_extension_formal")
    ap.add_argument("--qwen-service-url", default="http://127.0.0.1:18004")
    ap.add_argument("--runner-python", default="/home/dcase_task2/miniconda3/envs/voice/bin/python")
    ap.add_argument("--carla-host", default="127.0.0.1")
    ap.add_argument("--carla-port", type=int, default=2000)
    ap.add_argument("--qwen-timeout-ms", type=int, default=5000)
    ap.add_argument("--max-runs", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-uncommitted-code", action="store_true")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[2]
    plan_path = (repo / args.plan).resolve()
    registry_path = (repo / args.registry).resolve()
    base_ds = (repo / args.base_dataset).resolve()
    base_prov_path = (repo / args.base_provenance).resolve()
    artifact_manifest = (repo / args.teacher_artifact_manifest).resolve()
    out = (repo / args.output_dir).resolve()

    for p in [plan_path, registry_path, base_ds, base_prov_path, artifact_manifest]:
        if not p.is_file():
            raise RuntimeError(f"required file missing: {p}")

    plan = verify_plan(plan_path)
    base_rows = base.read_jsonl(base_ds)
    base_prov = base.read_json(base_prov_path)

    if base_prov.get("formal_code_gate") is not True:
        raise RuntimeError("base provenance is not formal")
    if len(base_rows) != int(plan.get("base_dataset_count") or -1):
        raise RuntimeError("base dataset count differs from plan")
    if base.sha256_file(base_ds) != plan.get("base_dataset_file_sha256"):
        raise RuntimeError("base dataset SHA differs from plan")
    if base_prov.get("collection_repo_git_sha") != plan.get("base_collection_repo_git_sha"):
        raise RuntimeError("base git SHA differs from plan")
    if base_prov.get("config_id") != plan.get("base_config_id"):
        raise RuntimeError("base config ID differs from plan")

    teacher_manifest = base.load_teacher_manifest(repo)
    teacher_artifact_evidence = base.load_model_artifact_manifest(artifact_manifest)
    health = base.teacher_health(args.qwen_service_url)
    runner = base.runner_preflight(args.runner_python, repo)
    base.carla_port_preflight(args.carla_host, args.carla_port)

    rel = "challenge/dataset/collect_d1_extension.py"
    if args.allow_uncommitted_code:
        collector_identity = {
            "path": rel,
            "sha256": base.sha256_file(repo / rel),
            "matches_head": None,
            "development_override": True,
        }
        formal_gate = False
        print("FORMAL_CODE_GATE=BYPASSED_FOR_DEVELOPMENT")
    else:
        collector_identity = base.verify_tracked_file_matches_head(repo, rel)
        formal_gate = True
        print("FORMAL_CODE_GATE=PASS")

    registry = base.load_registry(registry_path)
    registry_by_scenario = {
        str(r.get("scenario_id") or ""): r
        for r in registry if r.get("scenario_id")
    }

    config_payload = {
        "extension_dataset_version": EXTENSION_DATASET_VERSION,
        "extension_type": EXTENSION_TYPE,
        "collection_repo_git_sha": base.current_head(repo),
        "plan_canonical_sha256": plan["plan_canonical_sha256"],
        "plan_file_sha256": base.sha256_file(plan_path),
        "base_collection_repo_git_sha": base_prov["collection_repo_git_sha"],
        "base_config_id": base_prov["config_id"],
        "teacher_revision": base.EXPECTED_MODEL_REVISION,
        "teacher_artifact_sha256": base.EXPECTED_ARTIFACT_SHA256,
        "registry_sha256": base.sha256_file(registry_path),
        "qwen_timeout_ms": args.qwen_timeout_ms,
    }
    ext_config_id = canonical_json_sha256(config_payload)[:20]

    out.mkdir(parents=True, exist_ok=True)
    logs, images, tmp, ds = out/"logs", out/"qwen_images", out/"tmp", out/"dataset"
    for d in [logs, images, tmp, ds]:
        d.mkdir(parents=True, exist_ok=True)

    provenance = {
        "schema_version": "1.0",
        "dataset_version": EXTENSION_DATASET_VERSION,
        "extension_type": EXTENSION_TYPE,
        "collection_repo_git_sha": base.current_head(repo),
        "collection_branch": base.current_branch(repo),
        "collector_identity": collector_identity,
        "formal_code_gate": formal_gate,
        "extension_config_id": ext_config_id,
        "plan_path": str(plan_path.relative_to(repo)),
        "plan_canonical_sha256": plan["plan_canonical_sha256"],
        "plan_file_sha256": base.sha256_file(plan_path),
        "base_dataset_path": str(base_ds.relative_to(repo)),
        "base_dataset_file_sha256": base.sha256_file(base_ds),
        "base_dataset_count": len(base_rows),
        "base_collection_repo_git_sha": base_prov["collection_repo_git_sha"],
        "base_config_id": base_prov["config_id"],
        "registry_path": str(registry_path.relative_to(repo)),
        "registry_sha256": base.sha256_file(registry_path),
        "teacher_baseline_git_sha": base.EXPECTED_BASELINE_GIT_SHA,
        "teacher_model_id": base.EXPECTED_MODEL_ID,
        "teacher_model_revision": base.EXPECTED_MODEL_REVISION,
        "teacher_model_artifact_sha256": base.EXPECTED_ARTIFACT_SHA256,
        "teacher_health_snapshot": health,
        "teacher_manifest_snapshot": teacher_manifest,
        "teacher_artifact_evidence": teacher_artifact_evidence,
        "runner": runner,
        "protected_unseen_policy": "RESERVED_TEST_CANDIDATE excluded from extension",
    }
    base.write_json(out / "provenance_manifest.json", provenance)

    print("REPO_HEAD=" + base.current_head(repo))
    print("PLAN_CANONICAL_SHA256=" + plan["plan_canonical_sha256"])
    print("PLAN_FILE_SHA256=" + base.sha256_file(plan_path))
    print("COLLECTOR_SHA256=" + collector_identity["sha256"])
    print("EXTENSION_CONFIG_ID=" + ext_config_id)
    print("BASE_COUNT=" + str(len(base_rows)))
    print("PLANNED_RUNS=" + str(len(plan["plan"])))
    print("TARGET_TOTAL=" + str(plan["target_total"]))

    if args.dry_run:
        print("B1_D1_EXTENSION_DRY_RUN=PASS")
        return 0

    state_path = out / "run_state.json"
    state = base.load_run_state(state_path)
    state["dataset_version"] = EXTENSION_DATASET_VERSION
    state["collection_repo_git_sha"] = base.current_head(repo)
    state["extension_config_id"] = ext_config_id

    canonical_path = ds / "extension_valid.jsonl"
    student_path = ds / "extension_student_eligible.jsonl"
    quarantine_path = ds / "extension_quarantine.jsonl"
    rejected_path = ds / "extension_rejected.jsonl"

    ext_valid = len(base.read_jsonl(canonical_path))
    launched = 0

    for item in plan["plan"]:
        if len(base_rows) + ext_valid >= int(plan["target_total"]):
            break
        if args.max_runs is not None and launched >= args.max_runs:
            break

        eid = item["extension_id"]
        prior = state["runs"].get(eid)
        if isinstance(prior, dict) and prior.get("status") == "COMPLETED":
            print("SKIP_COMPLETED_EXTENSION=" + eid)
            continue

        scenario_path = str(item["scenario_path"])
        scenario_file = repo / scenario_path
        if not scenario_file.is_file():
            scenario_file = repo / "scenarios" / scenario_path
        if not scenario_file.is_file():
            raise RuntimeError(f"scenario not found: {scenario_path}")
        runner_path = str(scenario_file.relative_to(repo))

        sid = str(item["scenario_id"])
        before = set(logs.glob(f"{sid}_*.jsonl"))
        started = time.time()
        rc = run_seed_variant(
            repo, args.runner_python, runner_path, int(item["extension_seed"]),
            args.qwen_service_url, logs, str(images.relative_to(repo)),
            args.carla_host, args.carla_port, args.qwen_timeout_ms
        )
        launched += 1
        after = set(logs.glob(f"{sid}_*.jsonl"))
        created = sorted(after - before, key=lambda p: p.stat().st_mtime_ns)
        log_path = created[-1] if created else None

        state["runs"][eid] = {
            "extension_id": eid,
            "scenario_id": sid,
            "scenario_path": runner_path,
            "extension_type": EXTENSION_TYPE,
            "base_seed": int(item["base_seed"]),
            "extension_seed": int(item["extension_seed"]),
            "source_bucket": item["source_bucket"],
            "policy_class": item["policy_class"],
            "returncode": rc,
            "status": "COMPLETED" if rc == 0 and log_path else "FAILED",
            "log_file": str(log_path) if log_path else None,
            "started_unix_s": started,
            "finished_unix_s": time.time(),
        }
        base.save_run_state(state_path, state)

        if rc != 0 or log_path is None:
            print("EXTENSION_RUN_FAILED=" + eid)
            continue

        accepted_raw, rejected_raw = collect_one_log(repo, args.runner_python, log_path, tmp, eid)
        append_jsonl(rejected_path, [{"extension_id": eid, "record": r} for r in rejected_raw])

        canon, stud, quar = [], [], []
        for raw in accepted_raw:
            sample = base.enrich_canonical(
                raw,
                collection_head=base.current_head(repo),
                teacher_manifest=teacher_manifest,
                registry_by_scenario=registry_by_scenario,
            )
            meta = sample.setdefault("metadata", {})
            meta.update({
                "dataset_version": EXTENSION_DATASET_VERSION,
                "extension_id": eid,
                "extension_type": EXTENSION_TYPE,
                "parent_scenario_id": sid,
                "parent_scenario_path": runner_path,
                "base_seed": int(item["base_seed"]),
                "extension_seed": int(item["extension_seed"]),
                "extension_plan_canonical_sha256": plan["plan_canonical_sha256"],
                "extension_config_id": ext_config_id,
            })

            if meta.get("seed") != int(item["extension_seed"]):
                quar.append({"extension_id": eid, "reason": "SEED_OVERRIDE_NOT_PROPAGATED", "canonical_sample": sample})
                continue

            view, reason = base.student_view_or_reason(sample)
            if reason is not None:
                quar.append({"extension_id": eid, "reason": reason, "canonical_sample": sample})
                continue

            canon.append(sample)
            stud.append(view)

        append_jsonl(canonical_path, canon)
        append_jsonl(student_path, stud)
        append_jsonl(quarantine_path, quar)
        ext_valid += len(canon)

        print("CURRENT_EXTENSION_VALID=" + str(ext_valid))
        print("CURRENT_TOTAL_VALID=" + str(len(base_rows) + ext_valid))
        print("CURRENT_EXTENSION_QUARANTINE=" + str(len(base.read_jsonl(quarantine_path))))
        print("CURRENT_EXTENSION_REJECTED=" + str(len(base.read_jsonl(rejected_path))))

    base.validate_canonical(repo, args.runner_python, canonical_path)

    summary = {
        "dataset_version": EXTENSION_DATASET_VERSION,
        "base_dataset_count": len(base_rows),
        "extension_valid": len(base.read_jsonl(canonical_path)),
        "extension_student_eligible": len(base.read_jsonl(student_path)),
        "extension_quarantined": len(base.read_jsonl(quarantine_path)),
        "extension_rejected": len(base.read_jsonl(rejected_path)),
        "combined_valid": len(base_rows) + len(base.read_jsonl(canonical_path)),
        "target_total": int(plan["target_total"]),
        "target_reached": len(base_rows) + len(base.read_jsonl(canonical_path)) >= int(plan["target_total"]),
        "runs_launched_this_invocation": launched,
        "failed_extensions": [
            k for k, v in state["runs"].items()
            if isinstance(v, dict) and v.get("status") == "FAILED"
        ],
    }
    base.write_json(out / "extension_summary.json", summary)
    print("B1_D1_EXTENSION_SUMMARY=" + json.dumps(summary, ensure_ascii=False))
    return 0 if not summary["failed_extensions"] else 3

if __name__ == "__main__":
    raise SystemExit(main())
