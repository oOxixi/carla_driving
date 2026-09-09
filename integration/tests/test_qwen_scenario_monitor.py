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
