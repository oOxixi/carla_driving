"""Drive one CARLA scenario for `carla_measurement.ps1`.

Two runners are supported because the repository has two, and they are good at
different things:

* ``repo`` (default): ``python -m integration.carla_runner --scenario-file
  scenarios/.../X.json``.  This is the path B3's existing CARLA evidence was
  produced with, and the scenario file carries the map, delta and frame count.
* ``official``: the vendored CARLA ScenarioRunner via
  ``integration.official_scenario_runner``.  It is the reference implementation
  but needs its own checkout layout (``agents`` etc.), so it stays opt-in.

The script records the exact command it ran, so a later reader can repeat it
without guessing which of the two was used.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def resolve_scenario_file(repo: Path, scenario: str) -> Path:
    """Accept a direct path, a `scenarios/...` relative path, or a bare name."""
    candidates: list[Path] = []
    raw = Path(scenario)
    if raw.is_absolute() or raw.suffix == ".json":
        candidates.append(raw if raw.is_absolute() else repo / raw)
    else:
        candidates.append(repo / "scenarios" / "smoke" / f"{scenario}.json")
        candidates.extend(sorted((repo / "scenarios").rglob(f"{scenario}.json")))
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise SystemExit(f"scenario file not found for {scenario!r} under {repo / 'scenarios'}")


def run_repo_runner(args: argparse.Namespace, repo: Path, scenario_file: Path, log_dir: Path) -> dict:
    command = [
        sys.executable,
        "-m",
        "integration.carla_runner",
        "--scenario-file",
        str(scenario_file),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--timeout-s",
        str(args.timeout_s),
        "--log-dir",
        str(log_dir),
    ]
    if args.realtime:
        command.append("--realtime")
    if args.extra:
        command.extend(args.extra)
    completed = subprocess.run(command, cwd=repo, text=True, capture_output=True)
    tail = (completed.stdout or "")[-4000:]
    if tail:
        print(tail)
    if completed.stderr:
        print(completed.stderr[-2000:], file=sys.stderr)
    return {
        "runner": "repo",
        "command": command,
        "returncode": completed.returncode,
        "stdout_tail": tail,
        "stderr_tail": (completed.stderr or "")[-2000:],
        "scenario_file": str(scenario_file),
        "log_dir": str(log_dir),
    }


def run_official_runner(args: argparse.Namespace, repo: Path, scenario_file: Path) -> dict:
    sys.path.insert(0, str(repo))
    from integration.official_scenario_runner import (  # noqa: PLC0415
        ScenarioRunnerInvocation,
        build_command,
        run,
    )

    scenario_root = Path(args.scenario_root or (repo / "external" / "scenario_runner")).resolve()
    agent_path = repo / "integration" / "scenario_runner_agent.py"
    invocation = ScenarioRunnerInvocation(
        root=scenario_root,
        scenario=scenario_file.name,
        host=args.host,
        port=args.port,
        timeout_s=args.timeout_s,
        python_executable=sys.executable,
        agent_path=agent_path,
        agent_config=Path(args.agent_config) if args.agent_config else None,
    )
    command = build_command(invocation)
    completed = run(invocation, check=False)
    return {
        "runner": "official",
        "command": command,
        "returncode": completed.returncode,
        "scenario_file": str(scenario_file),
        "scenario_root": str(scenario_root),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--runner", choices=("repo", "official"), default="repo")
    parser.add_argument("--scenario-root", default=None)
    parser.add_argument("--agent-config", default=None)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2000)
    parser.add_argument("--timeout-s", type=float, default=180.0)
    parser.add_argument("--log-dir", default=None)
    parser.add_argument("--realtime", action="store_true")
    parser.add_argument("--summary-out", default=None)
    parser.add_argument(
        "--extra",
        nargs=argparse.REMAINDER,
        default=[],
        help=(
            "everything after this flag is passed to `integration.carla_runner` "
            "verbatim (must be last, so a value starting with -- is not read as an option)"
        ),
    )
    args = parser.parse_args(argv)
    args.extra = [str(item) for item in (args.extra or [])]

    repo = Path(args.repo).resolve()
    scenario_file = resolve_scenario_file(repo, args.scenario)
    log_dir = Path(args.log_dir) if args.log_dir else (repo / "artifacts" / "logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    if args.runner == "repo":
        result = run_repo_runner(args, repo, scenario_file, log_dir)
    else:
        result = run_official_runner(args, repo, scenario_file)

    result["scenario"] = args.scenario
    result["status"] = "SUCCEEDED" if result["returncode"] == 0 else "FAILED"
    result["python"] = sys.executable
    _emit(result, args.summary_out)
    return int(result["returncode"])


def _emit(summary: dict, summary_out: str | None) -> None:
    text = json.dumps(summary, ensure_ascii=False, indent=2, default=str)
    if summary_out:
        target = Path(summary_out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    raise SystemExit(main())
