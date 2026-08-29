from __future__ import annotations

import pytest

from runtime.complexity_router import CONFIRM_SAFE, FAST_LOCAL, QWEN_PLAN, ComplexityRouter


SIMPLE_CASES = (
    ("启动", "START", {}),
    ("请起步", "START", {}),
    ("Start driving", "START", {}),
    ("停车", "STOP", {}),
    ("现在停下", "STOP", {}),
    ("Stop now", "STOP", {}),
    ("紧急停车", "EMERGENCY_STOP", {}),
    ("立即刹车", "EMERGENCY_STOP", {}),
    ("Emergency stop", "EMERGENCY_STOP", {}),
    ("保持当前车道", "KEEP_LANE", {}),
    ("继续直行", "KEEP_LANE", {}),
    ("Keep the lane", "KEEP_LANE", {}),
    ("保持二十公里每小时", "SET_SPEED", {"target_speed_mps": 5.56}),
    ("速度调到二十", "SET_SPEED", {"target_speed_mps": 5.56}),
    ("以五米每秒行驶", "SET_SPEED", {"target_speed_mps": 5.0}),
    ("Set speed to five m/s", "SET_SPEED", {"target_speed_mps": 5.0}),
    ("减速到三米每秒", "SLOW_DOWN", {"target_speed_mps": 3.0}),
    ("请减速", "SLOW_DOWN", {}),
    ("Slow down", "SLOW_DOWN", {}),
    ("保持车道行驶", "KEEP_LANE", {}),
)

COMPLEX_CASES = (
    ("前方路口右转", "TURN", {"direction": "RIGHT"}),
    ("前方第二个路口左转", "TURN", {"direction": "LEFT"}),
    ("右转后进入左侧车道", "TURN", {"direction": "RIGHT"}),
    ("左转后保持十五公里每小时", "TURN", {"direction": "LEFT"}),
    ("确认安全后向左变道", "CHANGE_LANE", {"direction": "LEFT"}),
    ("向右变道并保持二十公里每小时", "CHANGE_LANE", {"direction": "RIGHT"}),
    ("绕过右前方停着的车，再回到当前车道", "AVOID_OBSTACLE", {}),
    ("绕开锥桶后回到原车道", "AVOID_OBSTACLE", {}),
    ("避开前方障碍物", "AVOID_OBSTACLE", {}),
    ("跟随右前方那辆车", "FOLLOW", {}),
    ("跟随前方蓝色车辆，保持两秒时距", "FOLLOW", {}),
    ("跟着前车通过路口", "FOLLOW", {}),
    ("如果前车减速就跟随，否则保持当前速度", "FOLLOW", {}),
    ("如果行人进入道路就停车", "YIELD", {}),
    ("等那辆车通过后再向左变道", "CHANGE_LANE", {"direction": "LEFT"}),
    ("通过斑马线后靠边停车", "PULL_OVER", {}),
    ("前方施工占道，从可用车道绕行", "AVOID_OBSTACLE", {}),
    ("看到锥桶就减速并向左变道", "CHANGE_LANE", {"direction": "LEFT"}),
    ("Take the next right and then keep 15 kilometers per hour", "TURN", {"direction": "RIGHT"}),
    ("After the junction, move to the left lane", "CHANGE_LANE", {"direction": "LEFT"}),
    ("Follow the vehicle ahead until the next junction", "FOLLOW", {}),
    ("If the pedestrian crosses, yield", "YIELD", {}),
    ("Go around the visible obstacle and return to the lane", "AVOID_OBSTACLE", {}),
    ("Pull over after the crossing", "PULL_OVER", {}),
    ("向左变道", "CHANGE_LANE", {"direction": "LEFT"}),
    ("右转", "TURN", {"direction": "RIGHT"}),
    ("让前方行人通过", "YIELD", {}),
    ("靠右停车", "PULL_OVER", {}),
    ("跟随目标车", "FOLLOW", {"target_id": "vehicle-1"}),
    ("前面第一个出口右转", "TURN", {"direction": "RIGHT"}),
)

CONFIRM_CASES = (
    ("从那边走", "UNKNOWN", {}, {}),
    ("快一点", "UNKNOWN", {}, {}),
    ("跟着它", "FOLLOW", {}, {}),
    ("随便变个道", "CHANGE_LANE", {}, {}),
    ("go there", "UNKNOWN", {}, {}),
    ("follow it", "FOLLOW", {}, {}),
    ("闯红灯过去", "TURN", {"direction": "RIGHT"}, {"traffic_light": "RED"}),
    ("逆行绕过去", "AVOID_OBSTACLE", {}, {}),
    ("撞开前面的车", "AVOID_OBSTACLE", {}, {}),
    ("不管有没有人直接过去", "KEEP_LANE", {}, {}),
    ("run the red light", "KEEP_LANE", {}, {"traffic_light": "RED"}),
    ("ignore the pedestrian and go", "KEEP_LANE", {}, {}),
    ("跟着那辆白车", "FOLLOW", {}, {"target_candidate_count": 2}),
    ("follow that white car", "FOLLOW", {}, {"target_candidate_count": 3}),
    ("保持速度", "SET_SPEED", {}, {}),
)


def _command(text, intent, parameters):
    return {
        "source_text": text,
        "intent": intent,
        "parameters": parameters,
        "confidence": 0.95,
        "requires_confirmation": False,
    }


def _scene(**updates):
    scene = {
        "objects": [{
            "track_id": "vehicle-1", "class": "vehicle",
            "position_m": [12.0, 0.0, 0.0],
        }],
        "traffic_light": "GREEN",
        "risk_level": "LOW",
        "stale": False,
        "sync": {"within_tolerance": True},
        "modality_valid": {"vehicle_state": True},
    }
    scene.update(updates)
    return scene


@pytest.mark.parametrize("text,intent,parameters", SIMPLE_CASES)
def test_clear_atomic_commands_never_call_qwen(text, intent, parameters):
    result = ComplexityRouter().decide(_command(text, intent, parameters), _scene(), {})
    assert result.disposition == FAST_LOCAL
    assert result.expected_qwen_calls == 0
    assert "CLEAR_ATOMIC" in result.reasons or "LOCAL_SAFETY" in result.reasons


@pytest.mark.parametrize("text,intent,parameters", COMPLEX_CASES)
def test_complex_commands_require_qwen_plan(text, intent, parameters):
    result = ComplexityRouter().decide(_command(text, intent, parameters), _scene(), {})
    assert result.disposition == QWEN_PLAN
    assert result.expected_qwen_calls == 1
    assert result.reasons


@pytest.mark.parametrize("text,intent,parameters,scene_updates", CONFIRM_CASES)
def test_ambiguous_or_illegal_commands_fail_closed(text, intent, parameters, scene_updates):
    result = ComplexityRouter().decide(
        _command(text, intent, parameters), _scene(**scene_updates), {},
    )
    assert result.disposition == CONFIRM_SAFE
    assert result.expected_qwen_calls == 0
    assert result.safe_wait_behavior in {"STOP", "SLOW_DOWN", "KEEP_LANE_LIMITED"}


def test_stale_perception_and_emergency_are_deterministic_gates():
    router = ComplexityRouter()
    stale = router.decide(
        _command("前方路口右转", "TURN", {"direction": "RIGHT"}),
        _scene(stale=True), {},
    )
    assert stale.disposition == CONFIRM_SAFE
    assert stale.reasons == ("PERCEPTION_INVALID",)
    emergency = router.decide(
        _command("紧急停车", "EMERGENCY_STOP", {}),
        _scene(risk_level="EMERGENCY"), {},
    )
    assert emergency.disposition == FAST_LOCAL
    assert emergency.safe_wait_behavior == "EMERGENCY_STOP"


def test_replan_event_is_qwen_routed_and_explainable():
    result = ComplexityRouter().decide(
        _command("继续跟随前车", "FOLLOW", {"target_id": "vehicle-1"}),
        _scene(), {"replan_reason": "TARGET_LOST"},
    )
    assert result.disposition == QWEN_PLAN
    assert "REPLAN_REQUIRED" in result.reasons
    assert "REPLAN_TARGET_LOST" in result.reasons
