from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class Day22Context:
    """
    Day22统一输入。

    voice_command:
        驾驶员语音文本。

    safety_state:
        第二组C的SafetyStateSummary.to_dict()，以及A/D补充的交通灯、
        停止线、天气等状态。

    perception:
        第一组RGB结构化结果。没有结果时必须为空字典，不能伪造目标。

    scene_state:
        可选车辆/场景状态。
    """

    voice_command: str
    safety_state: Mapping[str, Any]
    perception: Mapping[str, Any] = field(default_factory=dict)
    scene_state: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "voice_command": str(self.voice_command),
            "safety_state": dict(self.safety_state),
            "perception": dict(self.perception),
            "scene_state": dict(self.scene_state),
        }
