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
    """
    构造Day22稳定提示词。

    核心约束：
    1. 不编造视觉目标；
    2. 安全状态优先于用户命令；
    3. 不输出底层控制量；
    4. 中文原因不超过20个汉字。
    """

    payload = {
        "voice_command": voice_command,
        "perception": dict(perception),
        "safety_state": dict(safety_state),
        "scene_state": dict(scene_state),
    }

    return f"""
你是自动驾驶系统的高层行为决策模块，不是车辆底层控制器。

【允许动作】
START
STOP
SLOW_DOWN
SET_SPEED
EMERGENCY_STOP

【绝对禁止】
1. 禁止输出 throttle、brake、steer、方向盘角度、油门值或刹车值。
2. 禁止编造输入中不存在的车辆、行人、障碍物或交通灯。
3. object_class为空、visual_valid为false或目标置信度不足时，
   不得声称“检测到行人”或“检测到车辆”。
4. 只有LiDAR距离而没有视觉类别时，只能解释为“前方距离不足”或“TTC风险”。
5. 用户命令与安全状态冲突时，安全状态优先。
6. reason_zh必须简洁，只写一句话，不超过20个汉字。

【安全规则】
- recommended_action为FULL_BRAKE或EMERGENCY_BRAKE：停车或紧急停车。
- TTC不大于1.5秒：EMERGENCY_STOP。
- 红灯且已接近停止线：STOP。
- 可靠行人目标：STOP。
- 前方距离或TTC进入警戒范围：SLOW_DOWN。
- 视觉/LiDAR融合无效或输入置信度不足：STOP并请求确认。
- 无危险且用户要求继续：START。

【输出JSON】
{{
  "action": "",
  "target_speed_mps": null,
  "confidence": 0.0,
  "requires_confirmation": false,
  "reason_zh": ""
}}

只输出JSON，不输出Markdown或额外解释。

【输入】
{json.dumps(payload, ensure_ascii=False)}
""".strip()
