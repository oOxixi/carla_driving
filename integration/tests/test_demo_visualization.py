from __future__ import annotations

from types import SimpleNamespace

from PIL import Image

from integration.contracts import DetectedObject, PerceptionFrame
from integration.demo_visualization import (
    DemoFrameRenderer,
    DemoStatePresenter,
)


def _result(*, override: bool = False, reason: str = "NONE", ttc_s: float = 8.0):
    return SimpleNamespace(
        safety_override=override,
        safety_reason=reason,
        feedback=(),
        final_control=SimpleNamespace(throttle=0.0, brake=1.0 if override else 0.0, steer=0.0),
        longitudinal=SimpleNamespace(
            state="BRAKING" if override else "CRUISING",
            target_speed_mps=0.0 if override else 5.0,
            risk=SimpleNamespace(ttc_s=ttc_s),
        ),
    )


def _vehicle(speed_mps: float = 2.4):
    return SimpleNamespace(speed_mps=speed_mps)


def test_red_light_conflict_is_translated_into_a_strong_safety_event() -> None:
    presenter = DemoStatePresenter("ACC_A02_red_light_conflict")
    presenter.note_voice({
        "source_text": "不用停，继续往前开",
        "intent": "KEEP_LANE",
        "parameters": {"target_speed_kph": 20},
    })
    presenter.note_qwen("READY", {
        "behavior": "KEEP_LANE",
        "reason_code": "USER_REQUESTED_FORWARD",
    })
    scene = PerceptionFrame(
        12, 2.0, traffic_light="RED", distance_to_stop_line_m=11.4,
    )

    state = presenter.build(
        scene=scene,
        vehicle=_vehicle(),
        result=_result(override=True, reason="RED_LIGHT_STOP_LINE_GUARD"),
        target_speed_mps=0.0,
        perception_sources={"traffic_light": "CARLA_SENSOR"},
        active_command=True,
        now_s=2.0,
    )

    assert state.scene_name_cn == "红灯冲突安全处理"
    assert state.scene_id == "ACC_A02"
    assert state.voice_text == "不用停，继续往前开"
    assert state.intent_text == "保持当前车道"
    assert state.qwen_status == "决策完成"
    assert state.safety_status == "安全接管"
    assert state.safety_reason_cn == "红灯禁止通行"
    assert state.timeline_override is True
    assert "traffic" not in " ".join(state.perception_summary).lower()
    assert not state.debug_lines


def test_selected_qwen_target_is_the_only_highlighted_object() -> None:
    presenter = DemoStatePresenter("CX02_multi_vehicle_target_follow_brake")
    presenter.note_voice({
        "source_text": "跟着正前方那辆车",
        "intent": "FOLLOW",
    })
    presenter.note_qwen("SLOW_READY", {
        "behavior": "FOLLOW",
        "target_id": "lead_target",
        "reason_code": "UNIQUE_FORWARD_TARGET",
    })
    objects = (
        DetectedObject(1, "car", 0.9, (0.42, 0.35, 0.58, 0.72), 14.2, "lead_target"),
        DetectedObject(1, "car", 0.8, (0.12, 0.38, 0.26, 0.69), 11.0, "distractor_left"),
        DetectedObject(1, "car", 0.8, (0.74, 0.38, 0.88, 0.69), 18.0, "distractor_right"),
    )
    state = presenter.build(
        scene=PerceptionFrame(13, 2.1, lead_distance_m=14.2, lead_speed_mps=3.0,
                              detected_objects=objects),
        vehicle=_vehicle(3.0),
        result=_result(),
        target_speed_mps=4.0,
        perception_sources={},
        active_command=True,
        now_s=2.1,
    )

    assert state.perception_summary[0] == "候选目标：3"
    assert state.qwen_action_cn == "跟随前车"
    assert sum(item.selected for item in state.objects) == 1
    assert state.objects[0].selected is True


def test_sensor_fault_uses_degraded_chinese_summary() -> None:
    presenter = DemoStatePresenter("VAR_C04_rgb_blackout_lidar_alive")
    presenter.note_voice({"source_text": "感知异常时降低速度", "intent": "SLOW_DOWN"})
    state = presenter.build(
        scene=PerceptionFrame(20, 8.0),
        vehicle=_vehicle(2.0),
        result=_result(),
        target_speed_mps=1.5,
        perception_sources={},
        active_faults=({"type": "sensor_blackout", "sensor": "front_rgb"},),
        active_command=True,
        now_s=8.0,
    )

    assert state.perception_summary == (
        "摄像头：失效",
        "LiDAR：正常",
        "系统：降级运行",
    )


def test_safety_takeover_remains_visible_for_two_seconds() -> None:
    presenter = DemoStatePresenter("D03_front_vehicle_brake")
    presenter.note_voice({"source_text": "继续行驶", "intent": "KEEP_LANE"})
    presenter.build(
        scene=PerceptionFrame(1, 2.0), vehicle=_vehicle(),
        result=_result(override=True, reason="LOW_TTC"),
        target_speed_mps=0.0, perception_sources={}, now_s=2.0,
    )
    retained = presenter.build(
        scene=PerceptionFrame(2, 3.5), vehicle=_vehicle(),
        result=_result(), target_speed_mps=3.0,
        perception_sources={}, now_s=3.5,
    )
    expired = presenter.build(
        scene=PerceptionFrame(3, 4.1), vehicle=_vehicle(),
        result=_result(), target_speed_mps=3.0,
        perception_sources={}, now_s=4.1,
    )

    assert retained.safety_status == "安全接管"
    assert retained.timeline_override is True
    assert expired.safety_status == "安全监督"
    assert expired.timeline_override is False


def test_internal_qwen_wait_release_is_not_shown_as_user_command_failure() -> None:
    presenter = DemoStatePresenter("CX_MAIN_01_safe_urban_mission")
    presenter.note_voice({"source_text": "跟随前车", "intent": "KEEP_LANE"})
    presenter.note_qwen("READY", {"behavior": "FOLLOW"})
    result = _result()
    result.feedback = ({
        "command_id": "qwen-wait-123",
        "status": "FAILED",
        "detail": "Qwen result ready; temporary safety wait released",
    },)

    state = presenter.build(
        scene=PerceptionFrame(3, 1.0), vehicle=_vehicle(), result=result,
        target_speed_mps=4.0, perception_sources={}, active_command=True,
        now_s=1.0,
    )

    assert state.execution_status == "执行中"


def test_demo_renderer_produces_readable_1080p_composite() -> None:
    presenter = DemoStatePresenter("ACC_A02_red_light_conflict")
    presenter.note_voice({"source_text": "停车", "intent": "STOP"})
    presenter.note_qwen("READY", {"behavior": "STOP"})
    state = presenter.build(
        scene=PerceptionFrame(1, 0.1),
        vehicle=_vehicle(0.0),
        result=_result(),
        target_speed_mps=0.0,
        perception_sources={},
        now_s=0.1,
    )
    image = DemoFrameRenderer().render(
        Image.new("RGB", (800, 450), "#506875"), state,
    )

    assert image.size == (1920, 1080)
    assert image.mode == "RGB"
    # Main camera and light information panel must remain visually distinct.
    assert image.getpixel((100, 500)) != image.getpixel((1500, 500))


def test_debug_telemetry_is_opt_in() -> None:
    presenter = DemoStatePresenter("cruise")
    state = presenter.build(
        scene=PerceptionFrame(7, 1.0),
        vehicle=_vehicle(),
        result=_result(),
        target_speed_mps=4.0,
        perception_sources={},
        execution_state="FOLLOWING",
        now_s=1.0,
        debug=True,
    )
    assert any("throttle=" in line for line in state.debug_lines)
