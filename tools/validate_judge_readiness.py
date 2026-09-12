"""Run the reproducible, judge-facing static and optional live acceptance gates."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integration.carla_runner import DEFAULT_QWEN_MODEL  # noqa: E402
from integration.qwen_profiles import (  # noqa: E402
    PRODUCTION_QWEN_ARTIFACT_SHA256,
    PRODUCTION_QWEN_MODEL,
    PRODUCTION_QWEN_PROFILE,
    PRODUCTION_QWEN_REVISION,
    get_qwen_profile,
)


def _process(
    command: Sequence[str],
    *,
    timeout_s: float = 900.0,
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            list(command),
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
            check=False,
        )
        output = "\n".join(
            part.strip()
            for part in (completed.stdout, completed.stderr)
            if part.strip()
        )
        return {
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "command": list(command),
            "return_code": completed.returncode,
            "duration_s": round(time.monotonic() - started, 3),
            "output_tail": output.splitlines()[-30:],
        }
    except subprocess.TimeoutExpired as error:
        return {
            "status": "FAIL",
            "command": list(command),
            "return_code": None,
            "duration_s": round(time.monotonic() - started, 3),
            "output_tail": [f"TimeoutExpired: {error}"],
        }


def _git_text(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return completed.stdout.strip()


def _repository_check(*, allow_dirty: bool) -> dict[str, Any]:
    try:
        branch = _git_text("branch", "--show-current")
        head = _git_text("rev-parse", "HEAD")
        main = _git_text("rev-parse", "origin/main")
        merge_base = _git_text("merge-base", "HEAD", "origin/main")
        dirty_entries = _git_text(
            "status", "--porcelain", "--untracked-files=all"
        ).splitlines()
        based_on_main = merge_base == main
        passed = based_on_main and (not dirty_entries or allow_dirty)
        return {
            "name": "repository_baseline",
            "status": "PASS" if passed else "FAIL",
            "branch": branch,
            "head": head,
            "origin_main": main,
            "merge_base": merge_base,
            "based_on_origin_main": based_on_main,
            "clean": not dirty_entries,
            "dirty_entry_count": len(dirty_entries),
            "dirty_entries": dirty_entries[:30],
            "dirty_allowed": allow_dirty,
        }
    except (OSError, subprocess.CalledProcessError) as error:
        return {
            "name": "repository_baseline",
            "status": "FAIL",
            "error": f"{type(error).__name__}: {error}",
        }


def _qwen_contract_check() -> dict[str, Any]:
    profile = get_qwen_profile(PRODUCTION_QWEN_PROFILE)
    dimensions = {
        "runner_model_matches": DEFAULT_QWEN_MODEL == profile.model,
        "model_matches": profile.model == PRODUCTION_QWEN_MODEL,
        "revision_is_pinned": profile.revision == PRODUCTION_QWEN_REVISION,
        "two_b_only": "2B" in profile.model.upper(),
        "production_profile": profile.optional is False,
        "visual_budget_valid": (
            profile.image_max_side == 224 and profile.visual_tokens == 64
        ),
        "artifact_fingerprint_recorded": (
            len(PRODUCTION_QWEN_ARTIFACT_SHA256) == 64
        ),
    }
    return {
        "name": "production_qwen_contract",
        "status": "PASS" if all(dimensions.values()) else "FAIL",
        "profile": profile.name,
        "model": profile.model,
        "revision": profile.revision,
        "artifact_sha256": PRODUCTION_QWEN_ARTIFACT_SHA256,
        "quantization": profile.quantization,
        "image_max_side": profile.image_max_side,
        "visual_tokens": profile.visual_tokens,
        "dimensions": dimensions,
        "note": (
            "The recorded artifact fingerprint must be rechecked on each "
            "deployment host; repository validation does not hash remote weights."
        ),
    }


def _named_process(name: str, command: Sequence[str]) -> dict[str, Any]:
    result = _process(command)
    result["name"] = name
    return result


def build_report(
    *,
    allow_dirty: bool,
    quick: bool,
    require_live: bool,
    qwen_url: str,
    carla_host: str,
    carla_port: int,
) -> dict[str, Any]:
    checks = [
        _repository_check(allow_dirty=allow_dirty),
        _qwen_contract_check(),
        _named_process(
            "scenario_contracts",
            [sys.executable, "tools/validate_scenarios.py"],
        ),
        _named_process(
            "official_scene_contracts",
            [sys.executable, "tools/validate_official_scenes.py"],
        ),
    ]
    if not quick:
        checks.append(
            _named_process(
                "full_pytest",
                [sys.executable, "-m", "pytest", "-q"],
            )
        )
    if require_live:
        checks.append(
            _named_process(
                "live_qwen_carla_health",
                [
                    sys.executable,
                    "-m",
                    "runtime.healthcheck",
                    "--qwen-url",
                    qwen_url,
                    "--expected-qwen-model",
                    PRODUCTION_QWEN_MODEL,
                    "--expected-qwen-mode",
                    "planner_v2",
                    "--carla-host",
                    carla_host,
                    "--carla-port",
                    str(carla_port),
                    "--require-qwen",
                    "--require-carla",
                ],
            )
        )
    failures = [
        check["name"] for check in checks if check["status"] != "PASS"
    ]
    return {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if not failures else "FAIL",
        "scope": "static+live" if require_live else "static",
        "failed_checks": failures,
        "checks": checks,
    }


def render_markdown(report: dict[str, Any]) -> str:
    repository = next(
        check
        for check in report["checks"]
        if check["name"] == "repository_baseline"
    )
    model = next(
        check
        for check in report["checks"]
        if check["name"] == "production_qwen_contract"
    )
    lines = [
        "# Judge readiness report",
        "",
        f"- Overall: **{report['status']}**",
        f"- Scope: {report['scope']}",
        f"- Created (UTC): {report['created_at_utc']}",
        f"- Branch: {repository.get('branch', 'UNKNOWN')}",
        f"- Commit: {repository.get('head', 'UNKNOWN')}",
        (
            "- Based on frozen origin/main: "
            f"{repository.get('based_on_origin_main', False)}"
        ),
        f"- Worktree clean: {repository.get('clean', False)}",
        "",
        "## Production Qwen contract",
        "",
        f"- Profile: {model.get('profile')}",
        f"- Model: {model.get('model')}",
        f"- Exact revision: {model.get('revision')}",
        f"- Artifact SHA-256: {model.get('artifact_sha256')}",
        "",
        "## Gates",
        "",
        "| Gate | Result | Duration (s) |",
        "|---|---:|---:|",
    ]
    for check in report["checks"]:
        lines.append(
            f"| {check['name']} | **{check['status']}** | "
            f"{check.get('duration_s', '-')} |"
        )
    if report["failed_checks"]:
        lines.extend([
            "",
            "## Failed gates",
            "",
            *[f"- {name}" for name in report["failed_checks"]],
        ])
    lines.extend([
        "",
        "> Static PASS proves repository contracts and tests only. A formal CARLA "
        "run must use --require-live and retain its runtime evidence.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="skip full pytest")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--require-live", action="store_true")
    parser.add_argument("--qwen-url", default="http://127.0.0.1:18000")
    parser.add_argument("--carla-host", default="127.0.0.1")
    parser.add_argument("--carla-port", type=int, default=2000)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/review/main_optimization_readiness.json"),
    )
    args = parser.parse_args()
    report = build_report(
        allow_dirty=args.allow_dirty,
        quick=args.quick,
        require_live=args.require_live,
        qwen_url=args.qwen_url,
        carla_host=args.carla_host,
        carla_port=args.carla_port,
    )
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown = output.with_suffix(".md")
    markdown.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"markdown_report={markdown}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
