from challenge.dataset.collector import (
    classify_sample,
    classify_training_role,
)


def _request(risk="LOW"):
    return {
        "scene_summary": {
            "risk_level": risk,
        },
    }


def _plan(*behaviors):
    return {
        "steps": [
            {"behavior": behavior}
            for behavior in behaviors
        ],
    }


def _closed_loop(**overrides):
    base = {
        "available": True,
        "command_terminal_status": "SUCCEEDED",
        "plan_terminal_state": "SUCCEEDED",
        "plan_terminal_reason": "PLAN_COMPLETE",
        "collision_count": 0,
        "route_deviation_count": 0,
        "red_light_violation_count": 0,
        "scenario_acceptance_passed": True,
        "safety_override_observed": False,
        "safety_override_frames": 0,
        "run_status": "SUCCEEDED",
    }
    base.update(overrides)
    return base


def test_transient_safety_override_does_not_make_semantic_safety_critical():
    sample_class = classify_sample(
        _request("LOW"),
        _plan("TURN_RIGHT", "SET_SPEED"),
        _closed_loop(
            safety_override_observed=True,
            safety_override_frames=3,
        ),
    )

    assert sample_class == {
        "primary": "COMPLEX",
        "safety_critical": False,
    }


def test_outer_run_failure_can_still_be_positive_when_teacher_plan_succeeds():
    role, reasons = classify_training_role(
        True,
        _closed_loop(
            run_status="FAILED",
            command_terminal_status="SUCCEEDED",
            plan_terminal_state="SUCCEEDED",
            plan_terminal_reason="PLAN_COMPLETE",
            scenario_acceptance_passed=True,
        ),
    )

    assert role == "POSITIVE"
    assert reasons == []


def test_runtime_ended_teacher_execution_is_hard_negative():
    role, reasons = classify_training_role(
        True,
        _closed_loop(
            run_status="FAILED",
            command_terminal_status="FAILED",
            plan_terminal_state="FAILED",
            plan_terminal_reason="RUNTIME_ENDED",
        ),
    )

    assert role == "HARD_NEGATIVE"
    assert reasons == [
        "TEACHER_EXECUTION_NOT_SUCCEEDED:RUNTIME_ENDED"
    ]


def test_safety_override_terminal_is_hard_negative():
    role, reasons = classify_training_role(
        True,
        _closed_loop(
            run_status="FAILED",
            command_terminal_status="SAFETY_OVERRIDE",
            plan_terminal_state="SAFETY_OVERRIDE",
            plan_terminal_reason="EMERGENCY_FRONT_OBSTACLE_TOO_CLOSE",
            safety_override_observed=True,
            safety_override_frames=609,
        ),
    )

    assert role == "HARD_NEGATIVE"
    assert reasons == ["SAFETY_OVERRIDE_TERMINAL"]


def test_visual_avoid_return_is_semantic_safety_critical():
    sample_class = classify_sample(
        _request("LOW"),
        _plan("AVOID_OBSTACLE", "RETURN_TO_LANE"),
        _closed_loop(),
    )

    assert sample_class == {
        "primary": "SAFETY_CRITICAL",
        "safety_critical": True,
    }


def test_structurally_invalid_sample_is_rejected():
    role, reasons = classify_training_role(
        False,
        _closed_loop(),
    )

    assert role == "REJECTED"
    assert reasons == []
