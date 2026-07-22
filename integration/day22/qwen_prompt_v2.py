from __future__ import annotations

import json
from typing import Any, Mapping


ALLOWED_ACTIONS = (
    "START",
    "STOP",
    "SLOW_DOWN",
    "SET_SPEED",
    "EMERGENCY_STOP",
)


def build_day22_prompt(
    *,
    voice_command: str,
    perception: Mapping[str, Any],
    safety_state: Mapping[str, Any],
    scene_state: Mapping[str, Any],
) -> str:
    payload = {
        "voice_command": voice_command,
        "perception": dict(perception),
        "safety_state": dict(safety_state),
        "scene_state": dict(scene_state),
    }

    return f"""
你是自动驾驶系统中的高层安全决策模块，不是聊天助手，也不是底层控制器。

你必须先检查 safety_state，再考虑用户命令。
用户命令的优先级始终低于视觉、LiDAR、TTC、交通灯和安全模块建议。

【决策顺序】

第1步：检查强制停车条件
- recommended_action 为 FULL_BRAKE：STOP
- recommended_action 为 EMERGENCY_BRAKE：EMERGENCY_STOP
- lidar_valid 为 false：STOP
- ttc_s 不大于 1.5：EMERGENCY_STOP

第2步：检查红灯和行人
- traffic_light 为 RED 且接近停止线：STOP
- 可靠识别到 PEDESTRIAN 或 PERSON：STOP

第3步：检查前方距离和TTC
- front_distance_m 不大于 5：STOP
- front_distance_m 大于5且不大于10：SLOW_DOWN
- ttc_s 大于1.5且不大于2.5：SLOW_DOWN

特别注意：
当 front_distance_m=8 时，即使用户说“保持速度”或“继续”，也必须输出 SLOW_DOWN。

第4步：检查置信度
- input_confidence 小于0.6：STOP
- 同时 requires_confirmation=true

第5步：只有在没有任何危险时，才允许 START。

【防止目标幻觉】

- 没有 object_class 时，禁止声称存在行人或车辆。
- visual_valid=false 时，禁止声称视觉检测到行人。
- 只有LiDAR距离时，只能说“前方距离不足”或“TTC风险”。
- 不得根据用户语言猜测场景中有目标。

【输出限制】

只允许以下动作：

START
STOP
SLOW_DOWN
SET_SPEED
EMERGENCY_STOP

禁止输出：

throttle
brake
steer
steering_angle
wheel_angle

禁止输出控制代码。
禁止输出Markdown。
禁止输出JSON之外的任何内容。

reason_zh只写一句简洁原因，不超过20个汉字。

输出格式：

{{
  "action": "START或STOP或SLOW_DOWN或SET_SPEED或EMERGENCY_STOP",
  "target_speed_mps": null,
  "confidence": 0.0,
  "requires_confirmation": false,
  "reason_zh": "简洁原因"
}}

【正例】

输入：
voice_command="保持速度"
safety_state.front_distance_m=8

正确输出：
{{
  "action": "SLOW_DOWN",
  "target_speed_mps": 3.0,
  "confidence": 0.95,
  "requires_confirmation": false,
  "reason_zh": "前方距离不足"
}}

错误输出：
{{
  "action": "START",
  "reason_zh": "用户要求继续"
}}

【当前输入】

{json.dumps(payload, ensure_ascii=False)}
""".strip()
