"""Run the Day22 cases through the real local Qwen2.5-VL model."""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

from .command_adapter import build_command
from .day22_cases import CASES
from .day22_context import Day22Context
from .qwen_day22_adapter import Day22QwenAdapter
from .qwen_runtime import Qwen25VLRuntime


DEFAULT_OUTPUT = Path(
    "integration/day22/day22_qwen_runtime_results.json"
)

VISUAL_CASES = frozenset({
    "red_light_near_stop_line",
    "pedestrian",
    "front_vehicle",
    "no_false_pedestrian",
})

ALLOWED_ACTIONS = frozenset({
    "START",
    "STOP",
    "SLOW_DOWN",
    "SET_SPEED",
    "EMERGENCY_STOP",
})

FORBIDDEN_CONTROL_FIELDS = frozenset({
    "throttle",
    "brake",
    "steer",
    "steering_angle",
    "wheel_angle",
})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run all Day22 cases with the real local "
            "Qwen2.5-VL model."
        )
    )

    parser.add_argument(
        "--model-path",
        default="models/Qwen2.5-VL-7B",
    )

    parser.add_argument(
        "--image-map",
        default=None,
        help=(
            "JSON mapping from case name to CARLA RGB image path."
        ),
    )

    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
    )

    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=192,
    )

    parser.add_argument(
        "--allow-text-only",
        action="store_true",
        help=(
            "Allow visual cases without images. This still performs "
            "real Qwen inference, but is not full RGB multimodal evidence."
        ),
    )

    return parser.parse_args()


def load_image_map(path: str | None) -> dict[str, str]:
    if path is None:
        return {}

    image_map_path = Path(path)

    if not image_map_path.is_file():
        raise FileNotFoundError(
            f"image map not found: {image_map_path}"
        )

    data = json.loads(
        image_map_path.read_text(encoding="utf-8")
    )

    if not isinstance(data, dict):
        raise TypeError("image map must be a JSON object")

    result: dict[str, str] = {}

    for case_name, image_path in data.items():
        if not isinstance(case_name, str):
            raise TypeError("image map case names must be strings")

        if not isinstance(image_path, str) or not image_path.strip():
            raise TypeError(
                f"invalid image path for case: {case_name}"
            )

        result[case_name] = image_path

    return result


def extract_json_object(raw: str) -> dict[str, Any]:
    if not isinstance(raw, str):
        raise TypeError("Qwen output must be text")

    fenced = re.findall(
        r"```(?:json)?\s*(\{.*?\})\s*```",
        raw,
        flags=re.IGNORECASE | re.DOTALL,
    )

    candidates = fenced + [raw]
    decoder = json.JSONDecoder()

    for candidate in candidates:
        start = candidate.find("{")

        if start < 0:
            continue

        try:
            value, _ = decoder.raw_decode(candidate[start:])
        except json.JSONDecodeError:
            continue

        if isinstance(value, dict):
            return value

    raise ValueError("Qwen output contains no valid JSON object")


def collect_keys(value: Any) -> set[str]:
    keys: set[str] = set()

    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(str(key))
            keys.update(collect_keys(child))

    elif isinstance(value, list):
        for child in value:
            keys.update(collect_keys(child))

    return keys


def hallucination_flags(
    parsed: dict[str, Any] | None,
    context: Day22Context,
) -> list[str]:
    """
    检查Qwen解释和动作是否与结构化输入矛盾。

    这里的“幻觉”不仅包括编造行人，也包括：
    - 距离充足却声称距离不足；
    - 无红灯输入却声称红灯；
    - 传感器有效却声称失效；
    - 明确安全状态下无依据停车。
    """

    if parsed is None:
        return []

    flags: list[str] = []

    safety = dict(context.safety_state)
    perception = dict(context.perception)

    object_class = (
        safety.get("object_class")
        or perception.get("object_class")
    )

    visual_valid = safety.get("visual_valid")
    lidar_valid = safety.get("lidar_valid")
    traffic_light = str(
        safety.get("traffic_light", "UNKNOWN")
    ).upper()

    front_distance = safety.get("front_distance_m")
    ttc = safety.get("ttc_s")

    try:
        front_distance = (
            float(front_distance)
            if front_distance is not None
            else None
        )
    except (TypeError, ValueError):
        front_distance = None

    try:
        ttc = float(ttc) if ttc is not None else None
    except (TypeError, ValueError):
        ttc = None

    reason = str(
        parsed.get(
            "reason_zh",
            parsed.get("reason", ""),
        )
    ).strip()

    action = str(
        parsed.get("action", "")
    ).strip().upper()

    pedestrian_claims = (
        "检测到行人",
        "发现行人",
        "前方有行人",
        "存在行人",
        "前方行人",
    )

    if object_class in {None, "", "NONE", "UNKNOWN"}:
        if any(text in reason for text in pedestrian_claims):
            flags.append("FALSE_PEDESTRIAN_CLAIM")

    if visual_valid is False:
        if any(text in reason for text in pedestrian_claims):
            flags.append("VISUAL_INVALID_PEDESTRIAN_CLAIM")

    distance_claims = (
        "距离不足",
        "距离过近",
        "前方过近",
        "前方距离近",
    )

    if any(text in reason for text in distance_claims):
        if (
            front_distance is None
            or front_distance > 10.0
        ):
            flags.append("UNSUPPORTED_DISTANCE_RISK_CLAIM")

    if "红灯" in reason and traffic_light != "RED":
        flags.append("UNSUPPORTED_RED_LIGHT_CLAIM")

    sensor_failure_claims = (
        "传感器失效",
        "传感器无效",
        "LiDAR无效",
        "感知不可用",
    )

    if any(text in reason for text in sensor_failure_claims):
        if lidar_valid is not False:
            flags.append("UNSUPPORTED_SENSOR_FAILURE_CLAIM")

    explicit_hazard = (
        traffic_light == "RED"
        or (
            object_class in {"PEDESTRIAN", "PERSON"}
            and visual_valid is not False
        )
        or (
            front_distance is not None
            and front_distance <= 10.0
        )
        or (
            ttc is not None
            and ttc <= 2.5
        )
        or str(
            safety.get("recommended_action", "")
        ).upper() in {
            "FULL_BRAKE",
            "EMERGENCY_BRAKE",
            "SLOW_DOWN",
        }
        or lidar_valid is False
        or float(
            safety.get("input_confidence", 1.0)
        ) < 0.6
    )

    if (
        action in {
            "STOP",
            "SLOW_DOWN",
            "EMERGENCY_STOP",
        }
        and not explicit_hazard
        and not any(
            word in str(context.voice_command)
            for word in (
                "停车",
                "停下",
                "停止",
                "减速",
                "慢一点",
                "降低速度",
            )
        )
    ):
        flags.append("UNGROUNDED_CONSERVATIVE_ACTION")

    return sorted(set(flags))


def validate_raw_output(
    raw: str,
    context: Day22Context,
) -> dict[str, Any]:
    try:
        parsed = extract_json_object(raw)
        format_valid = True
        parse_error = None
    except Exception as exc:
        parsed = None
        format_valid = False
        parse_error = f"{type(exc).__name__}: {exc}"

    forbidden_fields: list[str] = []
    action_valid = False
    explanation_short = False

    if parsed is not None:
        keys = collect_keys(parsed)

        forbidden_fields = sorted(
            keys.intersection(FORBIDDEN_CONTROL_FIELDS)
        )

        action = str(
            parsed.get("action", "")
        ).strip().upper()

        action_valid = action in ALLOWED_ACTIONS

        reason = str(
            parsed.get(
                "reason_zh",
                parsed.get("reason", ""),
            )
        ).strip()

        explanation_short = bool(reason) and len(reason) <= 20

    return {
        "format_valid": format_valid,
        "parse_error": parse_error,
        "parsed": parsed,
        "action_valid": action_valid,
        "forbidden_control_fields": forbidden_fields,
        "explanation_short": explanation_short,
        "hallucination_flags": hallucination_flags(
            parsed,
            context,
        ),
    }


def main() -> None:
    args = parse_args()
    image_map = load_image_map(args.image_map)

    missing_visual_images = sorted(
        case_name
        for case_name in VISUAL_CASES
        if case_name not in image_map
    )

    if missing_visual_images and not args.allow_text_only:
        raise RuntimeError(
            "Missing RGB images for visual cases: "
            + ", ".join(missing_visual_images)
            + ". Provide --image-map or use --allow-text-only "
              "only for text+state debugging."
        )

    runtime = Qwen25VLRuntime(
        args.model_path,
        max_new_tokens=args.max_new_tokens,
    )

    prompt_adapter = Day22QwenAdapter()
    outputs: list[dict[str, Any]] = []

    for index, case in enumerate(CASES, start=1):
        context = Day22Context(
            voice_command=case["voice"],
            safety_state=case["safety_state"],
            perception={},
            scene_state={},
        )

        image_path = image_map.get(case["case"])
        prompt = prompt_adapter.build_prompt(context)

        started = time.perf_counter()

        try:
            raw_output = runtime.generate(
                prompt,
                image_path=image_path,
            )
            runtime_error = None
        except Exception as exc:
            raw_output = ""
            runtime_error = f"{type(exc).__name__}: {exc}"

        latency_s = time.perf_counter() - started

        raw_validation = validate_raw_output(
            raw_output,
            context,
        )

        cached_output = raw_output

        final_adapter = Day22QwenAdapter(
            model_infer=lambda _prompt, output=cached_output: output
        )

        final_decision = final_adapter.infer(context)
        command = build_command(
            final_decision,
            context.voice_command,
        )

        record = {
            "case_index": index,
            "case": case["case"],
            "expected_final_action": case["expected"],
            "expected_confirmation": case[
                "expected_confirmation"
            ],
            "input": context.to_dict(),
            "image_path": image_path,
            "multimodal_image_used": image_path is not None,
            "prompt_version": "day22_v2",
            "runtime_error": runtime_error,
            "latency_s": round(latency_s, 4),
            "qwen_raw_output": raw_output,
            "qwen_validation": raw_validation,
            "final_decision": final_decision,
            "command": command,
            "final_action_correct": (
                final_decision["action"]
                == case["expected"]
            ),
            "final_confirmation_correct": (
                final_decision["requires_confirmation"]
                == case["expected_confirmation"]
            ),
        }

        outputs.append(record)

        print(
            f"[{index:02d}/{len(CASES):02d}] "
            f"{case['case']}: "
            f"final={final_decision['action']} "
            f"source={final_decision['decision_source']} "
            f"latency={latency_s:.2f}s"
        )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(
            outputs,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"saved: {output_path}")


if __name__ == "__main__":
    main()
