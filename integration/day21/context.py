from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class Day21Context:

    """
    Unified multimodal input for Qwen.

    Input:
        voice
        RGB perception
        SceneState
        SafetyStateSummary

    Output:
        Qwen high level decision
    """

    voice_command: str

    scene_state: dict[str, Any]

    perception: dict[str, Any]

    safety_state: dict[str, Any]


    def to_dict(self):

        return asdict(self)
