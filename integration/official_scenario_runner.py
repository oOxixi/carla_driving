"""Pinned CARLA ScenarioRunner 0.9.16 process boundary.

This module does not vendor ScenarioRunner and does not compete with its world
clock.  It verifies the external checkout and builds one explicit subprocess
command.  The external process owns scenario orchestration; vehicle-side agents
can be supplied with ``agent_path`` and ``agent_config``.
"""
from __future__ import annotations

from dataclasses import dataclass
import subprocess
import sys
from pathlib import Path
from typing import Sequence


SCENARIO_RUNNER_TAG = "v0.9.16"
SCENARIO_RUNNER_COMMIT = "94ff3b8af752bad2b9d464ad5105868906aa34c0"


@dataclass(frozen=True, slots=True)
class ScenarioRunnerInvocation:
    root: Path
    scenario: str
    host: str = "127.0.0.1"
    port: int = 2000
    timeout_s: float = 60.0
    python_executable: str = sys.executable
    agent_path: Path | None = None
    agent_config: Path | None = None
    sync: bool = True
    reload_world: bool = False
    output: bool = True
    json_output: bool = True
    extra_args: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.scenario.strip():
            raise ValueError("scenario must be non-empty")
        if not self.host.strip() or not 1 <= self.port <= 65535:
            raise ValueError("host must be non-empty and port must be in 1..65535")
        if self.timeout_s <= 0.0:
            raise ValueError("timeout_s must be positive")
        if self.agent_config is not None and self.agent_path is None:
            raise ValueError("agent_config requires agent_path")


def verify_checkout(root: str | Path) -> str:
    """Fail unless ``root`` is the exact pinned ScenarioRunner checkout."""
    checkout = Path(root).resolve()
    entry = checkout / "scenario_runner.py"
    if not entry.is_file():
        raise FileNotFoundError(
            f"ScenarioRunner entry not found: {entry}. Run scripts/fetch_scenario_runner.ps1 first."
        )
    completed = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    commit = completed.stdout.strip().lower()
    if commit != SCENARIO_RUNNER_COMMIT:
        raise RuntimeError(
            f"ScenarioRunner commit mismatch: expected {SCENARIO_RUNNER_COMMIT}, got {commit or '<empty>'}"
        )
    return commit


def build_command(invocation: ScenarioRunnerInvocation, *, verify: bool = True) -> list[str]:
    root = invocation.root.resolve()
    if verify:
        verify_checkout(root)
    command = [
        invocation.python_executable,
        str(root / "scenario_runner.py"),
        "--host", invocation.host,
        "--port", str(invocation.port),
        "--timeout", str(invocation.timeout_s),
        "--scenario", invocation.scenario,
    ]
    if invocation.sync:
        command.append("--sync")
    if invocation.reload_world:
        command.append("--reloadWorld")
    if invocation.output:
        command.append("--output")
    if invocation.json_output:
        command.append("--json")
    if invocation.agent_path is not None:
        command.extend(("--agent", str(invocation.agent_path.resolve())))
    if invocation.agent_config is not None:
        command.extend(("--agentConfig", str(invocation.agent_config.resolve())))
    command.extend(invocation.extra_args)
    return command


def run(invocation: ScenarioRunnerInvocation, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run the verified external orchestrator without using a shell."""
    return subprocess.run(build_command(invocation), cwd=invocation.root, check=check, text=True)


__all__ = [
    "SCENARIO_RUNNER_TAG",
    "SCENARIO_RUNNER_COMMIT",
    "ScenarioRunnerInvocation",
    "verify_checkout",
    "build_command",
    "run",
]
