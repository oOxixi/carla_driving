from __future__ import annotations

import pytest

from voice_group.vehicle_nlu.src.intent_classifier import classify_intent


@pytest.mark.parametrize(
    "text",
    [
        # S1: simultaneous lane + speed constraints.
        "保持当前车道，将车速提升至60公里每小时",
        "保持当前车道并将速度提高到60公里每小时",

        # Navigation + pedestrian safety.
        "准备左转，同时注意避让正在通过的行人",
        "前方行人正在通过右转路径，请先等候再执行右转",

        # Obstacle avoidance + route recovery.
        "前车行驶缓慢挡住当前通行路径，避开它以后恢复原有行驶路线",
        "施工区域挡住当前路径，请安全绕过后恢复原路线",

        # Speed + obstacle response.
        "道路施工形成障碍，请先控制速度再避开前方设施",

        # Vulnerable-road-user context + speed + continuation.
        "公交车旁边有行人在路侧，请把当前速度调到30公里每小时后继续前进",
    ],
)
def test_multi_action_commands_route_to_slow_path(
    text: str,
) -> None:
    result = classify_intent(text)

    assert result["intent"] == "UNKNOWN"
    assert result["status"] == "needs_slow_path"
    assert result["route"] == "slow"
    assert result["reason"] == "multiple_intents"


@pytest.mark.parametrize(
    "text,expected_intent",
    [
        # A single explicit speed command remains deterministic.
        (
            "前车开得偏慢，本车先降到40公里每小时再继续行驶",
            "SET_SPEED",
        ),

        # Terminal emergency semantics:
        # avoidance is unavailable; STOP is the only executable action.
        (
            "右侧车辆突然切入，距离过近已经来不及避让，立即紧急停车",
            "EMERGENCY_STOP",
        ),
        (
            "前方碰撞风险很高，旁侧也无法安全避让，请立即紧急停车",
            "EMERGENCY_STOP",
        ),
        (
            "已经没有足够避让空间，前方碰撞危险很高，请立即紧急停车",
            "EMERGENCY_STOP",
        ),
    ],
)
def test_single_or_terminal_commands_remain_fast(
    text: str,
    expected_intent: str,
) -> None:
    result = classify_intent(text)

    assert result["route"] == "fast"
    assert result["status"] == "valid"
    assert result["intent"] == expected_intent
