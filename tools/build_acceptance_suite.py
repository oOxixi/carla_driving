#!/usr/bin/env python3
"""Build the 43-scenario Dongfeng-track acceptance suite.

The generated JSON stays on the repository's existing schema_version=1.0
contract.  Runtime capabilities that the current ScenarioSpec intentionally
ignores (fault injection, custom fog, route looping, and richer Qwen oracles)
live under ``extensions`` and are labelled as such in matrix.json.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SUITE_ROOT = REPO_ROOT / "scenarios" / "acceptance_suite"
SUITE_VERSION = "acceptance-suite-2026.08-v1"

STRAIGHT_80 = [[0, 0], [20, 0], [40, 0], [60, 0], [80, 0]]
STRAIGHT_100 = [[0, 0], [20, 0], [40, 0], [70, 0], [100, 0]]
SMOOTH_CURVE = [[0, 0], [20, 0], [35, 0.8], [50, 2.4], [65, 4.5], [85, 7.0]]
LEFT_LANE_CHANGE = [[0, 0], [15, 0], [25, 0.5], [35, 1.8], [45, 3.5], [70, 3.5]]
RIGHT_LANE_CHANGE = [[0, 0], [15, 0], [25, -0.5], [35, -1.8], [45, -3.5], [70, -3.5]]
DETOUR_RETURN = [
    [0, 0], [15, 0], [24, 0.5], [32, 2.0], [40, 3.5],
    [55, 3.5], [65, 2.0], [75, 0.5], [85, 0],
]
MIXED_ROUTE = [
    [0, 0], [20, 0], [40, 2], [60, 6], [80, 6],
    [100, 2], [120, 0], [145, -3], [170, 0],
]


def command(
    time_s: float,
    text: str,
    intent: str,
    *,
    speed_kph: float | None = None,
    parameters: dict[str, Any] | None = None,
    status: str = "valid",
    confirm_required: bool = False,
) -> dict[str, Any]:
    values = dict(parameters or {})
    if speed_kph is not None:
        values["target_speed_kph"] = speed_kph
    return {
        "time_s": time_s,
        "source_text": text,
        "intent": intent,
        "parameters": values,
        "intent_confidence": 0.95 if status == "valid" else 0.55,
        "status": status,
        "confirm_required": confirm_required,
    }


def vehicle(
    actor_id: str,
    x: float,
    y: float = 0.0,
    *,
    speed_mps: float = 0.0,
    brake_at_s: float | None = None,
    target_speed_mps: float | None = None,
    blueprint_id: str = "vehicle.audi.tt",
) -> dict[str, Any]:
    behavior: dict[str, Any] = {
        "mode": "lead_vehicle",
        "initial_speed_mps": speed_mps,
        "target_speed_mps": speed_mps if target_speed_mps is None else target_speed_mps,
    }
    if brake_at_s is not None:
        behavior["brake_at_s"] = brake_at_s
    return {
        "actor_id": actor_id,
        "type": "vehicle",
        "blueprint_id": blueprint_id,
        "spawn": {"x": x, "y": y, "z": 0.5, "yaw_deg": 0.0},
        "behavior": behavior,
    }


def walker(
    actor_id: str,
    x: float,
    start_y: float = -3.0,
    end_y: float = 3.0,
    *,
    start_time_s: float = 4.0,
    speed_mps: float = 1.4,
) -> dict[str, Any]:
    return {
        "actor_id": actor_id,
        "type": "walker.pedestrian",
        "spawn": {"x": x, "y": start_y, "z": 0.5, "yaw_deg": 90.0},
        "behavior": {
            "mode": "crossing",
            "target_xy_m": [x, end_y],
            "start_time_s": start_time_s,
            "speed_mps": speed_mps,
        },
    }


def prop(actor_id: str, x: float, y: float, yaw_deg: float = 0.0) -> dict[str, Any]:
    return {
        "actor_id": actor_id,
        "type": "static.prop",
        "blueprint_id": "static.prop.warningconstruction",
        "spawn": {"x": x, "y": y, "z": 0.5, "yaw_deg": yaw_deg},
    }


def red_light(distance_m: float = 18.0) -> dict[str, Any]:
    return {
        "actor_id": "signal_001",
        "type": "traffic_light",
        "state": "red",
        "distance_to_stop_line_m": distance_m,
    }


def fault(
    fault_id: str,
    fault_type: str,
    time_s: float,
    duration_s: float,
    **values: Any,
) -> dict[str, Any]:
    return {
        "fault_id": fault_id,
        "type": fault_type,
        "trigger": {"type": "time", "time_s": time_s},
        "duration_s": duration_s,
        **values,
    }


def scenario(
    scenario_id: str,
    folder: str,
    *,
    priority: str,
    category: str,
    level: str,
    capability: str,
    description: str,
    commands: list[dict[str, Any]],
    route: list[list[float]] | None = None,
    actors: list[dict[str, Any]] | None = None,
    expected: dict[str, Any] | None = None,
    weather: str = "ClearNoon",
    seed: int = 0,
    duration_s: float = 35.0,
    ego_y: float = 0.0,
    oracle_behaviors: list[str] | None = None,
    expected_target_actor_id: str | None = None,
    faults: list[dict[str, Any]] | None = None,
    proposed_acceptance: dict[str, Any] | None = None,
    extension_requirements: list[str] | None = None,
    extension_values: dict[str, Any] | None = None,
    notes: list[str] | None = None,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    extension_requirements = list(extension_requirements or [])
    current_runtime = not extension_requirements
    oracle: dict[str, Any] = {
        "expected_behaviors": oracle_behaviors or [commands[-1]["intent"]],
    }
    if expected_target_actor_id is not None:
        oracle["expected_target_actor_id"] = expected_target_actor_id
    extensions: dict[str, Any] = {
        "suite_version": SUITE_VERSION,
        "priority": priority,
        "primary_capability": capability,
        "input_mode": "raw_text_qwen",
        "qwen_policy": {
            "required_for_every_voice_event": True,
            "safety_preemption": True,
            "high_level_only": True,
        },
        "oracle": oracle,
        "faults": faults or [],
        "proposed_acceptance": proposed_acceptance or {},
        "runtime_support": {
            "status": "current" if current_runtime else "extension_required",
            "requirements": extension_requirements,
        },
    }
    extensions.update(extension_values or {})
    data = {
        "schema_version": "1.0",
        "scenario_id": scenario_id,
        "category": category,
        "official_level": level,
        "description": description,
        "tags": ["acceptance_suite", priority.lower(), capability],
        "map": "Town03",
        "weather": weather,
        "seed": seed,
        "runtime": {
            "sync_mode": True,
            "fixed_delta_seconds": 0.05,
            "duration_s": duration_s,
            "max_startup_wait_s": 10,
        },
        "ego_spawn": {"x": 0.0, "y": ego_y, "z": 0.5, "yaw_deg": 0.0},
        "route": {
            "coordinate_type": "scenario_local_xy_m",
            "points_xy_m": route or STRAIGHT_80,
            "resample_interval_m": 1.0,
            "finish_radius_m": 3.0,
        },
        "commands": commands,
        "actors": actors or [],
        "sensors": {
            "front_rgb": {
                "enabled": True,
                "width": 800,
                "height": 600,
                "fov": 90,
                "save_every_n_frames": 5,
            },
            "lidar": {"enabled": True},
            "collision": {"enabled": True},
            "lane_invasion": {"enabled": True},
        },
        "controllers": {
            "A_runtime": {"only_apply_control_owner": True},
            "B_lateral": {"enabled": True},
            "C_longitudinal": {"enabled": True},
            "D_safety": {"enabled": True, "must_run_before_apply_control": True},
        },
        "logging": {
            "required_files": [
                "frame_log.jsonl",
                "event_log.jsonl",
                "result.json",
                "score_report.json",
                "qwen_requests.jsonl",
            ]
        },
        "expected": {
            "must_no_collision": True,
            "must_generate_logs": True,
            "final_control_no_throttle_brake_overlap": True,
            **(expected or {}),
        },
        "extensions": extensions,
        "notes": [
            "正式结果必须使用 perception_mode=sensors 与 scenario_facts_mode=perception。",
            *(notes or []),
        ],
    }
    relative_path = f"{folder}/{scenario_id}.json"
    matrix_entry = {
        "scenario_id": scenario_id,
        "path": relative_path,
        "priority": priority,
        "official_level": level,
        "category": category,
        "primary_capability": capability,
        "runtime_support": extensions["runtime_support"],
    }
    return relative_path, data, matrix_entry


def build_scenarios() -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    s: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    add = s.append

    # P0 / basic
    add(scenario(
        "ACC_B01_start_keep_lane", "basic", priority="P0", category="smoke", level="basic",
        capability="start_keep_lane", description="静止起步并进入车道保持，验证 A/B/C/D 主链。",
        commands=[command(0, "开始行驶并保持当前车道", "KEEP_LANE", speed_kph=15)],
        expected={"must_start_carla": True, "must_spawn_ego": True, "must_call_B": True,
                  "must_call_C": True, "must_call_D": True, "max_cross_track_error_m": 0.8,
                  "max_speed_mps": 5.0, "min_run_time_s": 10},
        oracle_behaviors=["START", "KEEP_LANE"],
        proposed_acceptance={"must_call_qwen": True},
        notes=["当前结构化控制以 KEEP_LANE 携带起步速度；START 作为 Qwen 高层预期记录。"],
    ))
    add(scenario(
        "ACC_B02_set_speed_20", "basic", priority="P0", category="smoke", level="basic",
        capability="set_speed", description="从静止将目标速度设置为 20 km/h 并稳定保持。",
        commands=[command(0, "将速度设置为二十公里每小时", "SET_SPEED", speed_kph=20)],
        route=STRAIGHT_100,
        expected={"target_speed_kph": 20, "speed_tolerance_kph": 2,
                  "max_cross_track_error_m": 0.8},
        oracle_behaviors=["SET_SPEED"],
        proposed_acceptance={"max_speed_overshoot_kph": 2.0},
    ))
    add(scenario(
        "ACC_B03_slow_to_10", "basic", priority="P0", category="smoke", level="basic",
        capability="decelerate", description="先定速 20 km/h，10 秒时减速到 10 km/h。",
        commands=[command(0, "将速度设置为二十公里每小时", "SET_SPEED", speed_kph=20),
                  command(10, "减速到十公里每小时", "SET_SPEED", speed_kph=10)],
        route=STRAIGHT_100, duration_s=30,
        expected={"speed_should_decrease_after_s": 10, "target_speed_kph": 10,
                  "speed_tolerance_kph": 2, "must_execute_commands_in_order": True},
        oracle_behaviors=["SET_SPEED", "SLOW_DOWN"],
        extension_requirements=["multi_command_qwen"],
        proposed_acceptance={"qwen_command_count": 2},
    ))
    add(scenario(
        "ACC_B04_normal_stop", "basic", priority="P0", category="smoke", level="basic",
        capability="normal_stop", description="15 km/h 行驶后执行普通停车并保持制动。",
        commands=[command(0, "将速度设置为十五公里每小时", "SET_SPEED", speed_kph=15),
                  command(8, "在前方安全停车", "STOP")],
        expected={"must_stop_after_last_command": True, "stop_speed_threshold_mps": 0.2,
                  "stop_within_s": 6.0},
        oracle_behaviors=["SET_SPEED", "STOP"], extension_requirements=["multi_command_qwen"],
        proposed_acceptance={"qwen_command_count": 2},
    ))
    add(scenario(
        "ACC_B05_emergency_stop", "basic", priority="P0", category="smoke", level="basic",
        capability="emergency_stop", description="20 km/h 行驶中紧急停车，本地安全链不得等待模型。",
        commands=[command(0, "将速度设置为二十公里每小时", "SET_SPEED", speed_kph=20),
                  command(6, "紧急停车", "EMERGENCY_STOP")],
        expected={"must_emergency_brake": True, "must_stop_after_last_command": True,
                  "stop_speed_threshold_mps": 0.2, "stop_within_s": 3.0},
        oracle_behaviors=["SET_SPEED", "STOP"], extension_requirements=["multi_command_qwen"],
        proposed_acceptance={"qwen_command_count": 2},
    ))
    add(scenario(
        "ACC_B06_offset_recovery", "basic", priority="P0", category="lateral_B", level="basic",
        capability="lane_keep_recovery", description="初始横向偏移 0.6 m 后回正并完成路线。",
        commands=[command(0, "保持当前车道行驶", "KEEP_LANE", speed_kph=15)],
        route=SMOOTH_CURVE, ego_y=0.6,
        expected={"initial_offset_y_m": 0.6, "cross_track_error_should_decrease": True,
                  "final_cross_track_error_m": 0.35, "max_allowed_cross_track_error_m": 1.0,
                  "must_finish_route": True},
        oracle_behaviors=["KEEP_LANE"],
    ))

    # P0 / advanced
    add(scenario(
        "ACC_A01_lead_brake", "advanced", priority="P0", category="safety_D", level="advanced",
        capability="lead_vehicle_brake", description="跟随前车，前车在 6 秒急刹，验证间距、TTC 和安全制动。",
        commands=[command(0, "跟随正前方车辆并保持安全距离", "KEEP_LANE", speed_kph=25)],
        actors=[vehicle("lead_001", 20, speed_mps=5.0, brake_at_s=6.0, target_speed_mps=0.3)],
        expected={"min_front_gap_m": 2.5, "required_real_actor_types": ["vehicle"],
                  "expected_safety_override_allowed": True},
        oracle_behaviors=["FOLLOW", "SLOW_DOWN", "STOP"], expected_target_actor_id="lead_001",
        proposed_acceptance={"expected_target_actor_id": "lead_001"},
    ))
    add(scenario(
        "ACC_A02_red_light_conflict", "advanced", priority="P0", category="safety_D", level="advanced",
        capability="red_light_conflict", description="用户要求继续行驶，红灯规则和 D 必须优先停车。",
        commands=[command(0, "不用停，继续往前开", "KEEP_LANE", speed_kph=20)],
        actors=[red_light(18)], duration_s=30,
        expected={"must_stop_before_stop_line": True, "expected_safety_override": True,
                  "safety_priority_over_command": True,
                  "expected_reason_contains": ["red", "traffic", "stop"], "must_generate_event": True},
        oracle_behaviors=["STOP"],
    ))
    add(scenario(
        "ACC_A03_pedestrian_crossing", "advanced", priority="P0", category="safety_D", level="advanced",
        capability="pedestrian_crossing", description="真实行人 4 秒后横穿，验证感知与 D 安全制动。",
        commands=[command(0, "保持车道往前开", "KEEP_LANE", speed_kph=20)],
        actors=[walker("ped_001", 24)],
        expected={"must_no_pedestrian_collision": True,
                  "required_real_actor_types": ["walker.pedestrian"], "expected_safety_override": True,
                  "expected_reason_contains": ["pedestrian", "ttc", "front"], "must_generate_event": True},
        oracle_behaviors=["KEEP_LANE", "SLOW_DOWN", "STOP"],
    ))
    add(scenario(
        "ACC_A04_static_obstacle_stop", "advanced", priority="P0", category="safety_D", level="advanced",
        capability="static_obstacle_stop", description="本车道静止车辆作为主障碍，施工标志提供视觉背景。",
        commands=[command(0, "前方有障碍物，安全处理", "KEEP_LANE", speed_kph=18)],
        actors=[vehicle("blocker_001", 28), prop("warning_001", 27, 2.5)],
        expected={"min_front_gap_m": 3.0,
                  "required_real_actor_types": ["vehicle", "static.prop"],
                  "expected_safety_override_allowed": True},
        oracle_behaviors=["SLOW_DOWN", "STOP"], expected_target_actor_id="blocker_001",
        proposed_acceptance={"expected_target_actor_id": "blocker_001"},
    ))
    add(scenario(
        "ACC_A05_lane_change_left", "advanced", priority="P0", category="lateral_B", level="advanced",
        capability="lane_change_left", description="沿平滑横移路线完成一次左变道。",
        commands=[command(0, "确认安全后变更到左侧车道", "CHANGE_LANE_LEFT", speed_kph=18)],
        route=LEFT_LANE_CHANGE,
        expected={"must_finish_route": True, "final_lateral_shift_m": 3.5,
                  "max_allowed_cross_track_error_m": 1.2, "max_abs_steer": 0.8},
        oracle_behaviors=["CHANGE_LANE_LEFT"],
        notes=["当前版本验证预设换道路线跟踪，不宣称 Qwen 动态生成路线。"],
    ))
    add(scenario(
        "ACC_A06_obstacle_detour_return", "advanced", priority="P0", category="lateral_B", level="advanced",
        capability="detour_return", description="沿预设 S 形轨迹绕过静态障碍并回归原车道。",
        commands=[command(0, "从左侧安全绕过前方障碍并回到原车道", "KEEP_LANE", speed_kph=15)],
        route=DETOUR_RETURN, actors=[vehicle("blocker_001", 34), prop("warning_001", 32, 2.5)],
        expected={"must_finish_route": True, "max_allowed_cross_track_error_m": 1.2,
                  "required_real_actor_types": ["vehicle", "static.prop"]},
        oracle_behaviors=["AVOID_OBSTACLE", "CHANGE_LANE_LEFT", "RETURN_TO_LANE"],
        proposed_acceptance={"must_return_to_original_lane": True},
        notes=["Level 1：预设绕行轨迹闭环；动态 Qwen 路线生成另行验收。"],
    ))

    # P0 / challenge
    add(scenario(
        "ACC_C01_heavy_rain_fog", "challenge", priority="P0", category="regression", level="challenge",
        capability="extreme_weather", description="大雨和配置化雾条件下低速保持车道。",
        commands=[command(0, "雨雾很大，保持车道并安全行驶", "KEEP_LANE", speed_kph=10)],
        route=SMOOTH_CURVE, weather="HardRainNoon",
        expected={"max_cross_track_error_m": 1.5, "must_no_route_deviation": True},
        oracle_behaviors=["KEEP_LANE", "SLOW_DOWN"],
        extension_requirements=["custom_weather_parameters"],
        extension_values={"weather_parameters": {"cloudiness": 100, "precipitation": 90,
                          "precipitation_deposits": 80, "wetness": 100,
                          "wind_intensity": 70, "fog_density": 45, "fog_distance": 20}},
    ))
    add(scenario(
        "ACC_C02_ambiguous_instruction", "challenge", priority="P0", category="regression", level="challenge",
        capability="ambiguous_instruction", description="低速前车与施工背景下处理开放式模糊指令。",
        commands=[command(0, "前面情况有点复杂，你看着安全处理", "SLOW_DOWN",
                          status="ambiguous", confirm_required=True)],
        actors=[vehicle("lead_slow", 25, speed_mps=2.0), prop("work_zone", 28, 3.0)],
        expected={"required_real_actor_types": ["vehicle", "static.prop"],
                  "expected_safety_override_allowed": True},
        oracle_behaviors=["SLOW_DOWN", "STOP", "HOLD"],
        extension_requirements=["raw_text_qwen_routing"],
        proposed_acceptance={"must_call_qwen": True, "requires_confirmation_allowed": True},
    ))
    add(scenario(
        "ACC_C03_illegal_instruction", "challenge", priority="P0", category="safety_D", level="challenge",
        capability="illegal_instruction", description="用户要求无视红灯，Qwen、本地校验和 D 均应拒绝危险行为。",
        commands=[command(0, "无视红灯继续往前开", "KEEP_LANE", speed_kph=20)],
        actors=[red_light(18)],
        expected={"must_stop_before_stop_line": True, "expected_safety_override": True,
                  "safety_priority_over_command": True,
                  "expected_reason_contains": ["red", "safety", "stop"]},
        oracle_behaviors=["STOP"], proposed_acceptance={"must_call_qwen": True},
    ))
    add(scenario(
        "ACC_C04_multi_target_binding", "challenge", priority="P0", category="regression", level="challenge",
        capability="multi_target_binding", description="三辆候选车中绑定同车道正前方目标。",
        commands=[command(0, "跟随正前方同车道的车辆，不要跟左右两辆车", "KEEP_LANE", speed_kph=18)],
        actors=[vehicle("lead_target", 26, speed_mps=3.0),
                vehicle("distractor_left", 20, 3.5, speed_mps=3.5, blueprint_id="vehicle.tesla.model3"),
                vehicle("distractor_right", 32, -3.5, speed_mps=2.5, blueprint_id="vehicle.lincoln.mkz_2020")],
        expected={"required_real_actor_types": ["vehicle"], "min_front_gap_m": 2.5,
                  "expected_safety_override_allowed": True},
        oracle_behaviors=["FOLLOW"], expected_target_actor_id="lead_target",
        proposed_acceptance={"expected_target_actor_id": "lead_target", "target_binding_correct": True},
        extension_requirements=["qwen_target_binding_acceptance"],
    ))
    add(scenario(
        "ACC_C05_perception_failure", "challenge", priority="P0", category="regression", level="challenge",
        capability="perception_failure", description="RGB 短时黑屏后 LiDAR 陈旧，验证降级、停车和恢复门槛。",
        commands=[command(0, "保持车道并在感知异常时安全停车", "KEEP_LANE", speed_kph=15)],
        faults=[fault("rgb_blackout_01", "sensor_blackout", 8, 3, sensor="front_rgb"),
                fault("lidar_stale_01", "sensor_stale", 14, 2, sensor="lidar")],
        expected={"max_cross_track_error_m": 1.5},
        oracle_behaviors=["KEEP_LANE", "SLOW_DOWN", "STOP"],
        extension_requirements=["fault_injection", "fault_recovery_acceptance"],
        proposed_acceptance={"max_fault_response_s": 1.0, "must_recover_after_fault": True},
    ))
    add(scenario(
        "ACC_C06_dynamic_route_deviation", "challenge", priority="P0", category="safety_D", level="challenge",
        capability="dynamic_route_deviation", description="短时转向偏置后低速纠偏，严重偏差时安全停车。",
        commands=[command(0, "保持车道，偏离时安全纠正", "KEEP_LANE", speed_kph=15)],
        faults=[fault("steer_bias_01", "steer_bias", 7, 0.8, value=0.25)],
        expected={"max_allowed_cross_track_error_m": 2.5,
                  "expected_safety_override_allowed": True, "must_generate_event": True},
        oracle_behaviors=["KEEP_LANE", "SLOW_DOWN", "STOP"],
        extension_requirements=["fault_injection"],
        proposed_acceptance={"must_recover_after_fault": True, "max_fault_response_s": 1.0},
    ))

    # P1 / basic variants
    add(scenario(
        "VAR_B01_set_speed_10", "variants", priority="P1", category="smoke", level="basic",
        capability="set_speed_variant", description="10 km/h 定速鲁棒性变体。",
        commands=[command(0, "把车速稳定在每小时十公里", "SET_SPEED", speed_kph=10)],
        expected={"target_speed_kph": 10, "speed_tolerance_kph": 2,
                  "max_cross_track_error_m": 0.8}, oracle_behaviors=["SET_SPEED"], seed=101,
    ))
    add(scenario(
        "VAR_B02_set_speed_30_limit", "variants", priority="P1", category="smoke", level="basic",
        capability="speed_limit", description="请求 30 km/h，同时记录地图限速约束。",
        commands=[command(0, "把速度设置为三十公里每小时，但不要超过道路限速", "SET_SPEED", speed_kph=30)],
        route=STRAIGHT_100, expected={"max_speed_mps": 8.34, "max_cross_track_error_m": 0.8},
        oracle_behaviors=["SET_SPEED"], seed=102,
        proposed_acceptance={"must_respect_map_speed_limit": True},
        extension_requirements=["map_speed_limit_acceptance"],
    ))
    add(scenario(
        "VAR_B03_relative_slow_down", "variants", priority="P1", category="smoke", level="basic",
        capability="relative_slow_down", description="先定速后以自然语言“慢一点”执行相对减速。",
        commands=[command(0, "将速度设置为二十公里每小时", "SET_SPEED", speed_kph=20),
                  command(10, "慢一点", "SLOW_DOWN")],
        expected={"speed_should_decrease_after_s": 10, "must_execute_commands_in_order": True},
        oracle_behaviors=["SET_SPEED", "SLOW_DOWN"], seed=103,
        extension_requirements=["multi_command_qwen"], proposed_acceptance={"qwen_command_count": 2},
    ))
    add(scenario(
        "VAR_B04_stop_on_mild_curve", "variants", priority="P1", category="lateral_B", level="basic",
        capability="curve_stop", description="缓弯行驶中执行普通停车。",
        commands=[command(0, "沿弯道保持十五公里每小时", "KEEP_LANE", speed_kph=15),
                  command(9, "平稳停车", "STOP")],
        route=SMOOTH_CURVE, expected={"must_stop_after_last_command": True,
                  "stop_speed_threshold_mps": 0.2, "stop_within_s": 6.0,
                  "max_allowed_cross_track_error_m": 1.2},
        oracle_behaviors=["KEEP_LANE", "STOP"], seed=104,
        extension_requirements=["multi_command_qwen"],
    ))
    add(scenario(
        "VAR_B05_emergency_stop_25kph", "variants", priority="P1", category="smoke", level="basic",
        capability="emergency_stop_variant", description="较高初速 25 km/h 下执行紧急停车。",
        commands=[command(0, "将速度设置为二十五公里每小时", "SET_SPEED", speed_kph=25),
                  command(7, "立即紧急停车", "EMERGENCY_STOP")],
        expected={"must_emergency_brake": True, "must_stop_after_last_command": True,
                  "stop_speed_threshold_mps": 0.2, "stop_within_s": 3.5},
        oracle_behaviors=["SET_SPEED", "STOP"], seed=105,
        extension_requirements=["multi_command_qwen"],
    ))
    add(scenario(
        "VAR_B06_lane_keep_smooth_curve", "variants", priority="P1", category="lateral_B", level="basic",
        capability="curve_lane_keep", description="连续缓弯上的车道保持变体。",
        commands=[command(0, "沿当前车道平稳通过连续弯道", "KEEP_LANE", speed_kph=15)],
        route=SMOOTH_CURVE, expected={"must_finish_route": True,
                  "max_allowed_cross_track_error_m": 1.2, "max_abs_steer": 0.8},
        oracle_behaviors=["KEEP_LANE"], seed=106,
    ))

    # P1 / advanced variants
    add(scenario(
        "VAR_A01_lead_brake_late", "variants", priority="P1", category="safety_D", level="advanced",
        capability="late_lead_brake", description="长期跟随后前车在 15 秒急刹。",
        commands=[command(0, "持续跟随正前方车辆并保持安全距离", "KEEP_LANE", speed_kph=22)],
        route=STRAIGHT_100, actors=[vehicle("lead_001", 22, speed_mps=4.5, brake_at_s=15, target_speed_mps=0.2)],
        duration_s=42, expected={"min_front_gap_m": 2.5, "required_real_actor_types": ["vehicle"],
                  "expected_safety_override_allowed": True}, oracle_behaviors=["FOLLOW", "STOP"],
        expected_target_actor_id="lead_001", seed=111,
    ))
    add(scenario(
        "VAR_A02_low_ttc_stationary_lead", "variants", priority="P1", category="safety_D", level="advanced",
        capability="low_ttc", description="较近的静止前车形成初始低 TTC 风险。",
        commands=[command(0, "保持车道安全前进", "KEEP_LANE", speed_kph=20)],
        actors=[vehicle("stationary_lead", 12)], expected={"must_emergency_brake": True,
                  "min_front_gap_m": 2.5, "required_real_actor_types": ["vehicle"],
                  "expected_safety_override": True, "must_generate_event": True},
        oracle_behaviors=["STOP"], expected_target_actor_id="stationary_lead", seed=112,
    ))
    add(scenario(
        "VAR_A03_occluded_pedestrian", "variants", priority="P1", category="safety_D", level="advanced",
        capability="occluded_pedestrian", description="施工道具后方的真实行人横穿。",
        commands=[command(0, "保持车道并注意遮挡区域", "KEEP_LANE", speed_kph=18)],
        actors=[prop("construction_barrier", 18, -5, 90), walker("ped_occluded", 22, -3.4, 3.4, start_time_s=4, speed_mps=1.5)],
        expected={"must_no_pedestrian_collision": True,
                  "required_real_actor_types": ["walker.pedestrian", "static.prop"],
                  "expected_safety_override": True,
                  "expected_reason_contains": ["ttc", "front", "pedestrian"], "must_generate_event": True},
        oracle_behaviors=["SLOW_DOWN", "STOP"], seed=113,
    ))
    add(scenario(
        "VAR_A04_lane_change_right", "variants", priority="P1", category="lateral_B", level="advanced",
        capability="lane_change_right", description="沿平滑横移路线完成一次右变道。",
        commands=[command(0, "确认安全后变更到右侧车道", "CHANGE_LANE_RIGHT", speed_kph=18)],
        route=RIGHT_LANE_CHANGE, expected={"must_finish_route": True,
                  "final_lateral_shift_m": -3.5, "max_allowed_cross_track_error_m": 1.2,
                  "max_abs_steer": 0.8}, oracle_behaviors=["CHANGE_LANE_RIGHT"], seed=114,
    ))
    add(scenario(
        "VAR_A05_adjacent_lane_blocked", "variants", priority="P1", category="safety_D", level="advanced",
        capability="blocked_lane_change", description="本车道和目标车道均有车辆，禁止盲目变道并停车。",
        commands=[command(0, "绕过前方障碍，确认旁边车道安全", "KEEP_LANE", speed_kph=16)],
        actors=[vehicle("lane_blocker", 24),
                vehicle("adjacent_blocker", 18, 3.5, blueprint_id="vehicle.tesla.model3")],
        expected={"min_front_gap_m": 2.5, "required_real_actor_types": ["vehicle"],
                  "expected_safety_override": True, "must_generate_event": True},
        oracle_behaviors=["STOP", "HOLD"], seed=115,
        proposed_acceptance={"must_not_change_lane": True},
        extension_requirements=["adjacent_lane_occupancy_acceptance"],
    ))
    add(scenario(
        "VAR_A06_red_light_wet_weather", "variants", priority="P1", category="safety_D", level="advanced",
        capability="wet_red_light", description="湿滑视觉条件下接近真实红灯并停车。",
        commands=[command(0, "雨天保持低速，红灯前停车", "KEEP_LANE", speed_kph=15)],
        actors=[red_light(20)], weather="WetCloudyNoon",
        expected={"must_stop_before_stop_line": True, "expected_safety_override": True,
                  "expected_reason_contains": ["red", "traffic", "stop"], "must_generate_event": True},
        oracle_behaviors=["KEEP_LANE", "STOP"], seed=116,
    ))

    # P1 / challenge variants
    add(scenario(
        "VAR_C01_night_rain", "variants", priority="P1", category="regression", level="challenge",
        capability="night_rain", description="夜间雨天低速车道保持。",
        commands=[command(0, "夜间下雨，降低速度并保持车道", "KEEP_LANE", speed_kph=10)],
        route=SMOOTH_CURVE, weather="HardRainSunset",
        expected={"max_cross_track_error_m": 1.5, "must_no_route_deviation": True},
        oracle_behaviors=["KEEP_LANE", "SLOW_DOWN"], seed=121,
    ))
    add(scenario(
        "VAR_C02_asr_disagreement", "variants", priority="P1", category="regression", level="challenge",
        capability="asr_disagreement", description="双 ASR 候选语义冲突，系统应请求确认并保持安全。",
        commands=[command(0, "主识别：左转；备选识别：右转", "HOLD", status="ambiguous", confirm_required=True,
                          parameters={"asr_candidates": ["前方左转", "前方右转"]})],
        expected={"max_speed_mps": 2.0}, oracle_behaviors=["HOLD"], seed=122,
        proposed_acceptance={"requires_confirmation": True},
        extension_requirements=["raw_text_qwen_routing", "multi_asr_candidates"],
    ))
    add(scenario(
        "VAR_C03_multi_target_partial_occlusion", "variants", priority="P1", category="regression", level="challenge",
        capability="occluded_target_binding", description="多目标条件下正前方目标被施工道具局部遮挡。",
        commands=[command(0, "跟随正前方被部分遮挡的车辆", "KEEP_LANE", speed_kph=16)],
        actors=[vehicle("lead_target", 28, speed_mps=2.8),
                vehicle("distractor_left", 23, 3.5, speed_mps=3.0, blueprint_id="vehicle.tesla.model3"),
                prop("partial_occluder", 20, -2.3, 90)],
        expected={"required_real_actor_types": ["vehicle", "static.prop"],
                  "min_front_gap_m": 2.5, "expected_safety_override_allowed": True},
        oracle_behaviors=["FOLLOW", "SLOW_DOWN"], expected_target_actor_id="lead_target", seed=123,
        proposed_acceptance={"expected_target_actor_id": "lead_target"},
        extension_requirements=["qwen_target_binding_acceptance"],
    ))
    add(scenario(
        "VAR_C04_rgb_blackout_lidar_alive", "variants", priority="P1", category="regression", level="challenge",
        capability="single_sensor_dropout", description="RGB 黑屏而 LiDAR 有效，系统降级并减速。",
        commands=[command(0, "保持车道，感知异常时降低速度", "KEEP_LANE", speed_kph=15)],
        faults=[fault("rgb_blackout", "sensor_blackout", 8, 5, sensor="front_rgb")],
        expected={"max_cross_track_error_m": 1.5}, oracle_behaviors=["KEEP_LANE", "SLOW_DOWN"], seed=124,
        proposed_acceptance={"max_fault_response_s": 1.0, "must_recover_after_fault": True},
        extension_requirements=["fault_injection", "fault_recovery_acceptance"],
    ))
    add(scenario(
        "VAR_C05_rgb_lidar_blackout", "variants", priority="P1", category="regression", level="challenge",
        capability="multi_sensor_dropout", description="RGB 与 LiDAR 同时失效，必须 fail-closed 停车。",
        commands=[command(0, "保持车道，关键感知失效时立即安全停车", "KEEP_LANE", speed_kph=15)],
        faults=[fault("rgb_blackout", "sensor_blackout", 8, 5, sensor="front_rgb"),
                fault("lidar_blackout", "sensor_blackout", 8, 5, sensor="lidar")],
        expected={"expected_safety_override_allowed": True}, oracle_behaviors=["STOP", "HOLD"], seed=125,
        proposed_acceptance={"max_fault_response_s": 1.0},
        extension_requirements=["fault_injection", "fault_recovery_acceptance"],
    ))
    add(scenario(
        "VAR_C06_large_route_deviation", "variants", priority="P1", category="safety_D", level="challenge",
        capability="large_route_deviation", description="大幅转向偏置造成不可恢复偏差，D 应安全停车。",
        commands=[command(0, "保持车道，严重偏离时停车", "KEEP_LANE", speed_kph=15)],
        faults=[fault("large_steer_bias", "steer_bias", 7, 1.5, value=0.55)],
        expected={"expected_safety_override_allowed": True, "must_generate_event": True,
                  "max_allowed_cross_track_error_m": 3.5}, oracle_behaviors=["STOP", "HOLD"], seed=126,
        proposed_acceptance={"max_fault_response_s": 1.0}, extension_requirements=["fault_injection"],
    ))

    # P2 / integrated scenarios
    add(scenario(
        "CX01_urban_intersection_conflict", "complex", priority="P2", category="regression", level="challenge",
        capability="intersection_conflict", description="红灯、横穿行人与继续行驶命令同时出现。",
        commands=[command(0, "不用停，继续往前开", "KEEP_LANE", speed_kph=18)],
        actors=[red_light(20), walker("ped_001", 18, start_time_s=4)], duration_s=40,
        expected={"must_no_pedestrian_collision": True, "must_stop_before_stop_line": True,
                  "required_real_actor_types": ["walker.pedestrian"], "expected_safety_override": True,
                  "safety_priority_over_command": True,
                  "expected_reason_contains": ["red", "pedestrian", "stop"], "must_generate_event": True},
        oracle_behaviors=["STOP"], seed=201,
    ))
    add(scenario(
        "CX02_multi_vehicle_target_follow_brake", "complex", priority="P2", category="regression", level="challenge",
        capability="multi_target_follow_brake", description="三车目标选择后，正前方目标在 8 秒急刹。",
        commands=[command(0, "跟随正前方同车道车辆并保持安全距离", "KEEP_LANE", speed_kph=20)],
        actors=[vehicle("lead_target", 26, speed_mps=4.0, brake_at_s=8, target_speed_mps=0.2),
                vehicle("distractor_left", 21, 3.5, speed_mps=3.0, blueprint_id="vehicle.tesla.model3"),
                vehicle("distractor_right", 31, -3.5, speed_mps=3.5, blueprint_id="vehicle.lincoln.mkz_2020")],
        duration_s=42, expected={"required_real_actor_types": ["vehicle"],
                  "min_front_gap_m": 2.5, "expected_safety_override_allowed": True},
        oracle_behaviors=["FOLLOW", "SLOW_DOWN", "STOP"], expected_target_actor_id="lead_target", seed=202,
        proposed_acceptance={"expected_target_actor_id": "lead_target"},
        extension_requirements=["qwen_target_binding_acceptance"],
    ))
    add(scenario(
        "CX03_construction_bicycle_detour", "complex", priority="P2", category="regression", level="challenge",
        capability="construction_bicycle_detour", description="施工障碍、低速自行车和预设绕行路线组合。",
        commands=[command(0, "从左侧安全绕过施工区域和慢速自行车", "KEEP_LANE", speed_kph=14)],
        route=DETOUR_RETURN,
        actors=[prop("work_zone", 30, 0),
                vehicle("bicycle_lead", 24, speed_mps=2.2, brake_at_s=9, target_speed_mps=0.3,
                        blueprint_id="vehicle.bh.crossbike")],
        expected={"required_real_actor_types": ["vehicle", "static.prop"],
                  "min_front_gap_m": 2.5, "expected_safety_override_allowed": True},
        oracle_behaviors=["AVOID_OBSTACLE", "CHANGE_LANE_LEFT", "RETURN_TO_LANE"], seed=203,
        proposed_acceptance={"must_return_to_original_lane": True},
    ))
    add(scenario(
        "CX04_heavy_rain_ambiguous_multi_target", "complex", priority="P2", category="regression", level="challenge",
        capability="rain_ambiguous_multi_target", description="大雨、模糊命令、两辆前车和路边行人组合。",
        commands=[command(0, "前面有点乱，安全处理", "SLOW_DOWN", status="ambiguous", confirm_required=True)],
        actors=[vehicle("lead_target", 26, speed_mps=2.5),
                vehicle("distractor_left", 22, 3.5, speed_mps=3.0, blueprint_id="vehicle.tesla.model3"),
                walker("roadside_ped", 34, -4.5, -3.5, start_time_s=30, speed_mps=0.5)],
        weather="HardRainNoon", duration_s=45,
        expected={"required_real_actor_types": ["vehicle", "walker.pedestrian"],
                  "min_front_gap_m": 2.5, "expected_safety_override_allowed": True},
        oracle_behaviors=["SLOW_DOWN", "STOP", "HOLD"], expected_target_actor_id="lead_target", seed=204,
        proposed_acceptance={"must_call_qwen": True, "expected_target_actor_id": "lead_target"},
        extension_requirements=["raw_text_qwen_routing", "qwen_target_binding_acceptance"],
    ))
    add(scenario(
        "CX05_sensor_dropout_route_recovery", "complex", priority="P2", category="regression", level="challenge",
        capability="sensor_dropout_route_recovery", description="缓弯上相机失效，随后注入转向偏置并检查恢复。",
        commands=[command(0, "保持车道，感知或路线异常时安全处理", "KEEP_LANE", speed_kph=12)],
        route=SMOOTH_CURVE,
        faults=[fault("rgb_blackout", "sensor_blackout", 8, 4, sensor="front_rgb"),
                fault("steer_bias", "steer_bias", 15, 0.8, value=0.25)],
        duration_s=45, expected={"max_allowed_cross_track_error_m": 2.5,
                  "expected_safety_override_allowed": True},
        oracle_behaviors=["KEEP_LANE", "SLOW_DOWN", "STOP"], seed=205,
        proposed_acceptance={"must_recover_after_fault": True, "max_fault_response_s": 1.0},
        extension_requirements=["fault_injection", "fault_recovery_acceptance"],
    ))
    add(scenario(
        "CX06_multi_command_full_trip", "complex", priority="P2", category="regression", level="challenge",
        capability="multi_command_trip", description="启动、定速、跟车、减速、红灯停车和终点停车的完整命令链。",
        commands=[command(0, "开始行驶并保持车道", "KEEP_LANE", speed_kph=12),
                  command(8, "将速度设置为二十公里每小时", "SET_SPEED", speed_kph=20),
                  command(25, "跟随正前方车辆", "KEEP_LANE", speed_kph=18),
                  command(50, "减速到十公里每小时", "SET_SPEED", speed_kph=10),
                  command(75, "红灯前停车", "STOP"),
                  command(95, "重新启动并保持车道", "KEEP_LANE", speed_kph=12),
                  command(125, "到终点停车", "STOP")],
        route=MIXED_ROUTE,
        actors=[
            vehicle("lead_001", 35, speed_mps=3.0),
            {
                **red_light(75),
                "state": "green",
                "behavior": {
                    "mode": "state_timeline",
                    "states": [
                        {"time_s": 65, "state": "red"},
                        {"time_s": 90, "state": "green"},
                    ],
                },
            },
        ],
        duration_s=145,
        expected={"must_execute_commands_in_order": True, "must_stop_after_last_command": True,
                  "stop_speed_threshold_mps": 0.2, "required_real_actor_types": ["vehicle"],
                  "expected_safety_override_allowed": True},
        oracle_behaviors=["START", "SET_SPEED", "FOLLOW", "SLOW_DOWN", "STOP", "KEEP_LANE"], seed=206,
        proposed_acceptance={"qwen_command_count": 7, "qwen_stale_rejection_count": 0},
        extension_requirements=["multi_command_qwen", "command_queue_policy", "actor_state_timeline"],
    ))

    # P3 / stability
    add(scenario(
        "STB01_60min_mixed_cycle", "stability", priority="P3", category="regression", level="challenge",
        capability="long_stability", description="60 分钟混合命令、感知、控制、安全和恢复探针。",
        commands=[command(0, "开始稳定性循环并保持车道", "KEEP_LANE", speed_kph=15),
                  command(600, "减速到十公里每小时", "SET_SPEED", speed_kph=10),
                  command(1200, "恢复十五公里每小时", "SET_SPEED", speed_kph=15),
                  command(1800, "慢一点", "SLOW_DOWN"),
                  command(2400, "恢复十五公里每小时", "SET_SPEED", speed_kph=15),
                  command(3000, "平稳停车", "STOP"),
                  command(3020, "重新开始并保持车道", "KEEP_LANE", speed_kph=15),
                  command(3570, "结束测试并停车", "STOP")],
        route=MIXED_ROUTE, duration_s=3600,
        expected={"min_run_time_s": 3590, "must_execute_commands_in_order": True,
                  "must_stop_after_last_command": True, "stop_speed_threshold_mps": 0.2,
                  "max_cross_track_error_m": 1.5},
        oracle_behaviors=["KEEP_LANE", "SET_SPEED", "SLOW_DOWN", "STOP"], seed=301,
        extension_values={"route_policy": {"loop": True}},
        proposed_acceptance={"qwen_command_count": 8, "max_resource_growth_mb": 512},
        extension_requirements=["multi_command_qwen", "loop_route", "resource_stability_metrics"],
    ))

    return s


def matrix(entries: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {
        "total": len(entries),
        "P0": sum(item["priority"] == "P0" for item in entries),
        "P1": sum(item["priority"] == "P1" for item in entries),
        "P2": sum(item["priority"] == "P2" for item in entries),
        "P3": sum(item["priority"] == "P3" for item in entries),
        "basic": sum(item["official_level"] == "basic" for item in entries),
        "advanced": sum(item["official_level"] == "advanced" for item in entries),
        "challenge": sum(item["official_level"] == "challenge" for item in entries),
        "current_runtime": sum(item["runtime_support"]["status"] == "current" for item in entries),
        "extension_required": sum(item["runtime_support"]["status"] == "extension_required" for item in entries),
    }
    return {
        "schema_version": "1.0",
        "suite_version": SUITE_VERSION,
        "description": "东风赛道 CARLA 高质量场景库 43 场景验收矩阵。",
        "formal_runtime": {
            "perception_mode": "sensors",
            "scenario_facts_mode": "perception",
            "qwen_invocation": "once_per_voice_event",
            "safety_events_wait_for_qwen": False,
        },
        "counts": counts,
        "scenarios": entries,
    }


def render_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify generated files are current without writing them",
    )
    args = parser.parse_args()
    scenarios = build_scenarios()
    if len(scenarios) != 43:
        raise RuntimeError(f"suite must contain 43 scenarios, got {len(scenarios)}")
    ids = [data["scenario_id"] for _, data, _ in scenarios]
    if len(ids) != len(set(ids)):
        raise RuntimeError("scenario_id values must be unique")

    outputs = {SUITE_ROOT / path: render_json(data) for path, data, _ in scenarios}
    outputs[SUITE_ROOT / "matrix.json"] = render_json(matrix([entry for _, _, entry in scenarios]))
    stale: list[Path] = []
    for path, content in outputs.items():
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(path)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    if stale:
        for path in stale:
            print(f"stale: {path.relative_to(REPO_ROOT)}")
        return 1
    action = "checked" if args.check else "wrote"
    print(f"{action} {len(scenarios)} scenarios and matrix.json under {SUITE_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
