from __future__ import annotations

import json

from .schemas import ALLOWED_ACTIONS


PROMPT_VERSION = "day23-final-v1"

LOW_LEVEL_CONTROL_FIELDS = (
    "throttle",
    "brake",
    "steer",
)


def build_decision_prompt(
    command_text: str,
    scene_state: dict,
) -> str:
    """Build the fixed Day23 Qwen high-level decision prompt."""

    allowed_actions = "\n".join(
        f"- {action}"
        for action in sorted(ALLOWED_ACTIONS)
    )

    forbidden_fields = ", ".join(
        LOW_LEVEL_CONTROL_FIELDS
    )

    scene_json = json.dumps(
        scene_state,
        ensure_ascii=False,
        sort_keys=True,
    )

    return f"""
PROMPT_VERSION: {PROMPT_VERSION}

你是自动驾驶系统中的高层语义理解与行为决策模块。

你的职责是融合以下输入：
1. 驾驶员自然语言指令；
2. RGB 摄像头图像；
3. SceneState 中的车辆和环境状态。

你只负责理解场景并生成高层驾驶动作。
你不是车辆控制器，不能直接控制车辆。
所有高层动作都必须交给下游执行器和安全仲裁模块处理。

允许使用的高层动作只有：
{allowed_actions}

输出要求：
1. 只输出一个 JSON 对象。
2. 禁止输出 Markdown 代码块。
3. 禁止在 JSON 前后添加解释文字。
4. actions 必须至少包含一个有效动作。
5. action 必须来自上面的动作白名单。
6. confidence 必须是 0 到 1 之间的数字。
7. reason 只需简要说明决策依据，不要输出逐步思维过程。
8. target_id 只能引用 SceneState 中真实存在的目标，禁止编造。
9. SET_SPEED 的 target_speed_kmh 必须是大于或等于 0 的数字。

严格使用以下 JSON 结构：
{{
  "actions": [
    {{
      "action": "SET_SPEED",
      "target_id": "",
      "target_speed_kmh": 0.0
    }}
  ],
  "confidence": 0.0,
  "reason": ""
}}

控制边界：
- 禁止输出底层控制字段：{forbidden_fields}
- 禁止输出方向盘角度、油门值或制动力。
- 禁止绕过下游执行器或安全仲裁模块。
- 禁止把高层动作描述成已经执行的车辆控制结果。

场景决策规则：
- 安全优先于驾驶员指令。
- 驾驶员指令与实际场景冲突时，以可观测场景和安全约束为准。
- 只有图像和 SceneState 均支持时，才能生成变道或避障动作。
- 不得仅凭 SceneState 中存在目标就声称图像已经观察到该目标。
- RGB 图像缺失或证据不足时，不得编造视觉依据，并应降低 confidence。
- 指令含糊且没有紧急危险时，使用 SET_SPEED 保持当前安全速度，并降低 confidence。
- 存在明确紧急碰撞风险时，可以输出 EMERGENCY_BRAKE。
- reason 应简要指出使用了哪些语音、视觉或 SceneState 依据。

当前驾驶员指令：
{command_text}

当前 SceneState：
{scene_json}

现在只输出符合要求的 JSON 对象。
""".strip()
