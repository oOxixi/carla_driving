from pathlib import Path

import pytest

from integration.official_scenario_runner import ScenarioRunnerInvocation, build_command
import integration.scenario_runner_agent as official_agent_module


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


def test_builds_official_agent_handoff_for_arbitrary_scenario(tmp_path: Path) -> None:
    root = tmp_path / "scenario_runner"
    agent = tmp_path / "private_agent.py"
    config = tmp_path / "agent.json"
    invocation = ScenarioRunnerInvocation(
        root=root,
        scenario="OrganizerPrivateScenario_42",
        python_executable="python",
        agent_path=agent,
        agent_config=config,
    )

    command = build_command(invocation, verify=False)

    assert command[command.index("--scenario") + 1] == "OrganizerPrivateScenario_42"
    assert command[command.index("--agent") + 1] == str(agent.resolve())
    assert command[command.index("--agentConfig") + 1] == str(config.resolve())


def test_agent_class_name_matches_pinned_scenario_runner_loader() -> None:
    module_name = Path(official_agent_module.__file__).stem
    class_name = module_name.title().replace("_", "")

    assert class_name == "ScenarioRunnerAgent"
    assert getattr(official_agent_module, class_name) is official_agent_module.ScenarioRunnerAgent
