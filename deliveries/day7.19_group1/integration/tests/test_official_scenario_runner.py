from pathlib import Path

import pytest

from integration.official_scenario_runner import ScenarioRunnerInvocation, build_command


def test_builds_exact_scenario_runner_command_without_shell(tmp_path: Path) -> None:
    root = tmp_path / "scenario_runner"
    invocation = ScenarioRunnerInvocation(
        root=root,
        scenario="FollowLeadingVehicle_1",
        host="127.0.0.1",
        port=2000,
        timeout_s=60.0,
        python_executable="python",
        sync=True,
        reload_world=True,
    )
    command = build_command(invocation, verify=False)
    assert command[:2] == ["python", str(root.resolve() / "scenario_runner.py")]
    assert command[command.index("--scenario") + 1] == "FollowLeadingVehicle_1"
    assert "--sync" in command
    assert "--reloadWorld" in command
    assert "--output" in command and "--json" in command


def test_agent_config_requires_agent() -> None:
    with pytest.raises(ValueError, match="agent_config requires agent_path"):
        ScenarioRunnerInvocation(Path("external/scenario_runner"), "Example", agent_config=Path("agent.json"))
