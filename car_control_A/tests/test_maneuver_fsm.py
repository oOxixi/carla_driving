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


def test_speed_completion_accepts_closed_loop_ripple_near_30_kph():
    speed = _step(
        behavior="SET_SPEED",
        completion={
            "type": "SPEED_REACHED", "value": 8.333333333333334,
            "lane": None, "hold_frames": 3,
        },
        timeout_s=8.0,
    )
    fsm = ManeuverFSM()
    fsm.start(_plan(speed), now_s=0.0)

    assert not fsm.update(_snapshot(speed_mps=8.04), now_s=7.7).terminal
    assert not fsm.update(_snapshot(speed_mps=8.02), now_s=7.75).terminal
    terminal = fsm.update(_snapshot(speed_mps=8.04), now_s=7.8)

    assert terminal.state == "SUCCEEDED"


def test_set_speed_20_completes_within_acceptance_tolerance_before_timeout():
    speed = _step(
        behavior="SET_SPEED",
        completion={
            "type": "SPEED_REACHED", "value": 20.0 / 3.6,
            "lane": None, "hold_frames": 3,
        },
        timeout_s=8.0,
    )
    fsm = ManeuverFSM()
    fsm.start(_plan(speed), now_s=0.0)

    assert not fsm.update(_snapshot(speed_mps=5.00), now_s=7.90).terminal
    assert not fsm.update(_snapshot(speed_mps=5.05), now_s=7.95).terminal
    terminal = fsm.update(_snapshot(speed_mps=5.16), now_s=8.00)

    assert terminal.state == "SUCCEEDED"


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


def test_yield_emergency_resets_clear_window_without_failing_plan():
    yielding = _step(
        behavior="YIELD",
        preconditions=("PERCEPTION_FRESH",),
        completion={
            "type": "HOLD_FRAMES", "value": None,
            "lane": None, "hold_frames": 2,
        },
    )
    fsm = ManeuverFSM()
    fsm.start(_plan(yielding), now_s=0.0)

    assert not fsm.update(_snapshot(
        hold_condition=True,
    ), now_s=0.1).terminal
    emergency = fsm.update(_snapshot(emergency=True), now_s=0.15)
    assert not emergency.terminal
    assert emergency.safe_behavior == "EMERGENCY_STOP"
    assert not fsm.update(_snapshot(hold_condition=True), now_s=0.2).terminal
    terminal = fsm.update(_snapshot(
        hold_condition=True,
    ), now_s=0.25)
    assert terminal.state == "SUCCEEDED"


def test_conditional_slow_down_survives_emergency_and_restarts_clear_window():
    slowing = _step(
        behavior="SLOW_DOWN",
        preconditions=("PERCEPTION_FRESH",),
        completion={
            "type": "SPEED_BELOW", "value": 8.33,
            "lane": None, "hold_frames": 2,
        },
    )
    fsm = ManeuverFSM()
    fsm.start(_plan(slowing), now_s=0.0)

    assert not fsm.update(_snapshot(speed_mps=8.0), now_s=0.1).terminal
    emergency = fsm.update(_snapshot(
        speed_mps=0.0, emergency=True,
    ), now_s=0.15)
    assert not emergency.terminal
    assert emergency.safe_behavior == "EMERGENCY_STOP"
    assert not fsm.update(_snapshot(speed_mps=8.0), now_s=0.2).terminal
    terminal = fsm.update(_snapshot(speed_mps=8.0), now_s=0.25)
    assert terminal.state == "SUCCEEDED"


def test_conditional_slow_down_waits_for_speed_duration_and_target_clearance():
    slowing = CompiledPlanStep(
        step_id="slow-clear", source_step_id="slow-clear",
        behavior="SLOW_DOWN",
        target={"target_speed_mps": 8.33, "target_id": "bus_at_stop"},
        preconditions=("PERCEPTION_FRESH",),
        completion={
            "type": "TARGET_PASSED", "value": 6.0,
            "lane": None, "hold_frames": 3,
        },
        timeout_s=35.0, on_failure="SAFE_STOP",
    )
    fsm = ManeuverFSM()
    fsm.start(_plan(slowing), now_s=0.0)

    # Duration and reduced speed alone must never advance the plan while the
    # named actor is still ahead.  Repeating this for the full hold window
    # catches accidental replacement (rather than conjunction) of the
    # TARGET_PASSED predicate.
    for now_s in (6.0, 6.1, 6.2, 6.3):
        assert not fsm.update(_snapshot(
            speed_mps=8.0, target_passed=False,
        ), now_s=now_s).terminal
    assert not fsm.update(_snapshot(
        speed_mps=9.1, target_passed=True,
    ), now_s=6.4).terminal
    assert not fsm.update(_snapshot(
        speed_mps=8.0, target_passed=True,
    ), now_s=6.5).terminal
    assert not fsm.update(_snapshot(
        speed_mps=8.0, target_passed=True,
    ), now_s=6.55).terminal
    terminal = fsm.update(_snapshot(
        speed_mps=8.0, target_passed=True,
    ), now_s=6.6)
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
