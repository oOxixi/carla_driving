from __future__ import annotations

from car_control_A.maneuver_fsm import ManeuverFSM
from runtime.plan_compiler import CompiledManeuverPlan, CompiledPlanStep


def _step(
    step_id="turn", behavior="TURN_RIGHT", *, completion=None,
    preconditions=("PERCEPTION_FRESH", "NO_EMERGENCY_RISK"), timeout_s=5.0,
    on_failure="SAFE_STOP",
):
    return CompiledPlanStep(
        step_id=step_id,
        source_step_id=step_id,
        behavior=behavior,
        target={},
        preconditions=preconditions,
        completion=completion or {
            "type": "JUNCTION_EXITED", "value": None, "lane": None, "hold_frames": 2,
        },
        timeout_s=timeout_s,
        on_failure=on_failure,
    )


def _plan(*steps, replans=()):
    return CompiledManeuverPlan(
        command_id="cmd-1", plan_id="plan-1", steps=tuple(steps or (_step(),)),
        replan_conditions=tuple(replans), valid_until_ns=10_000_000_000,
    )


def _snapshot(**updates):
    state = {
        "perception_fresh": True,
        "no_emergency_risk": True,
        "risk_level": "LOW",
        "junction_exited": False,
        "speed_mps": 2.0,
    }
    state.update(updates)
    return state


def test_turn_completes_only_after_deterministic_hold_frames():
    fsm = ManeuverFSM()
    started = fsm.start(_plan(), now_s=0.0)
    assert started.state == "TURNING"
    assert [event.event_type for event in started.events] == [
        "qwen_plan_started", "qwen_step_started",
    ]
    assert fsm.update(_snapshot(junction_exited=True), now_s=1.0).terminal is False
    terminal = fsm.update(_snapshot(junction_exited=True), now_s=1.05)
    assert terminal.state == "SUCCEEDED"
    assert terminal.terminal is True
    assert [event.event_type for event in terminal.events] == [
        "qwen_step_completed", "qwen_terminal",
    ]
    assert fsm.update(_snapshot(junction_exited=True), now_s=1.1).events == ()


def test_lane_change_waits_for_gap_and_times_out_to_safe_stop():
    lane = _step(
        behavior="CHANGE_LANE_LEFT",
        preconditions=("PERCEPTION_FRESH", "LEFT_GAP_SAFE"),
        completion={
            "type": "LANE_CENTERED", "value": None,
            "lane": "LEFT_ADJACENT", "hold_frames": 2,
        },
        timeout_s=1.0,
    )
    fsm = ManeuverFSM()
    fsm.start(_plan(lane), now_s=0.0)
    waiting = fsm.update(_snapshot(left_gap_safe=False), now_s=0.5)
    assert waiting.state == "WAIT_SAFE_GAP"
    assert waiting.safe_behavior == "SLOW_DOWN"
    timeout = fsm.update(_snapshot(left_gap_safe=False), now_s=1.1)
    assert timeout.state == "FAILED"
    assert timeout.safe_behavior == "STOP"


def test_lane_change_entry_preconditions_are_latched_during_transition():
    lane = _step(
        behavior="CHANGE_LANE_LEFT",
        preconditions=("PERCEPTION_FRESH", "LEFT_LANE_EXISTS", "LEFT_GAP_SAFE"),
        completion={
            "type": "LANE_CENTERED", "value": None,
            "lane": "LEFT_ADJACENT", "hold_frames": 2,
        },
    )
    fsm = ManeuverFSM()
    fsm.start(_plan(lane), now_s=0.0)
    assert not fsm.update(_snapshot(
        left_lane_exists=True, left_gap_safe=True,
        lane="CURRENT", lateral_error_m=0.0,
    ), now_s=0.1).terminal

    # Once the vehicle is in the target lane, LEFT_LANE_EXISTS is relative to
    # the new lane and may be false; it must not invalidate an active step.
    assert not fsm.update(_snapshot(
        left_lane_exists=False, left_gap_safe=False,
        lane="LEFT_ADJACENT", lateral_error_m=0.1,
    ), now_s=0.2).terminal
    terminal = fsm.update(_snapshot(
        left_lane_exists=False, left_gap_safe=False,
        lane="LEFT_ADJACENT", lateral_error_m=0.1,
    ), now_s=0.25)
    assert terminal.state == "SUCCEEDED"


def test_pass_target_can_start_after_a_previously_seen_target_leaves_view():
    passed = _step(
        behavior="PASS_TARGET",
        preconditions=("PERCEPTION_FRESH", "TARGET_VISIBLE"),
        completion={
            "type": "TARGET_PASSED", "value": None,
            "lane": "LEFT_ADJACENT", "hold_frames": 2,
        },
    )
    fsm = ManeuverFSM()
    fsm.start(_plan(passed), now_s=0.0)
    first = fsm.update(_snapshot(
        target_visible=False, target_seen=True, target_passed=True,
    ), now_s=0.1)
    assert not first.terminal
    terminal = fsm.update(_snapshot(
        target_visible=False, target_seen=True, target_passed=True,
    ), now_s=0.15)
    assert terminal.state == "SUCCEEDED"


def test_emergency_preempts_plan_once():
    fsm = ManeuverFSM()
    fsm.start(_plan(), now_s=0.0)
    first = fsm.update(_snapshot(emergency=True), now_s=0.1)
    assert first.state == "SAFETY_OVERRIDE"
    assert first.safe_behavior == "EMERGENCY_STOP"
    assert len(first.events) == 1
    second = fsm.update(_snapshot(emergency=True), now_s=0.2)
    assert second.events == ()


def test_replan_cooldown_and_limit_prevent_call_storm():
    fsm = ManeuverFSM(replan_cooldown_s=2.0, max_replans_per_command=2)
    fsm.start(_plan(replans=("TARGET_LOST",)), now_s=0.0)
    first = fsm.update(_snapshot(target_lost=True), now_s=1.0)
    assert first.state == "REPLAN_PENDING"
    assert first.events[0].event_type == "qwen_replan_triggered"
    suppressed = fsm.request_replan("TARGET_LOST", now_s=1.5)
    assert suppressed.events[0].event_type == "qwen_replan_suppressed"
    second = fsm.request_replan("TARGET_LOST", now_s=3.1)
    assert second.events[0].event_type == "qwen_replan_triggered"
    exhausted = fsm.request_replan("TARGET_LOST", now_s=5.2)
    assert exhausted.state == "FAILED"
    assert exhausted.safe_behavior == "STOP"


def test_new_plan_supersedes_old_plan_with_explicit_terminal():
    fsm = ManeuverFSM()
    fsm.start(_plan(), now_s=0.0)
    replacement = CompiledManeuverPlan(
        command_id="cmd-2", plan_id="plan-2", steps=(_step("stop", "STOP", completion={
            "type": "STOPPED", "value": None, "lane": None, "hold_frames": 1,
        }),), replan_conditions=(), valid_until_ns=20_000_000_000,
    )
    update = fsm.start(replacement, now_s=0.2)
    assert update.events[0].state == "SUPERSEDED"
    assert update.events[0].command_id == "cmd-1"
    assert update.events[-1].command_id == "cmd-2"
