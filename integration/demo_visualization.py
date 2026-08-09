"""Read-only Chinese demonstration UI for the CARLA acceptance runner.

The presentation layer consumes snapshots produced by the existing runtime.  It
never owns a CARLA world, advances simulation time, or writes vehicle control.
Rendering runs on a latest-frame-wins worker so a slow display may drop frames
without delaying the control loop.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import queue
import threading
import time
from typing import Any, Mapping, Sequence

from PIL import Image, ImageDraw, ImageFont, ImageOps


ACTION_CN: Mapping[str, str] = {
    "START": "起步行驶",
    "SET_SPEED": "设置速度",
    "SLOW_DOWN": "降低车速",
    "SPEED_UP": "提高车速",
    "KEEP_LANE": "保持当前车道",
    "FOLLOW_ROUTE": "沿规划路线行驶",
    "STOP": "停车",
    "EMERGENCY_STOP": "紧急停车",
    "FOLLOW": "跟随前车",
    "YIELD": "主动让行",
    "AVOID_OBSTACLE": "绕过前方障碍",
    "CHANGE_LANE": "安全变道",
    "CHANGE_LANE_LEFT": "向左变道",
    "CHANGE_LANE_RIGHT": "向右变道",
    "TURN": "转向行驶",
    "TURN_LEFT": "左转",
    "TURN_RIGHT": "右转",
    "RETURN_TO_LANE": "返回原车道",
    "PULL_OVER": "靠边停车",
    "HOLD": "停车等待",
}

SAFETY_REASON_CN: Mapping[str, str] = {
    "NONE": "运行正常",
    "RED_LIGHT": "前方红灯",
    "RED_LIGHT_STOP_LINE_GUARD": "红灯禁止通行",
    "LOW_TTC": "碰撞风险过高",
    "RISK_EMERGENCY_BRAKE_REQUESTED": "碰撞风险过高",
    "EMERGENCY_FRONT_OBSTACLE_TOO_CLOSE": "前方障碍距离过近",
    "COLLISION_DETECTED": "检测到碰撞",
    "PEDESTRIAN": "前方行人",
    "SENSOR_STALE": "感知信息失效",
    "SCENARIO_PERCEPTION_INSUFFICIENT": "摄像头与 LiDAR 均失效",
    "SCENARIO_SINGLE_SENSOR_DEGRADED_SPEED_CAP": "单传感器失效，降级限速",
    "QWEN_TIMEOUT": "AI 决策超时",
    "QWEN_ERROR": "AI 决策失败",
    "QWEN_SAFETY_RULE": "AI 识别到安全冲突",
    "TARGET_LOST": "目标丢失",
    "INVALID_CONTROL": "控制输出异常",
    "WATCHDOG_ALERT": "运行状态异常",
    "RUNTIME_WATCHDOG_TIMEOUT": "运行模块响应超时",
    "PERCEPTION_STARTUP_GRACE": "感知系统正在启动",
    "C_VRU_SPEED_CAP_BRAKE": "弱势道路参与者风险",
    "C_FRONT_HAZARD_FAIL_CLOSED": "前方风险，安全停车",
}

SCENE_CN: Mapping[str, str] = {
    "ACC_A01_LEAD_BRAKE": "前车急刹安全处理",
    "ACC_A02_RED_LIGHT_CONFLICT": "红灯冲突安全处理",
    "ACC_A03_PEDESTRIAN_CROSSING": "行人横穿安全处理",
    "ACC_A04_STATIC_OBSTACLE_STOP": "静态障碍安全处理",
    "ACC_A05_LANE_CHANGE_LEFT": "安全变道",
    "ACC_A06_OBSTACLE_DETOUR_RETURN": "施工障碍绕行",
    "CX01_URBAN_INTERSECTION_CONFLICT": "城市路口冲突处理",
    "CX02_MULTI_VEHICLE_TARGET_FOLLOW_BRAKE": "多目标跟车",
    "CX03_CONSTRUCTION_BICYCLE_DETOUR": "施工区域绕行",
    "CX04_HEAVY_RAIN_AMBIGUOUS_MULTI_TARGET": "雨天多目标判断",
    "CX05_SENSOR_DROPOUT_ROUTE_RECOVERY": "感知故障降级恢复",
    "VAR_A01_LEAD_BRAKE_LATE": "前车急刹安全处理",
    "VAR_A02_LOW_TTC_STATIONARY_LEAD": "低碰撞时间安全处理",
    "VAR_A03_OCCLUDED_PEDESTRIAN": "遮挡行人安全处理",
    "VAR_A06_RED_LIGHT_WET_WEATHER": "雨天红灯安全处理",
    "VAR_C03_MULTI_TARGET_PARTIAL_OCCLUSION": "多目标遮挡判断",
    "VAR_C04_RGB_BLACKOUT_LIDAR_ALIVE": "摄像头故障降级运行",
    "VAR_C05_RGB_LIDAR_BLACKOUT": "多传感器故障安全停车",
    "QWX_01_MODEL_TIMEOUT": "AI 决策超时保护",
    "QWX_06_PEDESTRIAN_SAFETY_OVERRIDE": "行人风险安全接管",
    "D03_FRONT_VEHICLE_BRAKE": "前车急刹安全处理",
    "D08_COMMAND_CONFLICT_RED_LIGHT_CONTINUE": "红灯指令冲突",
    "RED_STOP": "红灯停车",
    "FOLLOW": "安全跟车",
    "EMERGENCY": "紧急制动",
    "CRUISE": "语音驾驶控制",
}

LANGUAGE_CN: Mapping[str, str] = {
    "zh": "普通话",
    "zh-cn": "普通话",
    "mandarin": "普通话",
    "cantonese": "粤语",
    "yue": "粤语",
    "dongbei": "东北话",
    "shaanxi": "陕西话",
    "taiwan": "台湾国语",
}

OBJECT_CN: Mapping[str, str] = {
    "car": "车辆",
    "vehicle": "车辆",
    "truck": "货车",
    "bus": "公交车",
    "person": "行人",
    "pedestrian": "行人",
    "bicycle": "自行车",
    "cyclist": "骑行者",
    "motorcycle": "摩托车",
    "obstacle": "障碍物",
    "traffic_light": "交通灯",
}

TERMINAL_CN: Mapping[str, str] = {
    "SUCCEEDED": "已完成",
    "FAILED": "执行失败",
    "REJECTED": "指令已拒绝",
    "EXPIRED": "指令已过期",
    "TIMED_OUT": "执行超时",
    "SAFETY_OVERRIDE": "安全停车",
}

TIMELINE_LABELS = ("语音输入", "识别完成", "Qwen 决策", "安全校验", "车辆执行")


@dataclass(frozen=True, slots=True)
class DemoObject:
    class_name_cn: str
    bbox_xyxy_norm: tuple[float, float, float, float]
    distance_m: float | None = None
    selected: bool = False


@dataclass(frozen=True, slots=True)
class DemoState:
    scene_name_cn: str
    scene_id: str
    voice_language: str = ""
    voice_text: str = "暂无语音"
    asr_text: str = ""
    intent_text: str = "等待语音指令"
    qwen_status: str = "等待语音"
    qwen_action_cn: str = "暂无决策"
    qwen_target_cn: str = ""
    qwen_reason_cn: str = ""
    perception_summary: tuple[str, ...] = ("道路：等待场景数据",)
    risk_level: str = "normal"
    safety_status: str = "正常"
    safety_reason_cn: str = "未触发安全接管"
    vehicle_speed_kmh: float = 0.0
    vehicle_target_speed_kmh: float | None = None
    vehicle_action_cn: str = "等待指令"
    execution_status: str = "等待中"
    timeline_index: int = 0
    timeline_override: bool = False
    objects: tuple[DemoObject, ...] = ()
    debug_lines: tuple[str, ...] = ()


def _enum(value: object) -> str:
    return str(getattr(value, "value", value or "")).strip().upper()


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _action_cn(value: object) -> str:
    action = _enum(value)
    return ACTION_CN.get(action, action.replace("_", " ") if action else "暂无")


def _sensor_cn(sensor: str) -> str:
    key = sensor.strip().lower()
    if key in {"front_rgb", "rgb", "camera"}:
        return "摄像头"
    if key in {"lidar", "lidar_roof"}:
        return "LiDAR"
    if key in {"radar", "radar_front"}:
        return "雷达"
    return "感知传感器"


def _scene_name(scene_id: str) -> str:
    normalized = scene_id.strip().upper()
    if normalized in SCENE_CN:
        return SCENE_CN[normalized]
    tokens = set(normalized.split("_"))
    if "RED" in tokens and "LIGHT" in tokens:
        return "红灯冲突安全处理"
    if "PEDESTRIAN" in tokens:
        return "行人横穿安全处理"
    if "MULTI" in tokens and ("TARGET" in tokens or "VEHICLE" in tokens):
        return "多目标跟车"
    if "SENSOR" in tokens or "BLACKOUT" in tokens or "DROPOUT" in tokens:
        return "感知故障降级运行"
    if "OBSTACLE" in tokens or "CONSTRUCTION" in tokens:
        return "障碍物安全处理"
    if "BRAKE" in tokens or "TTC" in tokens:
        return "动态风险安全处理"
    if "LANE" in tokens and "CHANGE" in tokens:
        return "安全变道"
    if "DEVIATION" in tokens or "OFFSET" in tokens:
        return "车道偏离恢复"
    if "ASR" in tokens or "VOICE" in tokens:
        return "语音识别安全处理"
    if "QWEN" in tokens or "MODEL" in tokens:
        return "AI 故障安全保护"
    if "RAIN" in tokens or "FOG" in tokens or "WEATHER" in tokens:
        return "复杂天气安全驾驶"
    if "ILLEGAL" in tokens or "INVALID" in tokens or "CONFLICT" in tokens:
        return "冲突指令安全处理"
    if "EMERGENCY" in tokens:
        return "紧急停车"
    if "SLOW" in tokens:
        return "语音减速控制"
    if "SPEED" in tokens:
        return "语音定速控制"
    if "STOP" in tokens:
        return "语音停车控制"
    if "START" in tokens:
        return "起步与车道保持"
    return "CARLA 语音驾驶演示"


class DemoStatePresenter:
    """Translate actual runtime events into a stable, judge-facing snapshot."""

    def __init__(self, scene_id: str) -> None:
        self.scene_id = scene_id
        self.scene_name_cn = _scene_name(scene_id)
        self._voice: dict[str, Any] = {}
        self._qwen_status = "WAITING"
        self._decision: dict[str, Any] = {}
        self._target_id: str | None = None
        self._terminal_status: str | None = None
        self._terminal_at_s: float | None = None
        self._safety_reason: str | None = None
        self._safety_hold_until_s = -1.0
        self._display_speed_kmh: float | None = None
        self._voice_prompt = ""

    def note_voice_prompt(self, source_text: str) -> None:
        prompt = str(source_text).strip()
        if not prompt:
            return
        self._voice_prompt = prompt
        self._voice = {}
        self._qwen_status = "WAITING"
        self._decision = {}
        self._target_id = None

    def note_voice(self, envelope: Mapping[str, Any] | None) -> None:
        if not envelope:
            return
        self._voice_prompt = ""
        self._voice = dict(envelope)
        self._qwen_status = "RECEIVED"
        self._decision = {}
        self._target_id = None
        self._terminal_status = None
        self._terminal_at_s = None
        self._safety_reason = None
        self._safety_hold_until_s = -1.0

    def note_qwen(self, status: str, decision: Mapping[str, Any] | None = None) -> None:
        normalized = _enum(status)
        aliases = {
            "SLOW_PENDING": "PENDING",
            "FAST": "READY",
            "CONFIRM_SAFE": "CONFIRM",
            "SLOW_READY": "READY",
            "TIMED_OUT": "TIMEOUT",
        }
        self._qwen_status = aliases.get(normalized, normalized or self._qwen_status)
        if decision:
            self._decision = dict(decision)
            target = _mapping(self._decision.get("target"))
            self._target_id = str(
                target.get("target_id")
                or self._decision.get("target_id")
                or ""
            ) or None

    def note_local_decision(self, envelope: Mapping[str, Any]) -> None:
        """Record a real fast-path decision without claiming Qwen inference."""
        self._qwen_status = "DISABLED"
        self._decision = {
            "action": envelope.get("intent"),
            "target": _mapping(envelope.get("parameters")).get("target", {}),
        }

    def note_orchestration(
        self, orchestration: object | None, *, now_s: float | None = None,
    ) -> None:
        if orchestration is None:
            return
        disposition = _enum(getattr(orchestration, "disposition", ""))
        decision = (
            getattr(orchestration, "decision_plan", None)
            or getattr(orchestration, "control_command", None)
        )
        control = _mapping(getattr(orchestration, "control_command", None))
        source = _enum(control.get("source"))
        if disposition == "FAST" and source != "QWEN_DECISION_PLAN":
            self.note_qwen("NOT_USED", decision)
        else:
            self.note_qwen(disposition, decision)
        if disposition in {"REJECTED", "ERROR", "TIMEOUT"}:
            self._decision.setdefault(
                "reason", getattr(orchestration, "reason_code", disposition),
            )
        feedback = _mapping(getattr(orchestration, "feedback", None))
        if _enum(feedback.get("status")) == "SAFETY_OVERRIDE" and now_s is not None:
            safety_event = _mapping(feedback.get("safety_event"))
            self._safety_reason = _enum(
                safety_event.get("reason_code")
                or getattr(orchestration, "reason_code", "SAFETY_OVERRIDE")
            )
            self._safety_hold_until_s = now_s + 2.0

    def note_feedback(self, feedbacks: Sequence[object], now_s: float) -> None:
        for feedback in feedbacks:
            status = (
                feedback.get("status")
                if isinstance(feedback, Mapping)
                else getattr(feedback, "status", None)
            )
            command_id = (
                feedback.get("command_id")
                if isinstance(feedback, Mapping)
                else getattr(feedback, "command_id", None)
            )
            normalized = _enum(status)
            # The internal qwen-wait command intentionally terminates as
            # FAILED when the real model result takes over.  It is an audit
            # marker for releasing the temporary stop, not a failed user
            # command, so surfacing it as “执行失败” is misleading.
            if normalized == "FAILED" and str(command_id or "").startswith("qwen-wait-"):
                continue
            if normalized in TERMINAL_CN:
                self._terminal_status = normalized
                self._terminal_at_s = now_s

    def _language(self) -> str:
        raw = str(
            self._voice.get("language")
            or self._voice.get("lang")
            or self._voice.get("dialect")
            or ""
        ).strip()
        return LANGUAGE_CN.get(raw.lower(), raw)

    def _intent_text(self) -> str:
        if not self._voice:
            return "等待语音指令"
        intent = _enum(self._voice.get("intent"))
        if not intent:
            return "正在理解语音含义"
        action = _action_cn(intent)
        params = _mapping(self._voice.get("parameters"))
        speed = params.get("target_speed_kph")
        if speed is None and params.get("target_speed_mps") is not None:
            speed = float(params["target_speed_mps"]) * 3.6
        direction = _enum(params.get("direction"))
        if intent in {"SET_SPEED", "START"} and speed is not None:
            return f"目标速度：{float(speed):.0f} km/h"
        if intent in {"CHANGE_LANE", "AVOID_OBSTACLE", "TURN"} and direction:
            direction_cn = {"LEFT": "左侧", "RIGHT": "右侧"}.get(direction, "安全方向")
            if intent == "AVOID_OBSTACLE":
                return f"从{direction_cn}绕过前方障碍"
            if intent == "CHANGE_LANE":
                return f"向{direction_cn}变道"
        return action

    def _decision_lines(self) -> tuple[str, str, str]:
        decision = self._decision
        action = (
            decision.get("action")
            or decision.get("behavior")
            or decision.get("intent")
        )
        if action is None:
            steps = decision.get("steps")
            if isinstance(steps, Sequence) and not isinstance(steps, (str, bytes)) and steps:
                first = steps[0]
                if isinstance(first, Mapping):
                    action = first.get("behavior") or first.get("action")
        action_cn = _action_cn(action) if action else (
            self._intent_text() if self._qwen_status == "READY" else "暂无决策"
        )
        target = _mapping(decision.get("target"))
        target_text = str(
            target.get("description")
            or decision.get("target_description")
            or ""
        ).strip()
        if not target_text and self._target_id:
            target_text = "当前选定道路目标"
        reason = str(
            decision.get("reason_cn")
            or decision.get("reason")
            or decision.get("rationale")
            or decision.get("strategy")
            or decision.get("reason_code")
            or ""
        ).strip()
        if "_" in reason and " " not in reason:
            reason = SAFETY_REASON_CN.get(reason.upper(), "已结合当前道路信息完成判断")
        return action_cn, target_text, reason

    def build(
        self,
        *,
        scene: object,
        vehicle: object,
        result: object,
        target_speed_mps: float | None,
        perception_sources: Mapping[str, str] | None,
        active_faults: Sequence[Mapping[str, Any]] = (),
        execution_state: str = "",
        active_command: bool = False,
        now_s: float = 0.0,
        debug: bool = False,
    ) -> DemoState:
        feedback = tuple(getattr(result, "feedback", ()) or ())
        self.note_feedback(feedback, now_s)
        speed_mps = float(getattr(vehicle, "speed_mps", 0.0))
        measured_speed_kmh = speed_mps * 3.6
        self._display_speed_kmh = (
            measured_speed_kmh
            if self._display_speed_kmh is None
            else 0.35 * measured_speed_kmh + 0.65 * self._display_speed_kmh
        )
        scene_objects = tuple(getattr(scene, "detected_objects", ()) or ())

        fault_sensors = {
            str(item.get("sensor", ""))
            for item in active_faults
            if str(item.get("type", "")).lower() in {"sensor_blackout", "sensor_stale"}
        }
        perception: list[str] = []
        if fault_sensors:
            for sensor in sorted(fault_sensors):
                perception.append(f"{_sensor_cn(sensor)}：失效")
            known = {"摄像头", "LiDAR"}
            failed_cn = {_sensor_cn(item) for item in fault_sensors}
            for sensor_cn in sorted(known - failed_cn):
                perception.append(f"{sensor_cn}：正常")
            perception.append("系统：降级运行")
        elif perception_sources and "failure" in perception_sources:
            perception.extend(("感知数据：失效", "系统：安全降级"))
        else:
            light = _enum(getattr(scene, "traffic_light", "UNKNOWN"))
            stop_distance = getattr(scene, "distance_to_stop_line_m", None)
            if light != "UNKNOWN":
                light_cn = {"RED": "红灯", "YELLOW": "黄灯", "GREEN": "绿灯"}.get(light, light)
                perception.append(f"交通灯：{light_cn}")
                if stop_distance is not None:
                    perception.append(f"停止线：{float(stop_distance):.1f} m")
            lead_distance = getattr(scene, "lead_distance_m", None)
            lead_speed = getattr(scene, "lead_speed_mps", None)
            if lead_distance is not None:
                perception.append(f"前方目标：{float(lead_distance):.1f} m")
                if lead_speed is not None:
                    relative = float(lead_speed) - speed_mps
                    if relative < -0.8:
                        perception.append(f"相对速度：{relative:.1f} m/s")
            if len(scene_objects) > 1:
                perception.insert(0, f"候选目标：{len(scene_objects)}")
            if getattr(scene, "collision", False):
                perception.insert(0, "碰撞事件：已触发")
            if not perception:
                perception.extend(("道路：当前车道正常", "前方：无高风险目标"))
        perception = perception[:4]

        qwen_map = {
            "WAITING": "等待语音",
            "RECEIVED": "已接收",
            "PENDING": "推理中",
            "READY": "决策完成",
            "TIMEOUT": "响应超时",
            "STALE": "结果已过期",
            "ERROR": "决策失败",
            "REJECTED": "决策已拒绝",
            "CONFIRM": "等待安全确认",
            "NOT_USED": "快速路径，无需推理",
            "NOT_SUBMITTED": "等待语音",
            "DISABLED": "未启用",
            "CANONICAL_READY": "等待语音",
        }
        qwen_cn = qwen_map.get(self._qwen_status, self._qwen_status or "等待语音")
        action_cn, target_cn, reason_cn = self._decision_lines()
        if self._qwen_status in {"TIMEOUT", "ERROR", "STALE", "REJECTED", "CONFIRM"}:
            action_cn = "保持安全状态"
            reason_cn = (
                "需要明确安全指令"
                if self._qwen_status == "CONFIRM"
                else "未获得可执行的 AI 决策"
            )

        safety_override = bool(getattr(result, "safety_override", False))
        safety_reason = _enum(getattr(result, "safety_reason", "NONE"))
        if safety_override:
            self._safety_reason = safety_reason
            self._safety_hold_until_s = now_s + 2.0
        safety_event_visible = safety_override or now_s <= self._safety_hold_until_s
        displayed_safety_reason = self._safety_reason or safety_reason
        longitudinal = getattr(result, "longitudinal", None)
        ttc_s = None
        if longitudinal is not None:
            risk = getattr(longitudinal, "risk", None)
            ttc_s = getattr(risk, "ttc_s", None)
        risk_level = "danger" if safety_event_visible else "warning" if ttc_s is not None and ttc_s < 4.0 else "normal"
        if safety_event_visible:
            safety_status = "安全接管"
            safety_cn = SAFETY_REASON_CN.get(
                displayed_safety_reason, "检测到风险，安全动作优先",
            )
        elif risk_level == "warning":
            safety_status = "风险提示"
            safety_cn = f"预计碰撞时间：{float(ttc_s):.1f} s"
        else:
            safety_status = "安全监督"
            safety_cn = "正常"

        longitudinal_state = _enum(getattr(longitudinal, "state", ""))
        if self._qwen_status == "PENDING":
            vehicle_action = "停车等待"
        elif safety_override:
            vehicle_action = "安全停车" if speed_mps < 0.3 else "安全制动"
        elif longitudinal_state in {"BRAKING", "DECELERATING", "SLOW_DOWN"}:
            vehicle_action = "减速"
        elif longitudinal_state in {"ACCELERATING", "SPEED_UP"}:
            vehicle_action = "加速"
        elif self._decision:
            vehicle_action = action_cn
        elif self._voice:
            vehicle_action = self._intent_text()
        else:
            vehicle_action = "等待指令"

        terminal_visible = (
            self._terminal_status is not None
            and self._terminal_at_s is not None
            and now_s - self._terminal_at_s <= 3.0
        )
        if self._qwen_status == "PENDING":
            execution_status = "等待 AI 决策"
        elif terminal_visible:
            execution_status = TERMINAL_CN[self._terminal_status or "FAILED"]
        elif active_command:
            execution_status = "执行中"
        elif self._voice:
            execution_status = "等待执行"
        else:
            execution_status = "等待中"

        if not self._voice:
            timeline_index = 0
        elif self._qwen_status in {"RECEIVED", "PENDING"}:
            timeline_index = 2
        elif self._qwen_status in {"TIMEOUT", "ERROR", "STALE"}:
            timeline_index = 3
        else:
            timeline_index = 4 if active_command or terminal_visible else 3

        objects: list[DemoObject] = []
        nearest_index = None
        nearest_distance = float("inf")
        for index, item in enumerate(scene_objects):
            distance = getattr(item, "distance_m", None)
            track_id = str(getattr(item, "track_id", "") or "")
            selected = bool(self._target_id and track_id == self._target_id)
            if distance is not None and float(distance) < nearest_distance:
                nearest_distance, nearest_index = float(distance), index
            objects.append(DemoObject(
                OBJECT_CN.get(str(getattr(item, "class_name", "object")).lower(), "道路目标"),
                tuple(getattr(item, "bbox_xyxy_norm")),
                None if distance is None else float(distance),
                selected,
            ))
        if objects and not any(item.selected for item in objects) and nearest_index is not None:
            selected = objects[nearest_index]
            objects[nearest_index] = DemoObject(
                selected.class_name_cn, selected.bbox_xyxy_norm,
                selected.distance_m, True,
            )

        debug_lines: tuple[str, ...] = ()
        if debug:
            final_control = getattr(result, "final_control", None)
            debug_lines = (
                f"frame={getattr(scene, 'frame', 'N/A')}",
                f"fsm={execution_state or 'N/A'}",
                f"command_id={getattr(result, 'command_id', 'N/A')}",
                f"throttle={getattr(final_control, 'throttle', 0.0):.3f}  "
                f"brake={getattr(final_control, 'brake', 0.0):.3f}  "
                f"steer={getattr(final_control, 'steer', 0.0):.3f}",
                f"safety={safety_reason}",
            )

        source_text = str(
            self._voice.get("source_text")
            or (f"请说：{self._voice_prompt}" if self._voice_prompt else "暂无语音")
        ).strip()
        asr_text = str(self._voice.get("asr_text") or "").strip()
        if asr_text == source_text:
            asr_text = ""
        return DemoState(
            scene_name_cn=self.scene_name_cn,
            scene_id=(
                "_".join(self.scene_id.split("_")[:2])
                if self.scene_id else ""
            ),
            voice_language=self._language(),
            voice_text=source_text,
            asr_text=asr_text,
            intent_text=(
                "麦克风已就绪，等待实时语音输入"
                if self._voice_prompt and not self._voice
                else self._intent_text()
            ),
            qwen_status=qwen_cn,
            qwen_action_cn=action_cn,
            qwen_target_cn=target_cn,
            qwen_reason_cn=reason_cn,
            perception_summary=tuple(perception),
            risk_level=risk_level,
            safety_status=safety_status,
            safety_reason_cn=safety_cn,
            vehicle_speed_kmh=self._display_speed_kmh,
            vehicle_target_speed_kmh=(
                None if target_speed_mps is None else float(target_speed_mps) * 3.6
            ),
            vehicle_action_cn=vehicle_action,
            execution_status=execution_status,
            timeline_index=timeline_index,
            timeline_override=safety_event_visible,
            objects=tuple(objects),
            debug_lines=debug_lines,
        )


@dataclass(frozen=True, slots=True)
class _Palette:
    canvas: str = "#EEF2F5"
    panel: str = "#F7F9FB"
    card: str = "#FFFFFF"
    text: str = "#17212B"
    muted: str = "#697681"
    line: str = "#DCE3E8"
    cyan: str = "#168E9B"
    blue: str = "#3778C2"
    purple: str = "#7356A5"
    green: str = "#2B8A68"
    orange: str = "#D3832E"
    red: str = "#C84C4C"
    inactive: str = "#B7C0C8"


class DemoFrameRenderer:
    """Pure Pillow renderer; usable in tests and by the async live display."""

    WIDTH = 1920
    HEIGHT = 1080
    MAIN_WIDTH = 1380
    PANEL_WIDTH = WIDTH - MAIN_WIDTH
    TIMELINE_HEIGHT = 96

    def __init__(self, *, debug: bool = False) -> None:
        self.debug = debug
        self.colors = _Palette()
        self._fonts: dict[tuple[int, bool], ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}
        self._font_paths = self._find_fonts()

    @staticmethod
    def _find_fonts() -> tuple[Path | None, Path | None]:
        regular_candidates = (
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc"),
            Path("C:/Windows/Fonts/msyh.ttc"),
        )
        bold_candidates = (
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
            Path("/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc"),
            Path("C:/Windows/Fonts/msyhbd.ttc"),
        )
        regular = next((item for item in regular_candidates if item.is_file()), None)
        bold = next((item for item in bold_candidates if item.is_file()), regular)
        return regular, bold

    def _font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        key = (size, bold)
        if key not in self._fonts:
            path = self._font_paths[1 if bold else 0]
            self._fonts[key] = (
                ImageFont.truetype(str(path), size=size, layout_engine=ImageFont.Layout.BASIC)
                if path is not None else ImageFont.load_default()
            )
        return self._fonts[key]

    @staticmethod
    def camera_image(rgb: object | None) -> Image.Image | None:
        if rgb is None:
            return None
        if isinstance(rgb, Image.Image):
            return rgb.convert("RGB")
        width, height = getattr(rgb, "width", None), getattr(rgb, "height", None)
        raw_data = getattr(rgb, "raw_data", None)
        if isinstance(width, int) and isinstance(height, int) and raw_data is not None:
            raw = bytes(raw_data)
            expected = width * height * 4
            if len(raw) != expected:
                raise ValueError(f"RGB frame has {len(raw)} bytes, expected {expected}")
            return Image.frombuffer(
                "RGBA", (width, height), raw, "raw", "BGRA", 0, 1,
            ).convert("RGB")
        raise TypeError("RGB input must be a PIL image or CARLA image measurement")

    def _fit_camera(self, rgb: Image.Image | None, size: tuple[int, int]) -> Image.Image:
        if rgb is None:
            image = Image.new("RGB", size, "#29343D")
            draw = ImageDraw.Draw(image)
            text = "等待 CARLA RGB 画面"
            box = draw.textbbox((0, 0), text, font=self._font(28, True))
            draw.text(
                ((size[0] - (box[2] - box[0])) / 2, (size[1] - (box[3] - box[1])) / 2),
                text, fill="#DCE3E8", font=self._font(28, True),
            )
            return image
        return ImageOps.fit(rgb, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))

    @staticmethod
    def _wrap(text: str, limit: int) -> list[str]:
        if not text:
            return []
        lines: list[str] = []
        current = ""
        for char in text:
            width = 1 if ord(char) < 128 else 2
            used = sum(1 if ord(item) < 128 else 2 for item in current)
            if current and used + width > limit:
                lines.append(current)
                current = char
            else:
                current += char
        if current:
            lines.append(current)
        return lines

    def _card(
        self,
        draw: ImageDraw.ImageDraw,
        box: tuple[int, int, int, int],
        title: str,
        lines: Sequence[str],
        *,
        accent: str,
        prominent: bool = False,
    ) -> None:
        x1, y1, x2, y2 = box
        fill = "#FFF7F6" if prominent else self.colors.card
        outline = accent if prominent else self.colors.line
        draw.rounded_rectangle(box, radius=16, fill=fill, outline=outline, width=3 if prominent else 1)
        draw.rounded_rectangle((x1, y1, x1 + 6, y2), radius=3, fill=accent)
        draw.text((x1 + 22, y1 + 13), title, fill=accent, font=self._font(19, True))
        body_y = y1 + 44
        size = 25 if prominent else 23
        for line in lines[:4]:
            if body_y + size + 3 > y2:
                break
            draw.text((x1 + 22, body_y), line, fill=self.colors.text, font=self._font(size, prominent))
            body_y += size + 8

    def _draw_target_box(
        self,
        draw: ImageDraw.ImageDraw,
        state: DemoState,
        source_size: tuple[int, int] | None,
        target_size: tuple[int, int],
    ) -> None:
        selected = next((item for item in state.objects if item.selected), None)
        if selected is None or source_size is None:
            return
        sw, sh = source_size
        tw, th = target_size
        scale = max(tw / sw, th / sh)
        rendered_w, rendered_h = sw * scale, sh * scale
        crop_x, crop_y = (rendered_w - tw) / 2.0, (rendered_h - th) / 2.0
        x1, y1, x2, y2 = selected.bbox_xyxy_norm
        box = (
            int(x1 * rendered_w - crop_x), int(y1 * rendered_h - crop_y),
            int(x2 * rendered_w - crop_x), int(y2 * rendered_h - crop_y),
        )
        box = tuple(max(6, min(value, (tw - 6) if index % 2 == 0 else (th - 6))) for index, value in enumerate(box))
        if box[2] <= box[0] or box[3] <= box[1]:
            return
        draw.rounded_rectangle(box, radius=8, outline="#55C4C9", width=5)
        label = f"目标{selected.class_name_cn}"
        if selected.distance_m is not None:
            label += f"  {selected.distance_m:.1f} m"
        label_box = draw.textbbox((0, 0), label, font=self._font(21, True))
        label_width = label_box[2] - label_box[0] + 24
        label_top = max(8, box[1] - 40)
        draw.rounded_rectangle(
            (box[0], label_top, min(tw - 8, box[0] + label_width), label_top + 34),
            radius=8, fill="#176C72",
        )
        draw.text((box[0] + 12, label_top + 4), label, fill="white", font=self._font(21, True))

    def render(self, rgb: object | None, state: DemoState) -> Image.Image:
        palette = self.colors
        canvas = Image.new("RGB", (self.WIDTH, self.HEIGHT), palette.canvas)
        source = self.camera_image(rgb)
        view_height = self.HEIGHT - self.TIMELINE_HEIGHT
        camera = self._fit_camera(source, (self.MAIN_WIDTH, view_height))
        canvas.paste(camera, (0, 0))
        camera_draw = ImageDraw.Draw(canvas)
        self._draw_target_box(
            camera_draw, state,
            None if source is None else source.size,
            (self.MAIN_WIDTH, view_height),
        )

        # A compact top strip keeps the view readable without obscuring the road.
        camera_draw.rounded_rectangle((28, 24, 282, 74), radius=14, fill="#17212BDD")
        camera_draw.text((48, 34), "CARLA 实时视野", fill="white", font=self._font(23, True))
        speed_text = f"{state.vehicle_speed_kmh:.1f} km/h"
        camera_draw.rounded_rectangle((1120, 24, 1348, 78), radius=16, fill="#17212BDD")
        camera_draw.text((1140, 34), speed_text, fill="white", font=self._font(25, True))

        panel = Image.new("RGB", (self.PANEL_WIDTH, view_height), palette.panel)
        draw = ImageDraw.Draw(panel)
        draw.text((30, 24), "当前任务", fill=palette.muted, font=self._font(18, True))
        draw.text((30, 49), state.scene_name_cn, fill=palette.text, font=self._font(31, True))
        if state.scene_id:
            draw.text((30, 88), f"场景 {state.scene_id}", fill=palette.muted, font=self._font(16))

        x1, x2 = 24, self.PANEL_WIDTH - 24
        voice_lines = []
        if state.voice_language:
            voice_lines.append(state.voice_language)
        voice_lines.extend(f"“{line}”" for line in self._wrap(state.voice_text, 35)[:2])
        if state.asr_text:
            voice_lines.append(f"识别：{state.asr_text}")
        self._card(draw, (x1, 116, x2, 240), "用户语音", voice_lines, accent=palette.cyan)
        self._card(
            draw, (x1, 252, x2, 344), "系统理解",
            self._wrap(state.intent_text, 36), accent=palette.blue,
        )
        self._card(
            draw, (x1, 356, x2, 494), "场景感知",
            state.perception_summary, accent=palette.green,
        )
        qwen_lines = [f"Qwen：{state.qwen_status}", f"动作：{state.qwen_action_cn}"]
        if state.qwen_target_cn:
            qwen_lines.append(f"目标：{state.qwen_target_cn}")
        if state.qwen_reason_cn:
            qwen_lines.extend(self._wrap(f"依据：{state.qwen_reason_cn}", 36)[:1])
        self._card(draw, (x1, 506, x2, 654), "AI 决策", qwen_lines, accent=palette.purple)

        safety_accent = (
            palette.red if state.risk_level == "danger"
            else palette.orange if state.risk_level == "warning"
            else palette.green
        )
        self._card(
            draw, (x1, 666, x2, 770), state.safety_status,
            self._wrap(state.safety_reason_cn, 36), accent=safety_accent,
            prominent=state.risk_level == "danger",
        )
        target = (
            "暂无" if state.vehicle_target_speed_kmh is None
            else f"{state.vehicle_target_speed_kmh:.1f}"
        )
        execution_lines = (
            f"速度：{state.vehicle_speed_kmh:.1f} → {target} km/h",
            f"动作：{state.vehicle_action_cn}",
            f"状态：{state.execution_status}",
        )
        self._card(draw, (x1, 782, x2, 956), "车辆执行", execution_lines, accent=palette.blue)
        canvas.paste(panel, (self.MAIN_WIDTH, 0))

        timeline = Image.new("RGB", (self.WIDTH, self.TIMELINE_HEIGHT), "#FFFFFF")
        td = ImageDraw.Draw(timeline)
        td.line((112, 41, self.WIDTH - 112, 41), fill=palette.line, width=4)
        positions = [160 + index * 400 for index in range(len(TIMELINE_LABELS))]
        for index, (label, x) in enumerate(zip(TIMELINE_LABELS, positions)):
            completed = index < state.timeline_index
            current = index == state.timeline_index
            color = palette.green if completed else palette.blue if current else palette.inactive
            if state.timeline_override and index == 3:
                color = palette.red
            td.ellipse((x - 13, 28, x + 13, 54), fill=color, outline="white", width=3)
            text_box = td.textbbox((0, 0), label, font=self._font(19, current or completed))
            td.text(
                (x - (text_box[2] - text_box[0]) / 2, 61), label,
                fill=color, font=self._font(19, current or completed),
            )
        canvas.paste(timeline, (0, view_height))

        if self.debug and state.debug_lines:
            debug_box = (24, view_height - 150, 560, view_height - 20)
            camera_draw = ImageDraw.Draw(canvas)
            camera_draw.rounded_rectangle(debug_box, radius=12, fill="#101820DD")
            y = debug_box[1] + 12
            for line in state.debug_lines:
                camera_draw.text((debug_box[0] + 16, y), line, fill="#D8E1E8", font=self._font(17))
                y += 22
        return canvas


@dataclass(frozen=True, slots=True)
class _RenderPacket:
    rgb: Image.Image | None
    state: DemoState


class AsyncDemoVisualizer:
    """Non-blocking, latest-frame-wins pygame display and optional frame dump."""

    def __init__(
        self,
        *,
        mode: str,
        fps: float = 10.0,
        record_dir: str | Path | None = None,
    ) -> None:
        if mode not in {"demo", "debug"}:
            raise ValueError("visualizer mode must be demo or debug")
        if fps <= 0.0:
            raise ValueError("visualizer fps must be positive")
        self.mode = mode
        self.fps = float(fps)
        self.record_dir = None if record_dir is None else Path(record_dir)
        self._queue: queue.Queue[_RenderPacket | None] = queue.Queue(maxsize=1)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.error: str | None = None
        self.dropped_frames = 0

    def start(self) -> None:
        if self._thread is not None:
            return
        if self.record_dir is not None:
            self.record_dir.mkdir(parents=True, exist_ok=True)
        self._thread = threading.Thread(
            target=self._run, name="carla-demo-ui", daemon=True,
        )
        self._thread.start()

    def submit(self, rgb: object | None, state: DemoState) -> None:
        if self._stop.is_set() or self.error is not None:
            return
        try:
            image = DemoFrameRenderer.camera_image(rgb)
        except (TypeError, ValueError) as error:
            self.error = f"RGB frame rejected: {error}"
            return
        packet = _RenderPacket(image.copy() if image is not None else None, state)
        try:
            self._queue.put_nowait(packet)
        except queue.Full:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            self.dropped_frames += 1
            try:
                self._queue.put_nowait(packet)
            except queue.Full:
                self.dropped_frames += 1

    def close(self) -> None:
        self._stop.set()
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        if self._thread is not None:
            self._thread.join(timeout=3.0)

    def _run(self) -> None:
        try:
            import pygame

            pygame.init()
            pygame.display.set_caption("CARLA 语音控制演示")
            screen = pygame.display.set_mode(
                (DemoFrameRenderer.WIDTH, DemoFrameRenderer.HEIGHT)
            )
            renderer = DemoFrameRenderer(debug=self.mode == "debug")
            interval = 1.0 / self.fps
            next_render = 0.0
            frame_index = 0
            while not self._stop.is_set():
                try:
                    packet = self._queue.get(timeout=0.1)
                except queue.Empty:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            self._stop.set()
                    continue
                if packet is None:
                    break
                now = time.monotonic()
                if now < next_render:
                    continue
                composed = renderer.render(packet.rgb, packet.state)
                surface = pygame.image.fromstring(
                    composed.tobytes(), composed.size, composed.mode,
                )
                screen.blit(surface, (0, 0))
                pygame.display.flip()
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self._stop.set()
                if self.record_dir is not None:
                    composed.save(self.record_dir / f"frame_{frame_index:06d}.png")
                frame_index += 1
                next_render = now + interval
            pygame.quit()
        except BaseException as error:  # UI failures must never escape to control.
            self.error = f"{type(error).__name__}: {error}"
            self._stop.set()
