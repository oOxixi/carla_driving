#!/usr/bin/env python3
"""B1 D2 expansion collector.

Run CARLA scenarios from the frozen D2 expansion plan, collect
ScenarioEvidenceRecorder JSONL logs and build Teacher distillation data.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.request
from pathlib import Path


DATASET_VERSION = "teacher_distill_v0.3_d2_expansion_wave1_v3"
TEACHER_MANIFEST = "challenge/teacher_pinned_manifest.json"
EXPECTED_TEACHER_GIT_SHA = "1a363c15b9b1790534358c11acbd100a3011fa93"
DEFAULT_TEACHER_REPO_ROOT = "../carla_main_teacher_refresh"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def health(url: str, pinned: dict):
    with urllib.request.urlopen(url.rstrip("/") + "/health", timeout=5) as r:
        data = json.loads(r.read())

    if data.get("status") != "READY":
        raise RuntimeError("Teacher service not ready")
    if data.get("production_ready") is not True:
        raise RuntimeError("Teacher service is not production_ready")
    if data.get("model_id") != pinned["model_id"]:
        raise RuntimeError(
            f"Teacher model mismatch: {data.get('model_id')} != {pinned['model_id']}"
        )
    if data.get("qwen_mode") != pinned["qwen_mode"]:
        raise RuntimeError(
            f"Teacher mode mismatch: {data.get('qwen_mode')} != {pinned['qwen_mode']}"
        )

    return data


def git_output(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed for {repo}: {result.stderr.strip()}"
        )
    return result.stdout.strip()


def verify_teacher_repo(teacher_repo: Path) -> dict:
    if not teacher_repo.is_dir():
        raise RuntimeError(f"Teacher repo does not exist: {teacher_repo}")

    head = git_output(teacher_repo, "rev-parse", "HEAD")
    if head != EXPECTED_TEACHER_GIT_SHA:
        raise RuntimeError(
            f"Teacher HEAD mismatch: {head} != {EXPECTED_TEACHER_GIT_SHA}"
        )

    # Only tracked changes invalidate the frozen Teacher.
    tracked_status = git_output(
        teacher_repo,
        "status",
        "--short",
        "--untracked-files=no",
    )
    if tracked_status:
        raise RuntimeError(
            "Teacher tracked worktree is dirty:\n" + tracked_status
        )

    return {
        "repo_root": str(teacher_repo.resolve()),
        "git_sha": head,
        "tracked_worktree_clean": True,
    }


def run_case(teacher_repo, challenge_repo, item, service, logs, images):
    cmd = [
        sys.executable, "-m", "integration.carla_runner",
        "--host", "127.0.0.1",
        "--port", "2000",
        "--scenario-file",
            (
                item["scenario_path"]
                if item["scenario_path"].startswith("scenarios/")
                else "scenarios/" + item["scenario_path"]
            ),
        "--seed", str(item["extension_seed"]),
        "--qwen-service-url", service,
        "--qwen-mode", "planner_v2",
        "--qwen-timeout-ms", "5000",
        "--qwen-queue-size", "1",
        "--qwen-image-root", str(challenge_repo),
        "--qwen-image-prefix", str(images.relative_to(challenge_repo)),
        "--log-dir", str(logs),
    ]
    print("RUN", item["scenario_path"], item["extension_seed"])
    return subprocess.run(cmd, cwd=teacher_repo, check=False).returncode


def collect(repo, logs, dataset):
    cmd = [
        sys.executable,
        "challenge/dataset/collector.py",
        "--repo-root",
        str(repo),
        "--output",
        str(dataset / "d2_valid.jsonl"),
        "--rejected-output",
        str(dataset / "d2_rejected.jsonl"),
        "--dataset-version",
        DATASET_VERSION,
    ]
    for p in sorted(logs.glob("*.jsonl")):
        cmd += ["--input-log", str(p)]

    if subprocess.run(cmd, cwd=repo, check=False).returncode:
        raise RuntimeError("collector failed")


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--plan",
        default="artifacts/b1_d2_expansion_plan_v1/d2_expansion_plan_wave1.json",
    )
    p.add_argument("--max-runs", type=int)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--qwen-service-url", default="http://127.0.0.1:18003")
    p.add_argument(
        "--teacher-repo-root",
        default=DEFAULT_TEACHER_REPO_ROOT,
        help="Frozen verified main worktree used to execute Teacher scenarios",
    )
    p.add_argument(
        "--output-root",
        default="artifacts/b1_d2_expansion_wave1",
        help="Challenge-repo output directory for logs, images, dataset, and provenance",
    )
    a = p.parse_args()

    repo = Path(__file__).resolve().parents[2]
    teacher_repo = Path(a.teacher_repo_root)
    if not teacher_repo.is_absolute():
        teacher_repo = (repo / teacher_repo).resolve()

    teacher_repo_info = verify_teacher_repo(teacher_repo)

    plan = load_json(repo / a.plan)
    runs = plan["plan"]

    seeds = [int(x["extension_seed"]) for x in runs]
    if len(seeds) != len(set(seeds)):
        raise RuntimeError("duplicate seeds")

    for x in runs:
        scenario_path = x["scenario_path"]

        candidate_paths = [
            teacher_repo / scenario_path,
            teacher_repo / "scenarios" / scenario_path,
        ]

        if not any(path.is_file() for path in candidate_paths):
            raise RuntimeError(
                "missing scenario " + scenario_path
            )

    print("PLAN_VERSION=", plan["plan_version"])
    print("PLANNED_RUNS=", len(runs))
    print("SEED_UNIQUE=PASS")
    print("SCENARIO_EXIST=PASS")
    print("TEACHER_REPO=", teacher_repo_info["repo_root"])
    print("TEACHER_GIT_SHA=", teacher_repo_info["git_sha"])
    print("TEACHER_TRACKED_CLEAN=PASS")

    if a.dry_run:
        print("D2_EXPANSION_DRY_RUN=PASS")
        return

    pinned = load_json(repo / TEACHER_MANIFEST)

    required_pin = {
        "teacher_profile": "b1-pinned-teacher-v3",
        "teacher_git_sha": "1a363c15b9b1790534358c11acbd100a3011fa93",
        "model_id": "Qwen/Qwen3.5-2B",
        "model_revision": "15852e8c16360a2fea060d615a32b45270f8a8fc",
        "model_artifact_sha256":
            "4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa",
        "qwen_mode": "planner_v2",
    }

    for key, expected in required_pin.items():
        if pinned.get(key) != expected:
            raise RuntimeError(
                f"Teacher pin mismatch for {key}: "
                f"{pinned.get(key)!r} != {expected!r}"
            )

    teacher = health(a.qwen_service_url, pinned)

    out = Path(a.output_root)
    if not out.is_absolute():
        out = repo / out
    logs = out / "logs"
    images = out / "qwen_images"
    dataset = out / "dataset"

    for d in (logs, images, dataset):
        d.mkdir(parents=True, exist_ok=True)

    selected = runs[:a.max_runs] if a.max_runs else runs

    runner_success_count = 0
    runner_failed_count = 0
    runner_failures = []

    for item in selected:
        rc = run_case(
            teacher_repo,
            repo,
            item,
            a.qwen_service_url,
            logs,
            images,
        )

        if rc == 0:
            runner_success_count += 1
        else:
            runner_failed_count += 1
            runner_failures.append({
                "scenario_path": item["scenario_path"],
                "extension_seed": item["extension_seed"],
                "returncode": rc,
            })

            print(
                "SCENARIO_RUN_FAILED",
                item["scenario_path"],
                item["extension_seed"],
                "returncode=",
                rc,
            )

    # Collect once after all selected scenario runs.
    collect(repo, logs, dataset)

    (out / "provenance_manifest.json").write_text(
        json.dumps(
            {
                "dataset_version": DATASET_VERSION,
                "plan": a.plan,
                "output_root": str(out.resolve()),
                "teacher_profile": pinned["teacher_profile"],
                "teacher_git_sha": pinned["teacher_git_sha"],
                "teacher_tag": pinned.get("teacher_tag"),
                "teacher_model_id": pinned["model_id"],
                "teacher_model_revision": pinned["model_revision"],
                "teacher_model_artifact_sha256": pinned[
                    "model_artifact_sha256"
                ],
                "teacher_qwen_mode": pinned["qwen_mode"],
                "teacher_pinned_manifest": pinned,
                "teacher_runtime_health": teacher,
                "teacher_execution_repo": teacher_repo_info,
                "challenge_repo_git_sha": git_output(repo, "rev-parse", "HEAD"),
                "executed_runs": len(selected),
                "runner_success_count": runner_success_count,
                "runner_failed_count": runner_failed_count,
                "runner_failures": runner_failures,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
