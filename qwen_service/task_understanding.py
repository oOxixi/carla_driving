"""Text-only intent decomposition, never an executable ManeuverPlan.

Separate requested tasks from physical grounding/safety. The model chooses every
action and its order; literal quotes make unsupported extraction observable.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any, Mapping

from .shadow_planner import ACTION_COMPLETIONS, _unique_object


ACTION_ZH = {
    "KEEP_LANE": "保持车道", "SET_SPEED": "设置或恢复车速", "SLOW_DOWN": "减速",
    "STOP": "停车", "YIELD": "让行", "FOLLOW": "跟车",
    "TURN_LEFT": "左转", "TURN_RIGHT": "右转",
    "CHANGE_LANE_LEFT": "向左变道", "CHANGE_LANE_RIGHT": "向右变道",
    "AVOID_OBSTACLE": "避障超车", "RETURN_TO_LANE": "回原车道",
    "PULL_OVER": "靠边停车", "HOLD": "等待确认",
}


def task_action_language(task: Mapping[str, Any], *, encode: bool) -> dict[str, Any]:
    """Bijective protocol translation only; never infer actions from source text."""
    mapping = ACTION_ZH if encode else {value: key for key, value in ACTION_ZH.items()}
    result = copy.deepcopy(dict(task))
    for step in result["steps"]:
        step["action"] = mapping[step["action"]]
    result["prohibited_actions"] = {mapping[key]: value for key, value in result["prohibited_actions"].items()}
    return result


TASK_SCHEMA: dict[str, Any] = {
    "type": "object", "additionalProperties": False,
    "required": ["steps", "prohibited_actions", "requires_confirmation"],
    "properties": {
        "steps": {
            "type": "array", "minItems": 1, "maxItems": 8,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["evidence", "action", "target_text", "direction", "speed_kph", "gap_m", "condition"],
                "properties": {
                    "action": {"enum": list(ACTION_COMPLETIONS)},
                    "target_text": {"type": ["string", "null"], "minLength": 1, "maxLength": 128},
                    "direction": {"enum": [None, "LEFT", "RIGHT", "STRAIGHT"]},
                    "speed_kph": {"type": ["number", "null"], "minimum": 0, "maximum": 300},
                    "gap_m": {"type": ["number", "null"], "minimum": 0, "maximum": 100},
                    "condition": {"type": ["string", "null"], "minLength": 1, "maxLength": 256},
                    "evidence": {"type": "string", "minLength": 1, "maxLength": 1000},
                },
            },
        },
        "prohibited_actions": {
            "type": "object", "additionalProperties": False,
            "properties": {name: {"const": True} for name in ACTION_COMPLETIONS},
        },
        "requires_confirmation": {"type": "boolean"},
    },
}

SYSTEM_PROMPT = """你是驾驶指令的语义分解器，不是车辆控制器。只输出符合schema的JSON。
识别完整原句的全部肯定任务并按用户要求的执行顺序列出，不能只输出第一项或最后一项。
不使用前置NLU分类，不依据一份旧动作白名单删去用户明确要求的后续任务。
动作含义：KEEP_LANE沿原车道继续；SET_SPEED设定/恢复明确车速；SLOW_DOWN减速；
STOP停车；YIELD让其他交通参与者先通过；FOLLOW跟随；TURN_LEFT/RIGHT转弯；
CHANGE_LANE_LEFT/RIGHT单纯变道；AVOID_OBSTACLE绕障或超车（含所需变道与通过目标）；
RETURN_TO_LANE回原车道；PULL_OVER靠边停车；HOLD不确定时等待确认。
同一句的“变道超越”作为AVOID_OBSTACLE，不重复生成一次变道；但“返回”和“恢复速度”是独立后续任务。
单纯“向左/右变道”是CHANGE_LANE_LEFT/RIGHT，不是AVOID_OBSTACLE；只有绕障/超越才用AVOID_OBSTACLE。
背景描述不是动作：“前方有某物/看到某人”不独立生成步骤。一个“减速至某速度”只列一个SLOW_DOWN，
不能拆成SLOW_DOWN加SET_SPEED。条件语句不独立生成HOLD。明确等待他人通过是YIELD而非HOLD。
每步evidence必须逐字摘录原句中支持该步的非空连续片段。
target_text是逐字摘录的目标名词短语，不是actor ID；不需要目标时null。
FOLLOW/YIELD/AVOID_OBSTACLE明确提到被跟随/让行/超越对象时必须摘录该对象；不要遗漏目标。
condition是原句逐字摘录的前提或完成后条件；条件应绑定到受它限制的动作，不独立生成一项动作。
顺序已经由steps数组表达，不要自行编造“恢复完成后”“停车后”等原文没有的条件。
只有“然后/再/最后”连接而没有明确条件时，condition=null；不要把动作本身填作它自己的条件。
方向LEFT/RIGHT/STRAIGHT，只在原句明确表达该步方向时填写；speed_kph用公里每小时，gap_m用米。
原句未明确给出的目标、数值、方向、条件用null，不推测、不补默认巡航速度。
“不要/禁止”的动作放入prohibited_actions，不要当作肯定任务。无法消歧则requires_confirmation=true。
输出只表达用户希望做什么，不代表现在安全、可执行或已经完成。不要生成轨迹、油门、刹车或方向盘值。
"""


def _example_step(evidence: str, action: str, **slots: Any) -> dict[str, Any]:
    return {"action": action, "target_text": None, "direction": None,
            "speed_kph": None, "gap_m": None, "condition": None, "evidence": evidence, **slots}


EXAMPLES = (
    ("先右转，再把车速设为25公里每小时", [
        _example_step("先右转", "TURN_RIGHT", direction="RIGHT"),
        _example_step("再把车速设为25公里每小时", "SET_SPEED", speed_kph=25),
    ], {}),
    ("停车", [_example_step("停车", "STOP")], {}),
    ("在安全时从右侧绕过路障，完成后返回原车道", [
        _example_step("在安全时从右侧绕过路障", "AVOID_OBSTACLE", target_text="路障", direction="RIGHT", condition="在安全时"),
        _example_step("完成后返回原车道", "RETURN_TO_LANE", condition="完成后"),
    ], {}),
    ("不要向左变道，保持当前车道", [_example_step("保持当前车道", "KEEP_LANE")], {"CHANGE_LANE_LEFT": True}),
    ("跟随前面那辆货车，等它驶离后恢复到50公里每小时", [
        _example_step("跟随前面那辆货车", "FOLLOW", target_text="前面那辆货车"),
        _example_step("等它驶离后恢复到50公里每小时", "SET_SPEED", speed_kph=50, condition="等它驶离后"),
    ], {}),
    ("前方路边有施工人员，减速到18公里每小时，待人员走开后恢复到28公里每小时", [
        _example_step("减速到18公里每小时", "SLOW_DOWN", target_text="施工人员", speed_kph=18),
        _example_step("待人员走开后恢复到28公里每小时", "SET_SPEED", speed_kph=28, condition="待人员走开后"),
    ], {}),
    ("看到路边的广告牌，保持车道，随后将车速设为22公里每小时", [
        _example_step("保持车道", "KEEP_LANE"),
        _example_step("随后将车速设为22公里每小时", "SET_SPEED", speed_kph=22),
    ], {}),
    ("注意路边树木，请向右变道，之后保持车道", [
        _example_step("请向右变道", "CHANGE_LANE_RIGHT", direction="RIGHT"),
        _example_step("之后保持车道", "KEEP_LANE"),
    ], {}),
    ("把车换到左边车道，然后以原速度继续行驶", [
        _example_step("把车换到左边车道", "CHANGE_LANE_LEFT", direction="LEFT"),
        _example_step("然后以原速度继续行驶", "KEEP_LANE"),
    ], {}),
    ("前面有一辆洒水车，先减速到12公里每小时，从左侧绕过它，通过后返回原车道，最后恢复到32公里每小时", [
        _example_step("先减速到12公里每小时", "SLOW_DOWN", target_text="洒水车", speed_kph=12),
        _example_step("从左侧绕过它", "AVOID_OBSTACLE", target_text="洒水车", direction="LEFT"),
        _example_step("通过后返回原车道", "RETURN_TO_LANE", condition="通过后"),
        _example_step("最后恢复到32公里每小时", "SET_SPEED", speed_kph=32),
    ], {}),
)


def validate_extraction(source: str, payload: Mapping[str, Any]) -> None:
    import jsonschema
    jsonschema.Draft202012Validator(TASK_SCHEMA).validate(payload)
    for index, step in enumerate(payload["steps"]):
        for field in ("evidence", "target_text", "condition"):
            value = step[field]
            if value is not None and value not in source:
                raise ValueError(f"steps[{index}].{field} has no literal support in source")
        if step["action"] in payload["prohibited_actions"]:
            raise ValueError(f"steps[{index}] executes a model-extracted prohibited action")
        if step["condition"] is not None and step["condition"] == step["evidence"]:
            raise ValueError(f"steps[{index}] condition repeats its own action evidence")
        # Validate explicit Arabic-number units in the model-selected evidence.
        # Never infer missing slots, choose an action or rewrite a number.
        for field, pattern in (
            ("speed_kph", r"(?P<value>\d+(?:\.\d+)?)\s*(?:公里每小时|公里/小时|千米每小时|km/h|kph)"),
            ("gap_m", r"(?P<value>\d+(?:\.\d+)?)\s*(?:米(?!每秒|/秒|/s)|metres?\b(?!\s*/\s*s)|meters?\b(?!\s*/\s*s)|m\b(?!\s*/\s*s))"),
        ):
            numbers = [float(m.group("value")) for m in re.finditer(pattern, step["evidence"], re.IGNORECASE)]
            if step[field] is not None and numbers and not any(abs(float(step[field]) - n) <= 1e-6 for n in numbers):
                raise ValueError(f"steps[{index}].{field} contradicts an explicit value in its quoted evidence")
        required_direction = {"TURN_LEFT": "LEFT", "TURN_RIGHT": "RIGHT",
                              "CHANGE_LANE_LEFT": "LEFT", "CHANGE_LANE_RIGHT": "RIGHT"}.get(step["action"])
        if required_direction is not None and step["direction"] not in (None, required_direction):
            raise ValueError(f"steps[{index}] action contradicts its direction slot")


def source_copy_schema(source: str) -> dict[str, Any]:
    """Offer all short source substrings, not a rule-selected target/condition.

    This is lexical copying only. It cannot tell which span is the right object.
    Bound grammar size; longer inputs still receive strict post-validation.
    """
    schema = copy.deepcopy(TASK_SCHEMA)
    if len(source) <= 256:
        for field, maximum in (("target_text", 24), ("condition", 48)):
            spans = dict.fromkeys(source[start:end]
                                  for start in range(len(source))
                                  for end in range(start + 1, min(len(source), start + maximum) + 1))
            schema["properties"]["steps"]["items"]["properties"][field]["enum"] = [None, *spans]
    return schema


class TaskUnderstandingPlanner:
    """No infer()/health(), no vehicle dispatch, no implicit ID grounding."""

    def __init__(self, transport: Any, *, max_tokens: int = 1536, review_rounds: int = 0,
                 action_language: str = "en") -> None:
        if type(max_tokens) is not int or not 256 <= max_tokens <= 8192:
            raise ValueError("max_tokens must be an integer in [256, 8192]")
        self.transport = transport
        self.max_tokens = max_tokens
        if type(review_rounds) is not int or review_rounds not in (0, 1):
            raise ValueError("review_rounds must be 0 or 1")
        self.review_rounds = review_rounds
        if action_language not in {"en", "zh"}:
            raise ValueError("action_language must be en or zh")
        self.action_language = action_language

    def generate(self, source_text: str) -> dict[str, Any]:
        if not isinstance(source_text, str) or not source_text.strip() or len(source_text) > 1000:
            raise ValueError("source_text must contain 1 to 1000 characters")
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for text, steps, prohibited in EXAMPLES:
            messages.append({"role": "user", "content": text})
            messages.append({"role": "assistant", "content": json.dumps({
                "steps": steps, "prohibited_actions": prohibited, "requires_confirmation": False,
            }, ensure_ascii=False)})
        messages.append({"role": "user", "content": source_text})
        schema = source_copy_schema(source_text)
        system_prompt = SYSTEM_PROMPT
        if self.action_language == "zh":
            system_prompt = system_prompt.replace("TURN_LEFT/RIGHT", "左转/右转")
            for action in sorted(ACTION_ZH, key=len, reverse=True):
                system_prompt = system_prompt.replace(action, ACTION_ZH[action])
            messages[0]["content"] = system_prompt
            for message in messages:
                if message["role"] == "assistant":
                    message["content"] = json.dumps(task_action_language(json.loads(message["content"]), encode=True), ensure_ascii=False)
            schema["properties"]["steps"]["items"]["properties"]["action"]["enum"] = list(ACTION_ZH.values())
            schema["properties"]["prohibited_actions"]["properties"] = {value: {"const": True} for value in ACTION_ZH.values()}
        report: dict[str, Any] = {
            "scope": "TEXT_INTENT_ONLY_NOT_GROUNDED_NOT_EXECUTABLE_NOT_GATE",
            "model_id": self.transport.model_id, "image_sent": False,
            "validation": "REJECTED", "task_accuracy": "NOT_MEASURED",
            "semantic_step_source": "MODEL_NOT_KEYWORD_EXPANSION",
            "source_sha256": hashlib.sha256(source_text.encode()).hexdigest(),
            "prompt_sha256": hashlib.sha256(json.dumps(messages, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
            "execution_constraints_applied": False, "ready_for_vehicle_execution": False,
            "review_rounds": self.review_rounds, "attempts": [],
            "action_language": self.action_language,
            "max_output_tokens": self.max_tokens,
            "copy_grammar_applied": len(source_text) <= 256,
            "wire_schema_sha256": hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest(),
        }
        import jsonschema
        for attempt in range(self.review_rounds + 1):
            prompt_hash = hashlib.sha256(json.dumps(messages, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            try:
                response = self.transport._client.chat.completions.create(
                    model=self.transport.model_id, messages=messages, temperature=0.0,
                    max_tokens=self.max_tokens,
                    extra_body={"structured_outputs": {"json": schema},
                                "chat_template_kwargs": {"enable_thinking": False}},
                )
            except Exception as error:
                current = {"attempt": attempt, "validation": "ERROR", "error_type": type(error).__name__,
                           "error": str(error), "prompt_sha256": prompt_hash}
                report["attempts"].append(current.copy())
                report.update(current)
                return report
            choices = getattr(response, "choices", None)
            if not choices:
                raise ValueError("task understanding returned no choices")
            choice = choices[0]
            raw = getattr(getattr(choice, "message", None), "content", None)
            current: dict[str, Any] = {
                "attempt": attempt, "raw_model_response": raw,
                "prompt_sha256": prompt_hash,
                "finish_reason": getattr(choice, "finish_reason", None), "validation": "REJECTED",
            }
            try:
                if current["finish_reason"] != "stop" or not isinstance(raw, str):
                    raise ValueError("incomplete task generation")
                task = json.loads(raw, object_pairs_hook=_unique_object)
                if self.action_language == "zh":
                    jsonschema.Draft202012Validator(schema).validate(task)
                    task = task_action_language(task, encode=False)
                validate_extraction(source_text, task)
                current.update(validation="INTENT_SCHEMA_PASS_ONLY", requested_tasks=task)
            except (ValueError, TypeError, jsonschema.ValidationError) as error:
                current.update(rejection_reason=str(error), rejection_type=type(error).__name__)
            report["attempts"].append(copy.deepcopy(current))
            if attempt < self.review_rounds:
                # The pinned deployment has a 4096-token context. Review keeps
                # source + candidate, not the entire few-shot history again.
                messages = [{"role": "system", "content": system_prompt},
                            {"role": "user", "content": source_text},
                            {"role": "assistant", "content": raw if isinstance(raw, str) else ""},
                            {"role": "user", "content": (
                                "复核上一份结果，只依据原始指令，不依据评分标签。删除误列为动作的背景描述，"
                                "不能把减速数值拆成两个动作，补查目标遗漏、左右方向、禁止动作以及后续恢复任务。"
                                "条件只能逐字摘录原文，没有明确条件就null。仅输出修正后的完整JSON。"
                                "条件不能与自身动作的evidence相同；仅有先后顺序时condition填null。"
                                "\n上一轮机械校验（不含预期动作标签）：" + current.get("rejection_reason", "引用校验通过，仍需复核语义")
                                + "\n原始指令：" + source_text
                            )}]
        # Only the final model answer is accepted; no fallback to an earlier answer.
        report.update(current)
        return report


def evaluate_development_case(report: Mapping[str, Any], expected: Mapping[str, Any]) -> dict[str, Any]:
    """Independent dev labels are used only AFTER inference, never in prompts."""
    tasks = report.get("requested_tasks", {})
    steps = tasks.get("steps", [])
    actions = [s["action"] for s in steps]
    sequences = expected["action_sequences"]
    checks = {
        "valid_extraction": report.get("validation") == "INTENT_SCHEMA_PASS_ONLY",
        "action_order": actions in sequences,
        "step_count": len(steps) in {len(seq) for seq in sequences},
        "confirmation": tasks.get("requires_confirmation") == expected.get("requires_confirmation", False),
        "prohibited_actions": set(tasks.get("prohibited_actions", {})) == set(expected.get("prohibited_actions", [])),
    }
    for field in ("speed_kph", "gap_m", "direction"):
        if field in expected:
            values = [s[field] for s in steps]
            labels = expected[field]
            checks[field] = len(values) == len(labels) and all(
                abs(actual - label) <= 1e-6 if type(actual) in (int, float) and type(label) in (int, float)
                else actual == label for actual, label in zip(values, labels)
            )
    for field in ("condition", "target_text"):
        for index, terms in expected.get(f"{field}_terms", {}).items():
            value = steps[int(index)][field] if int(index) < len(steps) else None
            checks[f"{field}_{index}"] = value is not None and all(term in value for term in terms)
    return {"scope": "DEVELOPMENT_LABEL_CHECK_NOT_FROZEN_TEST_OR_GATE", "checks": checks,
            "passed": all(checks.values()), "observed_actions": actions}


class SequenceFirstUnderstandingPlanner:
    """Model chooses sequence first, then fills model-chosen action slots.

    Fixing slots from the first model answer is not fixing them from a label.
    No missing action is added by code; wrong sequences remain wrong in scoring.
    """

    def __init__(self, transport: Any, *, max_tokens: int = 1536) -> None:
        self.transport = transport
        if type(max_tokens) is not int or not 256 <= max_tokens <= 8192:
            raise ValueError("max_tokens must be in [256, 8192]")
        self.max_tokens = max_tokens

    def generate(self, source_text: str) -> dict[str, Any]:
        if not isinstance(source_text, str) or not source_text.strip() or len(source_text) > 1000:
            raise ValueError("source_text must contain 1 to 1000 characters")
        import jsonschema
        sequence_schema = {
            "type": "object", "additionalProperties": False,
            "required": ["actions", "prohibited_actions", "requires_confirmation"],
            "properties": {
                "actions": {"type": "array", "minItems": 1, "maxItems": 8,
                            "items": {"enum": list(ACTION_COMPLETIONS)}},
                "prohibited_actions": TASK_SCHEMA["properties"]["prohibited_actions"],
                "requires_confirmation": {"type": "boolean"},
            },
        }
        system = (
            "只分解原始驾驶指令的全部肯定动作序列，不填写参数。背景/观察不是动作，条件不是单独动作。"
            "STOP停车；YIELD让人先通过；FOLLOW跟车；KEEP_LANE保持车道；SET_SPEED设置或恢复指定速度；"
            "SLOW_DOWN减速（含指定减速值，一个动作）；TURN_LEFT/RIGHT转弯；CHANGE_LANE_LEFT/RIGHT单纯变道；"
            "AVOID_OBSTACLE超越或绕障（包括所需变道）；RETURN_TO_LANE返回原车道；PULL_OVER靠边停车；HOLD不确定等待。"
            "不要把变道超车拆两次；返回、恢复是独立任务。禁止动作放prohibited_actions。仅输出JSON。"
        )
        messages = [{"role": "system", "content": system}]
        # Reuse authored examples, but sequence inference never sees slot labels
        # or the independently scored development cases.
        for text, steps, prohibited in EXAMPLES:
            messages.extend([{"role": "user", "content": text}, {"role": "assistant", "content": json.dumps({
                "actions": [s["action"] for s in steps], "prohibited_actions": prohibited,
                "requires_confirmation": False,
            }, ensure_ascii=False)}])
        messages.append({"role": "user", "content": source_text})
        report: dict[str, Any] = {
            "scope": "TEXT_INTENT_ONLY_NOT_GROUNDED_NOT_EXECUTABLE_NOT_GATE",
            "strategy": "SEQUENCE_FIRST_MODEL_SELECTED_SLOTS", "model_id": self.transport.model_id,
            "image_sent": False, "execution_constraints_applied": False,
            "ready_for_vehicle_execution": False, "task_accuracy": "NOT_MEASURED",
            "semantic_step_source": "MODEL_NOT_KEYWORD_EXPANSION", "validation": "REJECTED", "attempts": [],
            "max_output_tokens": {"sequence": min(self.max_tokens, 512), "slots": self.max_tokens},
            "source_sha256": hashlib.sha256(source_text.encode()).hexdigest(),
        }
        for stage in ("sequence", "slots"):
            schema = sequence_schema if stage == "sequence" else slots_schema
            attempt: dict[str, Any] = {"stage": stage, "validation": "REJECTED",
                "prompt_sha256": hashlib.sha256(json.dumps(messages, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                "wire_schema_sha256": hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest()}
            try:
                response = self.transport._client.chat.completions.create(
                    model=self.transport.model_id, messages=messages, temperature=0.0,
                    max_tokens=min(self.max_tokens, 512) if stage == "sequence" else self.max_tokens,
                    extra_body={"structured_outputs": {"json": schema},
                                "chat_template_kwargs": {"enable_thinking": False}},
                )
                choice = response.choices[0]
                raw = choice.message.content
                attempt.update(raw_model_response=raw, finish_reason=choice.finish_reason)
                if choice.finish_reason != "stop":
                    raise ValueError("incomplete sequence/slot generation")
                data = json.loads(raw, object_pairs_hook=_unique_object)
                jsonschema.Draft202012Validator(schema).validate(data)
                if stage == "sequence":
                    if any(a in data["prohibited_actions"] for a in data["actions"]):
                        raise ValueError("sequence includes its own prohibited action")
                    report["model_action_sequence"] = copy.deepcopy(data)
                    keys = [f"step_{i + 1}" for i in range(len(data["actions"]))]
                    slot_properties = {}
                    base = source_copy_schema(source_text)["properties"]["steps"]["items"]
                    for key, action in zip(keys, data["actions"]):
                        item = copy.deepcopy(base)
                        item["properties"]["action"] = {"const": action}
                        slot_properties[key] = item
                    slots_schema = {"type": "object", "additionalProperties": False,
                                    "required": keys, "properties": slot_properties}
                    sequence = copy.deepcopy(data)
                    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": "原始指令：" + source_text +
                                 "\n先前模型提取的动作：" + json.dumps(sequence, ensure_ascii=False) +
                                 "\n只为这些动作填写对应step_1等对象。保留原顺序。证据必须含支持该动作的命令，"
                                 "不只摘录背景/条件。条件无明确原文依据则null，不能与动作证据相同。仅输出JSON对象。"}]
                else:
                    task = {"steps": [data[key] for key in keys],
                            "prohibited_actions": sequence["prohibited_actions"],
                            "requires_confirmation": sequence["requires_confirmation"]}
                    validate_extraction(source_text, task)
                    report.update(validation="INTENT_SCHEMA_PASS_ONLY", requested_tasks=task)
                attempt["validation"] = "STAGE_SCHEMA_PASS_ONLY"
            except Exception as error:
                attempt.update(rejection_reason=str(error), rejection_type=type(error).__name__)
                report.update(rejection_reason=str(error), rejection_type=type(error).__name__)
                report["attempts"].append(attempt)
                return report
            report["attempts"].append(attempt)
        report["raw_model_response"] = report["attempts"][-1]["raw_model_response"]
        return report
