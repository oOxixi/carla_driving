from __future__ import annotations

import pytest

from integration.qwen_scenario_monitor import QwenScenarioMonitor


def _expected(**updates):
    expected = {
        "route": "QWEN_PLAN",
        "min_calls": 1,
        "max_calls": 2,
        "expected_behaviors": ["SLOW_DOWN", "TURN_RIGHT"],
        "expected_terminal": "SUCCEEDED",
        "allowed_replans": 1,
        "forbidden_low_level_fields": True,
    }
    expected.update(updates)
    return expected


def test_monitor_accepts_complete_auditable_contract():
    monitor = QwenScenarioMonitor(_expected())
    monitor.record_routing("QWEN_PLAN", qwen_submitted=True)
    monitor.record_plan({
        "schema_version": "2.0",
        "steps": [{"behavior": "SLOW_DOWN"}, {"behavior": "TURN_RIGHT"}],
    })
    monitor.record_terminal("SUCCEEDED")
    report = monitor.finalize()
    assert report.passed is True
    assert all(report.checks.values())


def test_monitor_reports_call_behavior_terminal_and_boundary_failures():
    monitor = QwenScenarioMonitor(_expected())
    monitor.record_routing("QWEN_PLAN", qwen_submitted=False)
    monitor.record_plan({
        "schema_version": "2.0",
        "steps": [{"behavior": "TURN_RIGHT", "steer": 0.8}],
    })
    monitor.record_terminal("FAILED")
    report = monitor.finalize()
    assert report.passed is False
    assert set(report.failures) == {
        "call_count", "behaviors", "terminal", "low_level_boundary",
    }


def test_monitor_enforces_replan_limit_without_call_storm():
    monitor = QwenScenarioMonitor(_expected(expected_behaviors=[]))
    monitor.record_routing("QWEN_PLAN", qwen_submitted=True)
    monitor.record_replan()
    monitor.record_replan()
    monitor.record_terminal("SUCCEEDED")
    assert monitor.finalize().checks["replans"] is False


def test_monitor_rejects_obsolete_local_route():
    with pytest.raises(ValueError, match="route is invalid"):
        QwenScenarioMonitor(_expected(route="LOCAL_BYPASS"))


def test_monitor_does_not_accept_internal_wait_command_as_user_terminal():
    monitor = QwenScenarioMonitor(_expected(expected_behaviors=[]))
    monitor.record_routing(
        "QWEN_PLAN", qwen_submitted=True, command_id="user-command",
    )
    monitor.record_terminal("SUCCEEDED", command_id="qwen-wait-internal")
    report = monitor.finalize()
    assert report.checks["terminal"] is False
    assert report.checks["single_terminal"] is False


def test_monitor_rejects_duplicate_terminals_for_one_user_command():
    monitor = QwenScenarioMonitor(_expected(expected_behaviors=[]))
    monitor.record_routing(
        "QWEN_PLAN", qwen_submitted=True, command_id="user-command",
    )
    monitor.record_terminal("FAILED", command_id="user-command")
    monitor.record_terminal("SUCCEEDED", command_id="user-command")
    assert monitor.finalize().checks["single_terminal"] is False


def test_monitor_requires_configured_terminal_reason_prefix():
    monitor = QwenScenarioMonitor(_expected(
        expected_behaviors=[],
        expected_terminal="SAFETY_OVERRIDE",
        expected_terminal_reason_prefix="C_FRONT_PEDESTRIAN_",
    ))
    monitor.record_routing(
        "QWEN_PLAN", qwen_submitted=True, command_id="user-command",
    )
    monitor.record_terminal(
        "SAFETY_OVERRIDE",
        command_id="user-command",
        reason_code="WATCHDOG_ALERT",
    )
    assert monitor.finalize().checks["terminal_reason"] is False

    semantic = QwenScenarioMonitor(_expected(
        expected_behaviors=[],
        expected_terminal="SAFETY_OVERRIDE",
        expected_terminal_reason_prefix="C_FRONT_PEDESTRIAN_",
    ))
    semantic.record_routing(
        "QWEN_PLAN", qwen_submitted=True, command_id="user-command",
    )
    semantic.record_terminal(
        "SAFETY_OVERRIDE",
        command_id="user-command",
        reason_code="C_FRONT_PEDESTRIAN_VRU_SHORT_FRONT_DISTANCE",
    )
    assert semantic.finalize().passed is True


def test_monitor_accepts_every_command_on_qwen_route():
    monitor = QwenScenarioMonitor(_expected(
        route="QWEN_PLAN",
        min_calls=4,
        max_calls=4,
        expected_behaviors=["KEEP_LANE", "EMERGENCY_STOP"],
        allowed_replans=0,
    ))
    for command_id in ("normal-1", "normal-2", "emergency-1", "emergency-2"):
        monitor.record_routing(
            "QWEN_PLAN", qwen_submitted=True, command_id=command_id,
        )
    monitor.record_behavior("KEEP_LANE")
    monitor.record_behavior("EMERGENCY_STOP")
    for command_id in ("normal-1", "normal-2", "emergency-1", "emergency-2"):
        monitor.record_terminal("SUCCEEDED", command_id=command_id)

    report = monitor.finalize()

    assert report.passed is True
    assert report.checks["route"] is True


@pytest.mark.parametrize("behavior,target,actual,plan,passes", [
    ("SET_SPEED", 20, 20, "p", True),
    ("SET_SPEED", 20, 18, "p", True),
    ("SET_SPEED", 10.26, 10.26, "p", False),
    ("SET_SPEED", 20, 16, "p", False),
    ("SET_SPEED", 20, None, "p", False),
    ("SET_SPEED", 20, float("nan"), "p", False),
    ("SET_SPEED", 20, 20, "other-plan", False),
    ("KEEP_LANE", 20, 20, "p", False),
])
def test_final_speed_requires_target_and_vehicle_evidence_from_successful_plan(behavior, target, actual, plan, passes):
    monitor = QwenScenarioMonitor(_expected(max_calls=1, expected_behaviors=["CHANGE_LANE_LEFT", "SET_SPEED"],
        final_set_speed={"kph": 20, "tolerance_kph": 2}))
    monitor.record_routing("QWEN_PLAN", qwen_submitted=True, command_id="c")
    monitor.record_behavior("CHANGE_LANE_LEFT")
    monitor.record_behavior("SET_SPEED")
    monitor.record_step_completion("c", "p", "step-1", "CHANGE_LANE_LEFT", 20/3.6, 20/3.6)
    monitor.record_step_completion("c", plan, "step-2", behavior, target/3.6, None if actual is None else actual/3.6)
    monitor.record_terminal("SUCCEEDED", command_id="c", plan_id="p")
    assert monitor.finalize().passed is passes


@pytest.mark.parametrize("speed", [None, {}, {"kph": True, "tolerance_kph": 2}, {"kph": 20, "tolerance_kph": -1}])
def test_monitor_rejects_malformed_final_speed_contract(speed):
    with pytest.raises(ValueError, match="final_set_speed"):
        QwenScenarioMonitor(_expected(max_calls=1, final_set_speed=speed))


def test_runner_records_same_step_speed_before_terminal():
    from car_control_A.maneuver_fsm import ManeuverEvent, ManeuverUpdate
    from integration.carla_runner import _record_maneuver_update
    from runtime.plan_compiler import CompiledPlanStep

    monitor = QwenScenarioMonitor(_expected(max_calls=1, expected_behaviors=["SET_SPEED"],
        final_set_speed={"kph": 20, "tolerance_kph": 2}))
    monitor.record_routing("QWEN_PLAN", qwen_submitted=True, command_id="c")
    monitor.record_behavior("SET_SPEED")
    step = CompiledPlanStep("step-2", "step-2", "SET_SPEED", {"target_speed_mps": 20/3.6},
        (), {"type": "SPEED_REACHED"}, 10.0, "STOP")
    events = (
        ManeuverEvent("qwen_step_completed", "c", "p", "step-2", "PLAN_EXECUTING", "COMPLETION_HELD", 1.0),
        ManeuverEvent("qwen_terminal", "c", "p", None, "SUCCEEDED", "PLAN_COMPLETE", 1.0),
    )
    _record_maneuver_update(ManeuverUpdate("SUCCEEDED", None, events, None, True),
        monitor=monitor, recorder=None, completed_step=step, actual_speed_mps=19/3.6)
    report = monitor.finalize()
    assert report.passed
    assert report.observed["final_set_speed"]["observed"]["actual_kph"] == pytest.approx(19)
