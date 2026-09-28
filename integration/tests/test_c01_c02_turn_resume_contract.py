from pathlib import Path

from integration.scenario_execution import (
    ScenarioSpec,
    scenario_trigger_satisfied,
)


ROOT = Path(__file__).resolve().parents[2]

C01 = (
    ROOT
    / "scenarios"
    / "targeted_collection"
    / "batch_a"
    / "TC_C01_true_3step_left.json"
)

C02 = (
    ROOT
    / "scenarios"
    / "targeted_collection"
    / "batch_a"
    / "TC_C02_yield_left_3step.json"
)


def test_c01_declares_three_step_chain():
    spec = ScenarioSpec.load(C01)

    assert len(spec.commands) == 3
    assert [
        str(command.envelope["intent"]).upper()
        for command in spec.commands
    ] == [
        "KEEP_LANE",
        "TURN_LEFT",
        "SET_SPEED",
    ]


def test_c02_declares_three_step_chain():
    spec = ScenarioSpec.load(C02)

    assert len(spec.commands) == 3
    assert [
        str(command.envelope["intent"]).upper()
        for command in spec.commands
    ] == [
        "YIELD",
        "TURN_LEFT",
        "SET_SPEED",
    ]


def _assert_resume_waits_for_turn_success(spec: ScenarioSpec):
    turn = spec.commands[1]
    resume = spec.commands[2]

    assert turn.phase_id is not None
    assert resume.trigger is not None

    # TURN terminal but not successful: SET_SPEED must stay blocked.
    assert scenario_trigger_satisfied(
        resume.trigger,
        elapsed_s=60.0,
        context={
            "terminal_phase_ids": (
                spec.commands[0].phase_id,
                turn.phase_id,
            ),
            "completed_phase_ids": (
                spec.commands[0].phase_id,
            ),
            "route_progress_m": 100.0,
        },
    ) is False

    # Only successful TURN completion may unlock SET_SPEED.
    assert scenario_trigger_satisfied(
        resume.trigger,
        elapsed_s=60.0,
        context={
            "terminal_phase_ids": (
                spec.commands[0].phase_id,
                turn.phase_id,
            ),
            "completed_phase_ids": (
                spec.commands[0].phase_id,
                turn.phase_id,
            ),
            "route_progress_m": 100.0,
        },
    ) is True


def test_c01_resume_speed_requires_turn_success():
    _assert_resume_waits_for_turn_success(
        ScenarioSpec.load(C01)
    )


def test_c02_resume_speed_requires_turn_success():
    _assert_resume_waits_for_turn_success(
        ScenarioSpec.load(C02)
    )


def test_c02_turn_resumes_immediately_after_successful_yield() -> None:
    root = Path(__file__).resolve().parents[2] / "scenarios"
    spec = ScenarioSpec.load(
        root
        / "targeted_collection"
        / "batch_a"
        / "TC_C02_yield_left_3step.json"
    )

    assert [item.phase_id for item in spec.commands] == [
        "C2_YIELD",
        "C2_TURN",
        "C2_SPEED",
    ]

    assert spec.commands[1].trigger == {
        "type": "previous_command_succeeded",
        "phase_id": "C2_YIELD",
    }
