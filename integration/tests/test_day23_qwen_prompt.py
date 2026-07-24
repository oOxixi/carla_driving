from pathlib import Path

from integration.day20.qwen_prompt import (
    LOW_LEVEL_CONTROL_FIELDS,
    PROMPT_VERSION,
    build_decision_prompt,
)
from integration.day20.schemas import ALLOWED_ACTIONS


def make_prompt() -> str:
    return build_decision_prompt(
        command_text="前方车辆减速，请降低速度",
        scene_state={
            "ego": {
                "speed_kmh": 18.5,
                "lane_id": 1,
            },
            "objects": [
                {
                    "object_id": "vehicle_12",
                    "category": "vehicle",
                    "distance_m": 12.0,
                    "direction": "front",
                }
            ],
        },
    )


def test_prompt_version_is_frozen():
    assert PROMPT_VERSION == "day23-final-v1"


def test_prompt_contains_all_allowed_actions():
    prompt = make_prompt()

    for action in ALLOWED_ACTIONS:
        assert action in prompt


def test_prompt_enforces_json_contract():
    prompt = make_prompt()

    assert "只输出一个 JSON 对象" in prompt
    assert "actions 必须至少包含一个有效动作" in prompt
    assert '"actions"' in prompt
    assert '"action"' in prompt
    assert '"target_id"' in prompt
    assert '"target_speed_kmh"' in prompt
    assert '"confidence"' in prompt
    assert '"reason"' in prompt


def test_prompt_enforces_control_boundary():
    prompt = make_prompt()

    assert "你不是车辆控制器" in prompt
    assert "下游执行器和安全仲裁模块" in prompt
    assert "禁止输出底层控制字段" in prompt

    for field in LOW_LEVEL_CONTROL_FIELDS:
        assert field in prompt


def test_prompt_contains_runtime_inputs():
    prompt = make_prompt()

    assert "前方车辆减速，请降低速度" in prompt
    assert '"speed_kmh": 18.5' in prompt
    assert '"object_id": "vehicle_12"' in prompt


def test_prompt_requires_grounded_visual_reasoning():
    prompt = make_prompt()

    assert "不得编造视觉依据" in prompt
    assert "图像和 SceneState 均支持" in prompt
    assert "应降低 confidence" in prompt

def test_qwen_adapter_uses_fixed_prompt_builder():
    adapter_source = Path(
        "integration/day20/qwen_vl_adapter.py"
    ).read_text(encoding="utf-8")

    assert (
        "from .qwen_prompt import build_decision_prompt"
        in adapter_source
    )
    assert "return build_decision_prompt(" in adapter_source
    assert "你是自动驾驶行为决策模块" not in adapter_source

