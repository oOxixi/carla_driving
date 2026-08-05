"""Evaluate Qwen on the frozen expanded CARLA language benchmark.

This is an isolated language + structured-scene evaluation.  It does not use
RGB frames, execute CARLA, or change the five-action production adapter.
"""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import time
from typing import Any


ACTION_TO_CODE = {
    "START": "A",
    "STOP": "B",
    "KEEP_LANE": "C",
    "SET_SPEED": "D",
    "EMERGENCY_STOP": "E",
    "TURN_LEFT": "F",
    "TURN_RIGHT": "G",
    "CHANGE_LANE_LEFT": "H",
    "CHANGE_LANE_RIGHT": "I",
    "AVOID_OBJECT": "J",
    "REQUEST_CONFIRMATION": "K",
}
CODE_TO_ACTION = {code: action for action, code in ACTION_TO_CODE.items()}

SYSTEM_PROMPT = """你是 CARLA 自动驾驶车辆的高层决策分类器。输入包含中文驾驶指令和仿真器导出的结构化场景事实。只选择当前首先应执行的一个高层动作。

必须遵守以下优先级：
1. 安全事实优先于用户指令。迫近碰撞、前车紧急制动且距离不足、行人或障碍物造成的即时危险，选择 EMERGENCY_STOP。
2. 请求的变道因目标车道被占用或间隙不安全时，保持原车道 KEEP_LANE，不要改为绕障；请求转向与交通参与者冲突时选择 STOP。
3. 目标有多个且无法唯一定位、目标不存在，或感知/能见度/导航信息不足以确定唯一安全动作时，选择 REQUEST_CONFIRMATION；但指令明确要求停车等待时选择 STOP。
4. 复合指令按结构化场景中的 priority、primary_action 和安全优先级选择当前第一动作。
5. 没有冲突或不确定性时，准确执行驾驶指令。减速或设定/保持具体速度均归为 SET_SPEED；正常跟车和沿当前道路行驶归为 KEEP_LANE。

动作代码：
A=START
B=STOP
C=KEEP_LANE
D=SET_SPEED
E=EMERGENCY_STOP
F=TURN_LEFT
G=TURN_RIGHT
H=CHANGE_LANE_LEFT
I=CHANGE_LANE_RIGHT
J=AVOID_OBJECT
K=REQUEST_CONFIRMATION

只输出一个大写代码，不要解释。"""


def build_case_prompt(record: dict[str, Any]) -> str:
    """Build a prompt without exposing any evaluation label or category."""
    instruction = record.get("template")
    scene = record.get("scene_constraints")
    if not isinstance(instruction, str) or not instruction.strip():
        raise ValueError("record template must be a non-empty string")
    if not isinstance(scene, dict):
        raise ValueError("record scene_constraints must be an object")
    scene_json = json.dumps(
        scene,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"驾驶指令：{instruction.strip()}\n结构化场景：{scene_json}"


def _percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _latency_summary(values: list[float]) -> dict[str, float | int | None]:
    return {
        "count": len(values),
        "mean_ms": statistics.fmean(values) if values else None,
        "p50_ms": _percentile(values, 0.50),
        "p95_ms": _percentile(values, 0.95),
        "p99_ms": _percentile(values, 0.99),
        "max_ms": max(values) if values else None,
    }


def _group_metrics(
    records: list[dict[str, Any]],
    field: str,
) -> dict[str, dict[str, float | int]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[str(record[field])].append(record)
    result: dict[str, dict[str, float | int]] = {}
    for name in sorted(groups):
        rows = groups[name]
        correct = sum(row["correct"] is True for row in rows)
        ready = sum(row["status"] == "READY" for row in rows)
        result[name] = {
            "count": len(rows),
            "ready": ready,
            "correct": correct,
            "accuracy": correct / len(rows),
            "strict_parse_rate": ready / len(rows),
        }
    return result


def _input_integrity(source_records: list[dict[str, Any]]) -> dict[str, int]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in source_records:
        groups[build_case_prompt(record)].append(record)
    conflicts = [
        rows
        for rows in groups.values()
        if len({row["expected_action"] for row in rows}) > 1
    ]
    return {
        "source_records": len(source_records),
        "unique_model_inputs": len(groups),
        "duplicate_model_input_records": len(source_records) - len(groups),
        "conflicting_input_groups": len(conflicts),
        "conflicting_input_records": sum(len(rows) for rows in conflicts),
    }


def summarize_records(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    if not records:
        raise ValueError("records must not be empty")
    total = len(records)
    ready = sum(record["status"] == "READY" for record in records)
    correct = sum(record["correct"] is True for record in records)
    latencies = [
        float(record["latency_ms"])
        for record in records
        if record["status"] == "READY"
    ]
    end_to_end_latencies = [
        float(record["end_to_end_latency_ms"])
        for record in records
        if record["status"] == "READY"
    ]
    queue_waits = [
        float(record["queue_wait_ms"])
        for record in records
        if record["status"] == "READY"
    ]
    confidences = [
        float(record["confidence"])
        for record in records
        if record.get("confidence") is not None
    ]
    confusion: dict[str, Counter[str]] = defaultdict(Counter)
    for record in records:
        predicted = record.get("predicted_action") or "ERROR"
        confusion[str(record["expected_action"])][str(predicted)] += 1
    by_category = _group_metrics(records, "category")
    return {
        "total": total,
        "ready": ready,
        "errors": total - ready,
        "correct": correct,
        "action_accuracy": correct / total,
        "strict_parse_rate": ready / total,
        "macro_category_accuracy": statistics.fmean(
            float(metrics["accuracy"]) for metrics in by_category.values()
        ),
        "request_latency_ms_under_configured_concurrency": _latency_summary(
            latencies
        ),
        "queue_wait_ms": _latency_summary(queue_waits),
        "end_to_end_latency_ms_including_local_queue": _latency_summary(
            end_to_end_latencies
        ),
        "selected_token_confidence": {
            "mean": statistics.fmean(confidences) if confidences else None,
            "p05": _percentile(confidences, 0.05),
            "p50": _percentile(confidences, 0.50),
        },
        "by_category": by_category,
        "by_expected_action": _group_metrics(records, "expected_action"),
        "by_safety_policy": _group_metrics(records, "safety_policy"),
        "confusion_matrix": {
            expected: dict(sorted(counts.items()))
            for expected, counts in sorted(confusion.items())
        },
    }


def _extract_choice(response: Any) -> tuple[str, float | None, list[dict[str, Any]]]:
    choices = getattr(response, "choices", None)
    if not choices:
        raise RuntimeError("server returned no completion choices")
    choice = choices[0]
    content = getattr(getattr(choice, "message", None), "content", None)
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("server returned an empty response")
    code = content.strip().upper()
    if code not in CODE_TO_ACTION:
        raise RuntimeError(f"server returned invalid action code: {code!r}")

    confidence: float | None = None
    alternatives: list[dict[str, Any]] = []
    entries = getattr(getattr(choice, "logprobs", None), "content", None)
    if entries:
        first = entries[0]
        value = getattr(first, "logprob", None)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            confidence = max(0.0, min(1.0, math.exp(float(value))))
        for alternative in getattr(first, "top_logprobs", None) or []:
            token = str(getattr(alternative, "token", "")).strip().upper()
            logprob = getattr(alternative, "logprob", None)
            if token in CODE_TO_ACTION and isinstance(logprob, (int, float)):
                alternatives.append({
                    "code": token,
                    "action": CODE_TO_ACTION[token],
                    "probability": max(
                        0.0,
                        min(1.0, math.exp(float(logprob))),
                    ),
                })
    return code, confidence, alternatives


async def _evaluate_one(
    *,
    client: Any,
    semaphore: asyncio.Semaphore,
    model: str,
    index: int,
    record: dict[str, Any],
    retries: int,
) -> dict[str, Any]:
    enqueued_ns = time.perf_counter_ns()
    error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            async with semaphore:
                request_started_ns = time.perf_counter_ns()
                response = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": build_case_prompt(record)},
                    ],
                    temperature=0.0,
                    max_tokens=1,
                    logprobs=True,
                    top_logprobs=5,
                    extra_body={
                        "structured_outputs": {
                            "choice": list(CODE_TO_ACTION),
                        },
                        "chat_template_kwargs": {"enable_thinking": False},
                    },
                )
                request_finished_ns = time.perf_counter_ns()
            code, confidence, alternatives = _extract_choice(response)
            predicted_action = CODE_TO_ACTION[code]
            return {
                "index": index,
                "id": record["id"],
                "category": record["category"],
                "safety_policy": record["safety_policy"],
                "instruction": record["template"],
                "expected_action": record["expected_action"],
                "predicted_action": predicted_action,
                "predicted_code": code,
                "correct": predicted_action == record["expected_action"],
                "status": "READY",
                "confidence": confidence,
                "top_alternatives": alternatives,
                "latency_ms": (
                    request_finished_ns - request_started_ns
                ) / 1e6,
                "queue_wait_ms": (
                    request_started_ns - enqueued_ns
                ) / 1e6,
                "end_to_end_latency_ms": (
                    request_finished_ns - enqueued_ns
                ) / 1e6,
                "attempts": attempt + 1,
            }
        except Exception as caught:  # the raw record preserves the exact error
            error = caught
            if attempt < retries:
                await asyncio.sleep(0.2 * (attempt + 1))
    assert error is not None
    return {
        "index": index,
        "id": record.get("id", f"index-{index}"),
        "category": record.get("category", "unknown"),
        "safety_policy": record.get("safety_policy", "unknown"),
        "instruction": record.get("template"),
        "expected_action": record.get("expected_action", "unknown"),
        "predicted_action": None,
        "correct": False,
        "status": "ERROR",
        "error_type": type(error).__name__,
        "error": str(error),
        "latency_ms": (time.perf_counter_ns() - enqueued_ns) / 1e6,
        "queue_wait_ms": None,
        "end_to_end_latency_ms": (
            time.perf_counter_ns() - enqueued_ns
        ) / 1e6,
        "attempts": retries + 1,
    }


def _select_records(
    records: list[dict[str, Any]],
    *,
    categories: list[str],
    sample_per_category: int | None,
    limit: int | None,
) -> list[dict[str, Any]]:
    selected = [
        record
        for record in records
        if not categories or record.get("category") in categories
    ]
    if sample_per_category is not None:
        counts: Counter[str] = Counter()
        sampled: list[dict[str, Any]] = []
        for record in selected:
            category = str(record["category"])
            if counts[category] < sample_per_category:
                sampled.append(record)
                counts[category] += 1
        selected = sampled
    if limit is not None:
        selected = selected[:limit]
    if not selected:
        raise ValueError("record selection is empty")
    return selected


async def _run(args: argparse.Namespace) -> int:
    try:
        from openai import AsyncOpenAI
    except ImportError as error:
        raise RuntimeError(
            "install the optional client from requirements-qwen-client.txt"
        ) from error

    dataset_path = args.dataset.expanduser().resolve()
    source_bytes = dataset_path.read_bytes()
    source_records = json.loads(source_bytes)
    if not isinstance(source_records, list) or not source_records:
        raise ValueError("dataset must be a non-empty JSON array")
    dataset_actions = {record["expected_action"] for record in source_records}
    unknown_actions = dataset_actions - set(ACTION_TO_CODE)
    if unknown_actions:
        raise ValueError(f"dataset contains unsupported actions: {unknown_actions}")
    selected = _select_records(
        source_records,
        categories=args.category,
        sample_per_category=args.sample_per_category,
        limit=args.limit,
    )

    client = AsyncOpenAI(
        base_url=args.base_url.rstrip("/"),
        api_key=os.environ.get("QWEN_API_KEY", "unused"),
        timeout=args.timeout_s,
        max_retries=0,
    )
    semaphore = asyncio.Semaphore(args.concurrency)
    started_ns = time.perf_counter_ns()
    tasks = [
        asyncio.create_task(_evaluate_one(
            client=client,
            semaphore=semaphore,
            model=args.model,
            index=index,
            record=record,
            retries=args.retries,
        ))
        for index, record in enumerate(selected)
    ]
    completed = 0
    results: list[dict[str, Any]] = []
    try:
        for task in asyncio.as_completed(tasks):
            results.append(await task)
            completed += 1
            if completed % args.progress_every == 0 or completed == len(tasks):
                correct = sum(record["correct"] is True for record in results)
                print(
                    f"completed {completed}/{len(tasks)} "
                    f"running_accuracy={correct / completed:.4f}",
                    flush=True,
                )
    finally:
        await client.close()
    elapsed_s = (time.perf_counter_ns() - started_ns) / 1e9
    results.sort(key=lambda record: int(record["index"]))

    metrics = summarize_records(results)
    incorrect = [record for record in results if record["correct"] is not True]
    output = args.output.expanduser().resolve()
    records_output = (
        args.records_output.expanduser().resolve()
        if args.records_output
        else output.with_suffix(".records.jsonl")
    )
    report = {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_kind": "language_plus_structured_scene_no_rgb_no_carla_execution",
        "scope_warning": (
            "This isolated 11-action evaluation does not modify or prove the "
            "five-action production adapter, visual grounding, or CARLA control."
        ),
        "dataset": str(dataset_path),
        "dataset_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "dataset_records": len(source_records),
        "selected_records": len(selected),
        "selection": {
            "categories": args.category,
            "sample_per_category": args.sample_per_category,
            "limit": args.limit,
        },
        "input_integrity_full_dataset": _input_integrity(source_records),
        "prompt_contract": {
            "input_fields": ["template", "scene_constraints"],
            "hidden_evaluation_fields": [
                "id",
                "category",
                "semantic_intent",
                "expected_action",
                "expected_parameters",
                "safety_policy",
            ],
            "action_to_code": ACTION_TO_CODE,
            "temperature": 0.0,
            "max_tokens": 1,
            "structured_choice": True,
        },
        "model": args.model,
        "base_url": args.base_url,
        "inference_hardware": {
            "name": args.server_gpu_name,
            "memory_mib": args.server_gpu_memory_mib,
            "source": (
                "operator-supplied remote nvidia-smi snapshot"
                if args.server_gpu_name
                else "not captured"
            ),
        },
        "concurrency": args.concurrency,
        "timeout_s": args.timeout_s,
        "retries": args.retries,
        "wall_time_s": elapsed_s,
        "throughput_records_per_s": len(results) / elapsed_s,
        "metrics": metrics,
        "incorrect_examples": incorrect[: args.max_incorrect_examples],
        "records_output": str(records_output),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    records_output.parent.mkdir(parents=True, exist_ok=True)
    records_output.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False) + "\n"
            for record in results
        ),
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(output),
        "records_output": str(records_output),
        "action_accuracy": metrics["action_accuracy"],
        "macro_category_accuracy": metrics["macro_category_accuracy"],
        "strict_parse_rate": metrics["strict_parse_rate"],
        "wall_time_s": elapsed_s,
    }, ensure_ascii=False), flush=True)
    return 0 if metrics["strict_parse_rate"] == 1.0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path(
            "CARLA-Language-Benchmark/datasets/final_benchmark/"
            "CARLA_language_benchmark_v1_normalized.json"
        ),
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("QWEN_BASE_URL", "http://127.0.0.1:8000/v1"),
    )
    parser.add_argument("--model", default=os.environ.get("QWEN_MODEL", "qwen2.5-vl"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--records-output", type=Path)
    parser.add_argument("--category", action="append", default=[])
    parser.add_argument("--sample-per-category", type=int)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--timeout-s", type=float, default=20.0)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--progress-every", type=int, default=100)
    parser.add_argument("--max-incorrect-examples", type=int, default=50)
    parser.add_argument("--server-gpu-name")
    parser.add_argument("--server-gpu-memory-mib", type=int)
    args = parser.parse_args()
    for name in ("concurrency", "progress_every"):
        if getattr(args, name) < 1:
            parser.error(f"--{name.replace('_', '-')} must be positive")
    for name in ("sample_per_category", "limit"):
        value = getattr(args, name)
        if value is not None and value < 1:
            parser.error(f"--{name.replace('_', '-')} must be positive")
    if args.retries < 0:
        parser.error("--retries must be non-negative")
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ACTION_TO_CODE",
    "CODE_TO_ACTION",
    "build_case_prompt",
    "summarize_records",
]
