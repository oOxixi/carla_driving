"""Offline clause-focused model extraction and model-selected global ordering."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any

from .shadow_planner import _unique_object
from .task_understanding import _example_step, source_copy_schema, validate_extraction


CLAUSE_PROMPT = """你只分析本轮【当前片段】的驾驶指令动作。完整原句仅供理解目标和指代。
不要重复输出其他片段的动作。背景描述、纯条件和禁止事项可以没有肯定动作，steps可以为空。
动作：保持车道KEEP_LANE；设定/恢复速度SET_SPEED；减速SLOW_DOWN；停车STOP；
等待他人先通行YIELD；跟车FOLLOW；转弯TURN_LEFT/RIGHT；单纯变道CHANGE_LANE_LEFT/RIGHT；
超车/绕障AVOID_OBSTACLE（含变道通过）；回原车道RETURN_TO_LANE；靠边停车PULL_OVER；不确定等待HOLD。
先区分动作主体：恢复车速不是回原车道，条件里“离开车道”不是命令本车变道。
看到某物只是背景；一个减速到数值只是一项SLOW_DOWN；变道超车合成一项AVOID_OBSTACLE。
evidence摘录本片段支持动作的原文，不能仅摘条件。target_text摘录完整原句中的目标名词，否则null。
condition只摘录明确的先决条件，不包含该步的动作本身，不能与evidence相同；只有“然后/最后”时null。
speed_kph单位公里每小时，gap_m单位米；未明确数值/方向就null。禁止动作填prohibited_actions。
只输出JSON。这里不选择真实actor ID、不判断是否可以安全驾驶，也不发车辆控制。
"""


CLAUSE_EXAMPLES = (
    ("路边有小朋友", [], {}),
    ("等货车开走后再提速至42公里每小时", [
        _example_step("再提速至42公里每小时", "SET_SPEED", speed_kph=42, condition="等货车开走后"),
    ], {}),
    ("等后车通过后向右变道", [
        _example_step("向右变道", "CHANGE_LANE_RIGHT", direction="RIGHT", condition="等后车通过后"),
    ], {}),
    ("回到原车道并恢复到26公里每小时", [
        _example_step("回到原车道", "RETURN_TO_LANE"),
        _example_step("恢复到26公里每小时", "SET_SPEED", speed_kph=26),
    ], {}),
    ("不要向左变道", [], {"CHANGE_LANE_LEFT": True}),
    ("与前方出租车保持5米距离跟随", [
        _example_step("与前方出租车保持5米距离跟随", "FOLLOW", target_text="前方出租车", gap_m=5),
    ], {}),
    ("先等横穿的骑车人过去", [
        _example_step("先等横穿的骑车人过去", "YIELD", target_text="横穿的骑车人"),
    ], {}),
    ("从左边超越前方卡车", [
        _example_step("从左边超越前方卡车", "AVOID_OBSTACLE", target_text="前方卡车", direction="LEFT"),
    ], {}),
    ("最后停车", [_example_step("最后停车", "STOP")], {}),
)


def split_clauses(source: str) -> list[str]:
    """Lexical punctuation only; no intent/condition/action keyword rules."""
    if not isinstance(source, str) or not source.strip() or len(source) > 1000:
        raise ValueError("source must contain 1 to 1000 characters")
    clauses = [part.strip() for part in re.split(r"[，,。；;！？!?\n]+", source) if part.strip()]
    if not clauses or len(clauses) > 16:
        raise ValueError("clause count must be in [1, 16]")
    return clauses


class ClauseFocusedUnderstandingPlanner:
    """No infer/health or control interface; no deterministic semantic completion."""

    def __init__(self, transport: Any, *, max_tokens: int = 1536) -> None:
        if type(max_tokens) is not int or not 256 <= max_tokens <= 1536:
            raise ValueError("clause max_tokens must be in [256, 1536]")
        self.transport = transport
        self.max_tokens = max_tokens

    def _generate(self, messages, schema, attempts, stage, *, tokens=None):
        import jsonschema
        attempt = {"stage": stage, "validation": "ERROR",
                   "prompt_sha256": hashlib.sha256(json.dumps(messages, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                   "wire_schema_sha256": hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest()}
        attempts.append(attempt)
        response = self.transport._client.chat.completions.create(
            model=self.transport.model_id, messages=messages, temperature=0.0,
            max_tokens=self.max_tokens if tokens is None else tokens,
            extra_body={"structured_outputs": {"json": schema},
                        "chat_template_kwargs": {"enable_thinking": False}},
        )
        choice = response.choices[0]
        attempt.update(raw_model_response=choice.message.content, finish_reason=choice.finish_reason)
        if choice.finish_reason != "stop":
            raise ValueError("incomplete clause/order generation")
        data = json.loads(choice.message.content, object_pairs_hook=_unique_object)
        jsonschema.Draft202012Validator(schema).validate(data)
        attempt["validation"] = "WIRE_SCHEMA_PASS_ONLY"
        return data

    def generate(self, source_text: str) -> dict[str, Any]:
        from jsonschema.exceptions import ValidationError
        clauses = split_clauses(source_text)
        report = {"scope": "TEXT_INTENT_ONLY_NOT_GROUNDED_NOT_EXECUTABLE_NOT_GATE",
                  "strategy": "CLAUSE_FOCUSED_MODEL_ORDER", "model_id": self.transport.model_id,
                  "image_sent": False, "execution_constraints_applied": False,
                  "ready_for_vehicle_execution": False, "task_accuracy": "NOT_MEASURED",
                  "semantic_step_source": "MODEL_NOT_KEYWORD_EXPANSION", "validation": "REJECTED",
                  "source_sha256": hashlib.sha256(source_text.encode()).hexdigest(),
                  "clauses": clauses, "attempts": [], "clause_frames": []}
        schema = source_copy_schema(source_text)
        schema["properties"]["steps"]["minItems"] = 0
        messages = [{"role": "system", "content": CLAUSE_PROMPT}]
        for text, steps, prohibited in CLAUSE_EXAMPLES:
            messages.extend([{"role": "user", "content": "完整原句：" + text + "\n当前片段：" + text},
                             {"role": "assistant", "content": json.dumps({"steps": steps,
                                 "prohibited_actions": prohibited, "requires_confirmation": False}, ensure_ascii=False)}])
        tasks = []
        prohibited = {}
        requires_confirmation = False
        try:
            for index, clause in enumerate(clauses):
                frame = self._generate([*messages, {"role": "user", "content":
                    "完整原句：" + source_text + "\n当前片段：" + clause}], schema, report["attempts"], f"clause_{index}")
                report["clause_frames"].append(copy.deepcopy(frame))
                if frame["steps"]:
                    validate_extraction(source_text, frame)
                for step in frame["steps"]:
                    if step["evidence"] not in clause:
                        raise ValueError(f"clause {index} evidence comes from a different clause")
                tasks.extend(frame["steps"])
                prohibited.update(frame["prohibited_actions"])
                requires_confirmation |= frame["requires_confirmation"]
                report["attempts"][-1]["validation"] = "CLAUSE_SUPPORT_PASS_ONLY"
            if not 1 <= len(tasks) <= 8:
                raise ValueError("model extracted no tasks or more than eight tasks")
            # Model decides order. The schema supplies opaque node indices only.
            if len(tasks) > 1:
                keys = [f"position_{i + 1}" for i in range(len(tasks))]
                order_schema = {"type": "object", "additionalProperties": False, "required": keys,
                                "properties": {k: {"enum": list(range(len(tasks)))} for k in keys}}
                order = self._generate([
                    {"role": "system", "content": "按原句要求的实际执行先后排列任务索引。只排序，不能新增、删除、重复任务。输出JSON。"},
                    {"role": "user", "content": "原句：" + source_text + "\n模型提取的任务节点：" + json.dumps(
                        [{"index": i, **step} for i, step in enumerate(tasks)], ensure_ascii=False)},
                ], order_schema, report["attempts"], "global_order", tokens=512)
                indices = [order[k] for k in keys]
                if sorted(indices) != list(range(len(tasks))):
                    raise ValueError("model order is not a permutation; no duplicate removal performed")
                tasks = [tasks[i] for i in indices]
                report["model_order"] = indices
            task = {"steps": tasks, "prohibited_actions": prohibited, "requires_confirmation": requires_confirmation}
            validate_extraction(source_text, task)
            report.update(validation="INTENT_SCHEMA_PASS_ONLY", requested_tasks=task)
        except Exception as error:
            report.update(rejection_reason=str(error), rejection_type=type(error).__name__,
                          rejection_stage=report["attempts"][-1]["stage"] if report["attempts"] else "setup")
            if not isinstance(error, (ValueError, TypeError, ValidationError)):
                report["validation"] = "ERROR"
        return report
