#!/usr/bin/env python3
"""B1 D3 Wave1 Teacher-v4 expansion collector.

Consumes the frozen Wave2 plan only. Historical Wave1 acquisition is never
modified. Acquisition resume is keyed by plan extension_id, not by final
dataset sample_id.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any


DATASET_VERSION = "teacher_distill_v0.5_d3_expansion_wave1_v4"

EXPECTED_PLAN_VERSION = "b1_d3_expansion_wave1_v1"
EXPECTED_PLAN_REPO_SHA = (
    "a037952b98e77b76a62daca4447334f81347c2d2"
)
EXPECTED_PLAN_CANONICAL_SHA256 = (
    "7bee42b1080bfbf095ec85cc6570590211ef058a0df34af424787766e413c2aa"
)
EXPECTED_PLAN_FILE_SHA256 = (
    "0931c543fd86042af7b6d92d4490fffe0e380583f792d7430acde1b63ceb14e5"
)

EXPECTED_TEACHER_PROFILE = "b1-pinned-teacher-v4"
EXPECTED_TEACHER_GIT_SHA = (
    "95e97b00def8ec36f12937da34ce8bb9082c4a04"
)
EXPECTED_MODEL_ID = "Qwen/Qwen3.5-2B"
EXPECTED_MODEL_REVISION = (
    "15852e8c16360a2fea060d615a32b45270f8a8fc"
)
EXPECTED_MODEL_ARTIFACT_SHA256 = (
    "4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa"
)
EXPECTED_QWEN_MODE = "planner_v2"

EXPECTED_RUNS = 2000
EXPECTED_SEED_START = 2_200_000
EXPECTED_SEED_END = 2_201_999

DEFAULT_PLAN = (
    "artifacts/b1_d3_expansion_plan_wave1_v1/"
    "d3_expansion_plan_wave1.json"
)
DEFAULT_TEACHER_MANIFEST = "challenge/teacher_pinned_manifest_v4.json"
DEFAULT_TEACHER_REPO_ROOT = "../carla_main_teacher_refresh"
DEFAULT_OUTPUT_ROOT = "artifacts/b1_d3_wave1_2000_teacher_v4"
DEFAULT_SERVICE_URL = "http" + "://127.0.0.1:18007"

STATE_SCHEMA_VERSION = "1.0"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON object expected: {path}")
    return value


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json_sha256_without_field(
    value: dict[str, Any],
    field: str,
) -> str:
    obj = dict(value)
    obj.pop(field, None)
    raw = json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


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
            f"git {' '.join(args)} failed for {repo}: "
            f"{result.stderr.strip()}"
        )
    return result.stdout.strip()


def current_branch(repo: Path) -> str:
    return git_output(repo, "rev-parse", "--abbrev-ref", "HEAD")


def verify_collector_matches_head(
    repo: Path,
) -> dict[str, Any]:
    rel = Path("challenge/dataset/collect_d3_wave1.py")
    path = repo / rel

    if not path.is_file():
        raise RuntimeError(f"collector missing: {path}")

    worktree_sha = sha256_file(path)

    result = subprocess.run(
        ["git", "-C", str(repo), "show", f"HEAD:{rel.as_posix()}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "D3 Wave1 collector is not tracked in HEAD; commit it before "
            "formal acquisition"
        )

    head_sha = hashlib.sha256(result.stdout).hexdigest()

    if worktree_sha != head_sha:
        raise RuntimeError(
            "D3 Wave1 collector differs from committed HEAD: "
            f"worktree={worktree_sha} head={head_sha}"
        )

    return {
        "path": rel.as_posix(),
        "sha256": worktree_sha,
        "head_sha256": head_sha,
        "matches_head": True,
    }


def health(
    url: str,
    pinned: dict[str, Any],
) -> dict[str, Any]:
    with urllib.request.urlopen(
        url.rstrip("/") + "/health",
        timeout=5,
    ) as response:
        data = json.loads(response.read())

    if data.get("status") != "READY":
        raise RuntimeError(
            f"Teacher service not ready: {data.get('status')!r}"
        )

    if data.get("production_ready") is not True:
        raise RuntimeError(
            "Teacher service production_ready is not true"
        )

    if data.get("model_id") != pinned["model_id"]:
        raise RuntimeError(
            "Teacher service model mismatch: "
            f"{data.get('model_id')!r} != {pinned['model_id']!r}"
        )

    if data.get("qwen_mode") != pinned["qwen_mode"]:
        raise RuntimeError(
            "Teacher service qwen_mode mismatch: "
            f"{data.get('qwen_mode')!r} != {pinned['qwen_mode']!r}"
        )

    return data


def verify_teacher_manifest(
    path: Path,
) -> dict[str, Any]:
    pinned = load_json(path)

    expected = {
        "teacher_profile": EXPECTED_TEACHER_PROFILE,
        "teacher_git_sha": EXPECTED_TEACHER_GIT_SHA,
        "model_id": EXPECTED_MODEL_ID,
        "model_revision": EXPECTED_MODEL_REVISION,
        "model_artifact_sha256": EXPECTED_MODEL_ARTIFACT_SHA256,
        "qwen_mode": EXPECTED_QWEN_MODE,
    }

    for key, wanted in expected.items():
        actual = pinned.get(key)
        if actual != wanted:
            raise RuntimeError(
                f"Teacher manifest mismatch for {key}: "
                f"{actual!r} != {wanted!r}"
            )

    verification = pinned.get("verification") or {}

    if verification.get("directional_semantic_gate") != "8/8 PASS":
        raise RuntimeError(
            "Teacher v4 directional semantic gate not frozen PASS"
        )

    if (
        verification.get("directional_closed_loop_gate")
        != "8/8 SUCCEEDED"
    ):
        raise RuntimeError(
            "Teacher v4 directional closed-loop gate not frozen PASS"
        )

    return pinned


def verify_teacher_repo(
    teacher_repo: Path,
) -> dict[str, Any]:
    if not teacher_repo.is_dir():
        raise RuntimeError(
            f"Teacher repo does not exist: {teacher_repo}"
        )

    head = git_output(
        teacher_repo,
        "rev-parse",
        "HEAD",
    )

    if head != EXPECTED_TEACHER_GIT_SHA:
        raise RuntimeError(
            f"Teacher HEAD mismatch: "
            f"{head} != {EXPECTED_TEACHER_GIT_SHA}"
        )

    tracked_status = git_output(
        teacher_repo,
        "status",
        "--short",
        "--untracked-files=no",
    )

    if tracked_status:
        raise RuntimeError(
            "Teacher tracked worktree is dirty:\n"
            + tracked_status
        )

    return {
        "repo_root": str(teacher_repo.resolve()),
        "git_sha": head,
        "tracked_worktree_clean": True,
    }


def resolve_scenario_path(
    root: Path,
    scenario_path: str,
) -> Path | None:
    rel = Path(scenario_path)

    candidates = [
        root / rel,
        root / "scenarios" / rel,
    ]

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    return None


def verify_plan(
    plan_path: Path,
    teacher_manifest: dict[str, Any],
    challenge_repo: Path,
    teacher_repo: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not plan_path.is_file():
        raise RuntimeError(
            f"Wave2 plan missing: {plan_path}"
        )

    plan_file_sha = sha256_file(plan_path)

    if plan_file_sha != EXPECTED_PLAN_FILE_SHA256:
        raise RuntimeError(
            "Wave2 plan file SHA mismatch: "
            f"{plan_file_sha} != {EXPECTED_PLAN_FILE_SHA256}"
        )

    plan = load_json(plan_path)

    if plan.get("plan_version") != EXPECTED_PLAN_VERSION:
        raise RuntimeError(
            "Wave2 plan_version mismatch: "
            f"{plan.get('plan_version')!r}"
        )

    if plan.get("challenge_git_sha") != EXPECTED_PLAN_REPO_SHA:
        raise RuntimeError(
            "D3 Wave1 plan challenge_git_sha mismatch: "
            f"{plan.get('challenge_git_sha')!r}"
        )

    if plan.get("formal_code_gate") is not True:
        raise RuntimeError(
            "Wave2 plan was not generated through formal code gate"
        )

    embedded_canonical = plan.get(
        "plan_canonical_sha256"
    )

    recomputed_canonical = (
        canonical_json_sha256_without_field(
            plan,
            "plan_canonical_sha256",
        )
    )

    if (
        embedded_canonical
        != EXPECTED_PLAN_CANONICAL_SHA256
        or recomputed_canonical
        != EXPECTED_PLAN_CANONICAL_SHA256
    ):
        raise RuntimeError(
            "Wave2 plan canonical hash mismatch: "
            f"embedded={embedded_canonical} "
            f"recomputed={recomputed_canonical}"
        )

    teacher_identity = plan.get(
        "teacher_identity"
    ) or {}

    expected_teacher_values = {
        "teacher_profile":
            teacher_manifest["teacher_profile"],
        "teacher_baseline_git_sha":
            teacher_manifest["teacher_git_sha"],
        "teacher_model_id":
            teacher_manifest["model_id"],
        "teacher_model_revision":
            teacher_manifest["model_revision"],
        "teacher_model_artifact_sha256":
            teacher_manifest[
                "model_artifact_sha256"
            ],
    }

    for key, wanted in expected_teacher_values.items():
        actual = teacher_identity.get(key)
        if actual != wanted:
            raise RuntimeError(
                f"Plan Teacher mismatch for {key}: "
                f"{actual!r} != {wanted!r}"
            )

    runs = plan.get("plan")

    if not isinstance(runs, list):
        raise RuntimeError(
            "Wave2 plan[] missing"
        )

    if len(runs) != EXPECTED_RUNS:
        raise RuntimeError(
            f"Wave2 run count mismatch: "
            f"{len(runs)} != {EXPECTED_RUNS}"
        )

    ids = [
        row.get("extension_id")
        for row in runs
    ]

    seeds = [
        row.get("extension_seed")
        for row in runs
    ]

    if (
        any(
            not isinstance(x, str) or not x
            for x in ids
        )
        or len(ids) != len(set(ids))
    ):
        raise RuntimeError(
            "Wave2 extension_id uniqueness failure"
        )

    if (
        any(type(x) is not int for x in seeds)
        or len(seeds) != len(set(seeds))
    ):
        raise RuntimeError(
            "Wave2 extension_seed uniqueness failure"
        )

    expected_seeds = list(
        range(
            EXPECTED_SEED_START,
            EXPECTED_SEED_END + 1,
        )
    )

    if seeds != expected_seeds:
        raise RuntimeError(
            "Wave2 seed namespace is not the exact frozen "
            f"{EXPECTED_SEED_START}..{EXPECTED_SEED_END}"
        )

    for row in runs:
        if row.get("policy_class") != "TRAIN_POSITIVE":
            raise RuntimeError(
                "Non-TRAIN_POSITIVE row leaked into Wave2 plan: "
                f"{row.get('extension_id')}"
            )

        if row.get("source_bucket") not in {
            "SEEN",
            "VARIANT",
        }:
            raise RuntimeError(
                "Forbidden source bucket in Wave2: "
                f"{row.get('extension_id')} "
                f"{row.get('source_bucket')!r}"
            )

        if (
            row.get("teacher_profile")
            != EXPECTED_TEACHER_PROFILE
        ):
            raise RuntimeError(
                "Per-run Teacher profile mismatch: "
                f"{row.get('extension_id')}"
            )

        if (
            row.get("teacher_git_sha")
            != EXPECTED_TEACHER_GIT_SHA
        ):
            raise RuntimeError(
                "Per-run Teacher SHA mismatch: "
                f"{row.get('extension_id')}"
            )

        scenario_path = str(
            row.get("scenario_path", "")
        )

        if not scenario_path:
            raise RuntimeError(
                "Wave2 row missing scenario_path"
            )

        challenge_scenario = resolve_scenario_path(
            challenge_repo,
            scenario_path,
        )

        teacher_scenario = resolve_scenario_path(
            teacher_repo,
            scenario_path,
        )

        if challenge_scenario is None:
            raise RuntimeError(
                "Scenario missing from challenge repo: "
                + scenario_path
            )

        if teacher_scenario is None:
            raise RuntimeError(
                "Scenario missing from Teacher repo: "
                + scenario_path
            )

        # Do not silently execute divergent scenario definitions.
        if (
            sha256_file(challenge_scenario)
            != sha256_file(teacher_scenario)
        ):
            raise RuntimeError(
                "Scenario differs between challenge and Teacher "
                f"repos: {scenario_path}"
            )

    return plan, runs


def empty_state(
    *,
    plan: dict[str, Any],
    plan_path: Path,
    collector_repo_sha: str,
) -> dict[str, Any]:
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "dataset_version": DATASET_VERSION,
        "plan_version": EXPECTED_PLAN_VERSION,
        "plan_file": str(plan_path.resolve()),
        "plan_file_sha256":
            EXPECTED_PLAN_FILE_SHA256,
        "plan_canonical_sha256":
            EXPECTED_PLAN_CANONICAL_SHA256,
        "plan_repo_git_sha":
            plan["challenge_git_sha"],
        "collector_repo_git_sha":
            collector_repo_sha,
        "teacher_profile":
            EXPECTED_TEACHER_PROFILE,
        "teacher_git_sha":
            EXPECTED_TEACHER_GIT_SHA,
        "runs": {},
    }


def validate_state_identity(
    state: dict[str, Any],
) -> None:
    expected = {
        "schema_version":
            STATE_SCHEMA_VERSION,
        "dataset_version":
            DATASET_VERSION,
        "plan_version":
            EXPECTED_PLAN_VERSION,
        "plan_file_sha256":
            EXPECTED_PLAN_FILE_SHA256,
        "plan_canonical_sha256":
            EXPECTED_PLAN_CANONICAL_SHA256,
        "plan_repo_git_sha":
            EXPECTED_PLAN_REPO_SHA,
        "teacher_profile":
            EXPECTED_TEACHER_PROFILE,
        "teacher_git_sha":
            EXPECTED_TEACHER_GIT_SHA,
    }

    for key, wanted in expected.items():
        actual = state.get(key)
        if actual != wanted:
            raise RuntimeError(
                f"run_state identity mismatch for {key}: "
                f"{actual!r} != {wanted!r}"
            )

    if not isinstance(state.get("runs"), dict):
        raise RuntimeError(
            "run_state runs must be an object"
        )


def atomic_write_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    tmp = path.with_suffix(
        path.suffix + ".tmp"
    )

    tmp.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    tmp.replace(path)


def load_or_create_state(
    state_path: Path,
    *,
    resume: bool,
    plan: dict[str, Any],
    plan_path: Path,
    collector_repo_sha: str,
) -> dict[str, Any]:
    if state_path.exists():
        if not resume:
            raise RuntimeError(
                f"run_state already exists: {state_path}. "
                "Use --resume only if continuing this exact "
                "Wave2 acquisition."
            )

        state = load_json(state_path)
        validate_state_identity(state)
        return state

    if resume:
        raise RuntimeError(
            f"--resume requested but run_state missing: "
            f"{state_path}"
        )

    return empty_state(
        plan=plan,
        plan_path=plan_path,
        collector_repo_sha=collector_repo_sha,
    )


def select_runs(
    runs: list[dict[str, Any]],
    state: dict[str, Any],
    *,
    start_index: int,
    max_runs: int | None,
    resume: bool,
) -> tuple[
    list[dict[str, Any]],
    int,
]:
    if start_index < 0:
        raise RuntimeError(
            "--start-index must be >= 0"
        )

    if start_index > len(runs):
        raise RuntimeError(
            "--start-index exceeds plan length"
        )

    candidates = runs[start_index:]

    already_succeeded = 0

    if resume:
        filtered = []

        state_runs = state["runs"]

        for item in candidates:
            extension_id = item["extension_id"]
            previous = state_runs.get(
                extension_id
            )

            if (
                isinstance(previous, dict)
                and previous.get("status")
                == "SUCCEEDED"
            ):
                already_succeeded += 1
                continue

            filtered.append(item)

        candidates = filtered

    if max_runs is not None:
        if max_runs < 1:
            raise RuntimeError(
                "--max-runs must be >= 1"
            )
        candidates = candidates[:max_runs]

    return candidates, already_succeeded


def clear_attempt_outputs(
    item_log_dir: Path,
    item_image_dir: Path,
) -> None:
    # A failed acquisition may have left partial evidence. Before retrying
    # that same extension_id, remove only that item's isolated outputs.
    for path in (
        item_log_dir,
        item_image_dir,
    ):
        if path.exists():
            shutil.rmtree(path)


def run_case(
    teacher_repo: Path,
    challenge_repo: Path,
    item: dict[str, Any],
    service: str,
    logs_root: Path,
    images_root: Path,
) -> int:
    extension_id = item["extension_id"]

    item_logs = (
        logs_root / extension_id
    )
    item_images = (
        images_root / extension_id
    )

    clear_attempt_outputs(
        item_logs,
        item_images,
    )

    item_logs.mkdir(
        parents=True,
        exist_ok=True,
    )

    item_images.mkdir(
        parents=True,
        exist_ok=True,
    )

    scenario_path = str(
        item["scenario_path"]
    )

    scenario_arg = (
        scenario_path
        if scenario_path.startswith(
            "scenarios/"
        )
        else "scenarios/" + scenario_path
    )

    image_prefix = item_images.relative_to(
        challenge_repo
    )

    cmd = [
        sys.executable,
        "-m",
        "integration.carla_runner",

        "--host",
        "127.0.0.1",

        "--port",
        "2000",

        "--scenario-file",
        scenario_arg,

        "--seed",
        str(item["extension_seed"]),

        "--qwen-service-url",
        service,

        "--qwen-mode",
        EXPECTED_QWEN_MODE,

        "--qwen-timeout-ms",
        "5000",

        "--qwen-queue-size",
        "1",

        "--qwen-image-root",
        str(challenge_repo),

        "--qwen-image-prefix",
        str(image_prefix),

        "--log-dir",
        str(item_logs),
    ]

    print(
        "RUN",
        extension_id,
        scenario_path,
        item["extension_seed"],
        flush=True,
    )

    result = subprocess.run(
        cmd,
        cwd=teacher_repo,
        check=False,
    )

    return result.returncode


def collect_dataset(
    repo: Path,
    logs_root: Path,
    dataset_root: Path,
) -> None:
    input_logs = sorted(
        p
        for p in logs_root.rglob("*.jsonl")
        if p.is_file()
    )

    if not input_logs:
        raise RuntimeError(
            "No ScenarioEvidenceRecorder JSONL logs found"
        )

    dataset_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    cmd = [
        sys.executable,
        "challenge/dataset/collector.py",

        "--repo-root",
        str(repo),

        "--output",
        str(
            dataset_root
            / "d2_valid.jsonl"
        ),

        "--rejected-output",
        str(
            dataset_root
            / "d2_rejected.jsonl"
        ),

        "--dataset-version",
        DATASET_VERSION,
    ]

    for path in input_logs:
        cmd += [
            "--input-log",
            str(path),
        ]

    result = subprocess.run(
        cmd,
        cwd=repo,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "D3 Wave1 collector.py post-processing failed"
        )


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--plan",
        default=DEFAULT_PLAN,
    )

    parser.add_argument(
        "--teacher-manifest",
        default=DEFAULT_TEACHER_MANIFEST,
    )

    parser.add_argument(
        "--teacher-repo-root",
        default=DEFAULT_TEACHER_REPO_ROOT,
    )

    parser.add_argument(
        "--qwen-service-url",
        default=DEFAULT_SERVICE_URL,
    )

    parser.add_argument(
        "--output-root",
        default=DEFAULT_OUTPUT_ROOT,
    )

    parser.add_argument(
        "--start-index",
        type=int,
        default=0,
    )

    parser.add_argument(
        "--max-runs",
        type=int,
    )

    parser.add_argument(
        "--resume",
        action="store_true",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Validate committed collector, frozen plan, "
            "Teacher manifest/repo, all scenario files, "
            "and live Teacher service health without "
            "executing CARLA."
        ),
    )

    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[2]

    collector_identity = (
        verify_collector_matches_head(
            repo
        )
    )

    collector_repo_sha = git_output(
        repo,
        "rev-parse",
        "HEAD",
    )

    plan_path = Path(args.plan)
    if not plan_path.is_absolute():
        plan_path = (
            repo / plan_path
        ).resolve()

    manifest_path = Path(
        args.teacher_manifest
    )
    if not manifest_path.is_absolute():
        manifest_path = (
            repo / manifest_path
        ).resolve()

    teacher_repo = Path(
        args.teacher_repo_root
    )
    if not teacher_repo.is_absolute():
        teacher_repo = (
            repo / teacher_repo
        ).resolve()

    output_root = Path(
        args.output_root
    )
    if not output_root.is_absolute():
        output_root = (
            repo / output_root
        ).resolve()

    pinned = verify_teacher_manifest(
        manifest_path
    )

    teacher_repo_info = verify_teacher_repo(
        teacher_repo
    )

    plan, runs = verify_plan(
        plan_path,
        pinned,
        repo,
        teacher_repo,
    )

    teacher_runtime = health(
        args.qwen_service_url,
        pinned,
    )

    print(
        "COLLECTOR_CODE_GATE=PASS"
    )
    print(
        "COLLECTOR_REPO_HEAD="
        + collector_repo_sha
    )
    print(
        "COLLECTOR_SHA256="
        + collector_identity["sha256"]
    )
    print(
        "PLAN_VERSION="
        + plan["plan_version"]
    )
    print(
        "PLAN_REPO_SHA="
        + plan["challenge_git_sha"]
    )
    print(
        "PLAN_CANONICAL_SHA256="
        + plan["plan_canonical_sha256"]
    )
    print(
        "PLAN_FILE_SHA256="
        + sha256_file(plan_path)
    )
    print(
        "PLANNED_RUNS="
        + str(len(runs))
    )
    print(
        "SEED_RANGE="
        + f"{runs[0]['extension_seed']}"
        + ".."
        + f"{runs[-1]['extension_seed']}"
    )
    print(
        "TEACHER_PROFILE="
        + pinned["teacher_profile"]
    )
    print(
        "TEACHER_GIT_SHA="
        + teacher_repo_info["git_sha"]
    )
    print(
        "TEACHER_TRACKED_CLEAN=PASS"
    )
    print(
        "TEACHER_SERVICE_STATUS="
        + str(
            teacher_runtime.get(
                "status"
            )
        )
    )
    print(
        "TEACHER_SERVICE_PRODUCTION_READY="
        + str(
            teacher_runtime.get(
                "production_ready"
            )
        )
    )
    print(
        "SCENARIO_PARITY=PASS"
    )

    if args.dry_run:
        print(
            "D2_WAVE2_COLLECTOR_DRY_RUN=PASS"
        )
        return 0

    logs_root = (
        output_root / "logs"
    )
    images_root = (
        output_root / "qwen_images"
    )
    dataset_root = (
        output_root / "dataset"
    )
    state_path = (
        output_root / "run_state.json"
    )

    if output_root.exists() and not args.resume:
        meaningful = [
            p
            for p in output_root.iterdir()
            if p.name not in {
                ".DS_Store",
            }
        ]

        if meaningful:
            raise RuntimeError(
                "Wave2 output root is not empty: "
                f"{output_root}. "
                "Use a new root or --resume."
            )

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    logs_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    images_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataset_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    state = load_or_create_state(
        state_path,
        resume=args.resume,
        plan=plan,
        plan_path=plan_path,
        collector_repo_sha=collector_repo_sha,
    )

    # For a resumed acquisition, collector code may have advanced only
    # through a deliberate committed bug fix. Preserve both identities.
    state.setdefault(
        "collector_repo_git_shas",
        [],
    )

    if (
        collector_repo_sha
        not in state["collector_repo_git_shas"]
    ):
        state[
            "collector_repo_git_shas"
        ].append(
            collector_repo_sha
        )

    selected, already_succeeded = (
        select_runs(
            runs,
            state,
            start_index=args.start_index,
            max_runs=args.max_runs,
            resume=args.resume,
        )
    )

    print(
        "SELECTED_RUNS="
        + str(len(selected))
    )

    print(
        "RESUME_ALREADY_SUCCEEDED="
        + str(already_succeeded)
    )

    atomic_write_json(
        state_path,
        state,
    )

    invocation_success = 0
    invocation_failed = 0

    for item in selected:
        extension_id = item[
            "extension_id"
        ]

        rc = run_case(
            teacher_repo,
            repo,
            item,
            args.qwen_service_url,
            logs_root,
            images_root,
        )

        status = (
            "SUCCEEDED"
            if rc == 0
            else "FAILED"
        )

        state["runs"][
            extension_id
        ] = {
            "extension_id":
                extension_id,
            "scenario_id":
                item["scenario_id"],
            "scenario_path":
                item["scenario_path"],
            "extension_seed":
                item["extension_seed"],
            "quota_bucket":
                item["quota_bucket"],
            "returncode":
                rc,
            "status":
                status,
        }

        atomic_write_json(
            state_path,
            state,
        )

        if rc == 0:
            invocation_success += 1
        else:
            invocation_failed += 1
            print(
                "SCENARIO_RUN_FAILED",
                extension_id,
                item["scenario_path"],
                item["extension_seed"],
                "returncode=",
                rc,
                flush=True,
            )

    # Rebuild dataset from all isolated acquisition logs currently present,
    # including previous successful runs during --resume.
    collect_dataset(
        repo,
        logs_root,
        dataset_root,
    )

    run_records = state["runs"]

    total_succeeded = sum(
        1
        for x in run_records.values()
        if (
            isinstance(x, dict)
            and x.get("status")
            == "SUCCEEDED"
        )
    )

    total_failed = sum(
        1
        for x in run_records.values()
        if (
            isinstance(x, dict)
            and x.get("status")
            == "FAILED"
        )
    )

    provenance = {
        "schema_version": "1.0",

        "dataset_version":
            DATASET_VERSION,

        "plan": {
            "path":
                str(plan_path.resolve()),
            "plan_version":
                plan["plan_version"],
            "plan_file_sha256":
                sha256_file(plan_path),
            "plan_canonical_sha256":
                plan[
                    "plan_canonical_sha256"
                ],
            "plan_repo_git_sha":
                plan["challenge_git_sha"],
            "planned_runs":
                len(runs),
        },

        "collector": {
            "path":
                collector_identity["path"],
            "sha256":
                collector_identity["sha256"],
            "challenge_repo_git_sha":
                collector_repo_sha,
            "challenge_branch":
                current_branch(repo),
        },

        "teacher": {
            "teacher_profile":
                pinned["teacher_profile"],
            "teacher_git_sha":
                pinned["teacher_git_sha"],
            "teacher_tag":
                pinned.get("teacher_tag"),
            "teacher_model_id":
                pinned["model_id"],
            "teacher_model_revision":
                pinned[
                    "model_revision"
                ],
            "teacher_model_artifact_sha256":
                pinned[
                    "model_artifact_sha256"
                ],
            "teacher_qwen_mode":
                pinned["qwen_mode"],
            "teacher_manifest_path":
                str(
                    manifest_path.resolve()
                ),
            "teacher_manifest_sha256":
                sha256_file(
                    manifest_path
                ),
            "teacher_execution_repo":
                teacher_repo_info,
            "teacher_runtime_health":
                teacher_runtime,
            "teacher_service_url":
                args.qwen_service_url,
        },

        "acquisition": {
            "output_root":
                str(
                    output_root.resolve()
                ),
            "state_path":
                str(
                    state_path.resolve()
                ),
            "start_index":
                args.start_index,
            "max_runs":
                args.max_runs,
            "resume":
                bool(args.resume),

            "invocation_selected_runs":
                len(selected),
            "invocation_success_count":
                invocation_success,
            "invocation_failed_count":
                invocation_failed,

            "resume_already_succeeded":
                already_succeeded,

            "state_recorded_runs":
                len(run_records),
            "state_succeeded_runs":
                total_succeeded,
            "state_failed_runs":
                total_failed,
        },
    }

    atomic_write_json(
        output_root
        / "provenance_manifest.json",
        provenance,
    )

    print(
        "INVOCATION_SUCCESS="
        + str(invocation_success)
    )
    print(
        "INVOCATION_FAILED="
        + str(invocation_failed)
    )
    print(
        "STATE_SUCCEEDED="
        + str(total_succeeded)
    )
    print(
        "STATE_FAILED="
        + str(total_failed)
    )
    print(
        "D2_WAVE2_COLLECTION_INVOCATION=PASS"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
