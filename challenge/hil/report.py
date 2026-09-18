"""Build the Markdown test report and guard the claim scope."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .identity import CandidateIdentity
from .stages import SEGMENT_NAMES


SEGMENT_ORDER: tuple[str, ...] = tuple(
    name
    for name in (
        "preprocess_ms",
        "packing_ms",
        "inference_setup_ms",
        "model_inference_ms",
        "postprocess_ms",
        "adapter_ms",
        "plan_validation_ms",
        "pre_model_ms",
        "post_model_ms",
        "model_only_ms",
        "planner_overhead_ms",
        "planner_e2e_ms",
    )
    if name in SEGMENT_NAMES
)

SEGMENT_LABELS: dict[str, str] = {
    "preprocess_ms": "预处理 (T0→T1)",
    "packing_ms": "Token/Target packing (T1→T2)",
    "inference_setup_ms": "推理提交开销 (T2→T3)",
    "model_inference_ms": "模型纯推理 (T3→T4)",
    "postprocess_ms": "后处理 (T4→T5)",
    "adapter_ms": "Student Adapter (T5→T6)",
    "plan_validation_ms": "计划校验 (T6→T7)",
    "pre_model_ms": "进入推理前合计 (T0→T3)",
    "post_model_ms": "推理后合计 (T4→T7)",
    "model_only_ms": "模型纯推理",
    "planner_overhead_ms": "Planner 额外开销",
    "planner_e2e_ms": "完整 Planner 端到端 (T0→T7)",
}


REPORT_FILENAME_J6P = "j6p_test_report.md"
REPORT_FILENAME_X86 = "x86_test_report.md"


def report_filename(device_class: str) -> str:
    """Name the report after the environment it actually measured.

    The challenge deliverable is named ``j6p_test_report.md``; an X86
    pre-validation run must not produce a file with that name, or a reader will
    mistake it for board evidence.
    """
    return REPORT_FILENAME_J6P if device_class == "J6P_BOARD" else REPORT_FILENAME_X86


def claim_scope(
    *,
    device_class: str,
    power_measured: bool,
    bpu_measured: bool,
) -> dict[str, Any]:
    if device_class == "J6P_BOARD":
        scope = "J6P_ON_DEVICE"
        j6p_status = "J6P_MEASURED"
        allowed = ["J6P 板端实测延时与内存结论"]
        if power_measured:
            allowed.append("J6P 实测评均/峰值功耗结论")
        if bpu_measured:
            allowed.append("J6P BPU 利用率原始采样值（公式未确认前不给结论）")
    else:
        scope = "X86_PRE_VALIDATED"
        j6p_status = "J6P_PENDING"
        allowed = [
            "工具链与测量流程的正确性",
            "相对趋势（同一主机、同一配置下的版本间比较）",
        ]
    forbidden = [
        "把 X86 或桌面 GPU 结果写成 J6P 实机达标",
        "把模型文件大小当作运行内存",
        "用 INT8 体积下降代替 FLOPs 下降",
        "用估算值或 TDP 代替实测功耗",
        "用未确认公式给出“异构算力利用率 = xx%”结论",
    ]
    if not power_measured:
        forbidden.append("在功耗未实测时给出功耗达标结论")
    if not bpu_measured:
        forbidden.append("在 BPU 未实测时给出 BPU 利用率结论")
    return {
        "scope": scope,
        "j6p_status": j6p_status,
        "allowed_claims": allowed,
        "forbidden_claims": forbidden,
    }


def _table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for row in rows:
        lines.append("| " + " | ".join("" if cell is None else str(cell) for cell in row) + " |")
    return lines


def _number(value: Any, digits: int = 3) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.{digits}f}"
    return ""


def _latency_table(metrics: Mapping[str, Any]) -> list[str]:
    rows = []
    for name in SEGMENT_ORDER:
        stats = metrics.get(name)
        if not stats or stats.get("count") in (None, 0):
            continue
        rows.append(
            [
                SEGMENT_LABELS.get(name, name),
                stats.get("count"),
                _number(stats.get("mean")),
                _number(stats.get("p50")),
                _number(stats.get("p95")),
                _number(stats.get("p99")),
                _number(stats.get("max")),
            ]
        )
    if not rows:
        return ["（无有效 measured 样本）"]
    return _table(["时段", "n", "mean", "P50", "P95", "P99", "max"], rows)


def build_report(
    *,
    run_id: str,
    identity: CandidateIdentity,
    capabilities: Mapping[str, Any],
    hardware_env: Mapping[str, Any],
    latency_report: Mapping[str, Any],
    replay_summary: Mapping[str, Any] | None,
    telemetry: Mapping[str, Any] | None,
    failure_summary: Mapping[str, Any] | None,
    run_summary: Mapping[str, Any] | None,
    blocked_on: Sequence[str],
    extra_notes: Sequence[str] = (),
    stability_summary: Mapping[str, Any] | None = None,
) -> str:
    scope = claim_scope(
        device_class=str(hardware_env.get("device_class", "X86_WORKSTATION")),
        power_measured=bool((telemetry or {}).get("power", {}).get("measured")),
        bpu_measured=bool((telemetry or {}).get("utilization", {}).get("bpu_measured")),
    )
    lines: list[str] = []
    lines.append(f"# B3 HIL / J6P 实测报告 — `{run_id}`")
    lines.append("")
    lines.append(f"- 生成时间（UTC）：`{datetime.now(timezone.utc).isoformat()}`")
    lines.append(f"- 可信范围：`{scope['scope']}`")
    lines.append(f"- J6P 状态：`{scope['j6p_status']}`")
    lines.append("")
    lines.append("> 本报告的全部数字来源于同一次运行目录内的原始文件，")
    lines.append("> 每个文件的 SHA256 记录在 `measurement_manifest.json` 中。")
    lines.append("")

    lines.append("## 1. 被测身份（五标识）")
    lines.append("")
    lines.extend(
        _table(
            ["字段", "值"],
            [
                ["git_sha", identity.git_sha],
                ["model_id", identity.model_id],
                ["model_sha256", identity.model_sha256],
                ["dataset_version", identity.dataset_version],
                ["config_id", identity.config_id],
                ["weights gate_status", identity.gate_status],
                ["身份完整", "是" if identity.complete else "否"],
            ],
        )
    )
    lines.append("")
    if not identity.complete:
        lines.append(
            f"> 身份不完整，缺失：`{', '.join(identity.missing())}`。"
            "本次结果**只能**作为工具链验证，不能作为任何 Gate 的通过依据。"
        )
        lines.append("")
    lines.append("被测链能力：")
    lines.append("")
    lines.extend(
        _table(
            ["能力", "状态"],
            [
                ["完整 Planner 链", capabilities.get("full_chain")],
                ["模型纯推理", capabilities.get("model_only")],
                ["PlanValidator", capabilities.get("plan_validator")],
                ["打点来源", capabilities.get("stage_source")],
            ],
        )
    )
    lines.append("")
    for note in capabilities.get("notes", ()):
        lines.append(f"- 说明：{note}")
    lines.append("")

    lines.append("## 2. 测量环境")
    lines.append("")
    lines.extend(
        _table(
            ["字段", "值"],
            [
                ["device_class", hardware_env.get("device_class")],
                ["host", hardware_env.get("host", {}).get("hostname") if isinstance(hardware_env.get("host"), Mapping) else None],
                ["cpu", hardware_env.get("host", {}).get("cpu_model") if isinstance(hardware_env.get("host"), Mapping) else None],
                ["accelerator", hardware_env.get("accelerator", {}).get("name") if isinstance(hardware_env.get("accelerator"), Mapping) else None],
                ["bpu", hardware_env.get("bpu")],
                ["openexplorer", hardware_env.get("openexplorer")],
                ["power_measurement", hardware_env.get("power_measurement")],
                ["cpu_governor", hardware_env.get("cpu_governor")],
                ["torch", (hardware_env.get("runtime_libraries") or {}).get("torch")],
                ["onnxruntime", (hardware_env.get("runtime_libraries") or {}).get("onnxruntime")],
                ["numpy", (hardware_env.get("runtime_libraries") or {}).get("numpy")],
                ["电源", hardware_env.get("power_source")],
                ["CPU 标定 (ms)", hardware_env.get("cpu_calibration_ms")],
                ["时钟源", (hardware_env.get("clock") or {}).get("source")],
                ["时钟分辨率 (ns)", (hardware_env.get("clock") or {}).get("resolution_ns")],
            ],
        )
    )
    lines.append("")
    clock = hardware_env.get("clock") or {}
    platform_resolution = clock.get("platform_monotonic_resolution_ns")
    if isinstance(platform_resolution, (int, float)) and platform_resolution > 1_000_000:
        lines.append(
            f"> 注意：本机 `time.monotonic` 分辨率约 {platform_resolution / 1e6:.1f} ms，"
            "低于该量级的推理会被量化成 0，因此本次测量统一使用 "
            f"`{clock.get('source')}`（分辨率 {clock.get('resolution_ns')} ns）。"
        )
        lines.append("")

    lines.append("## 3. 延迟")
    lines.append("")
    lines.append(
        "口径：单调时钟纳秒；预热样本单独记录且不计入统计；"
        "仅 `outcome=READY` 的 measured 样本进入百分位；百分位为线性插值。"
    )
    lines.append("")
    lines.append(
        f"有效样本 `{latency_report.get('measured_ready_count')}` / "
        f"总记录 `{latency_report.get('trace_count')}`；"
        f"结果分布 `{latency_report.get('outcome_counts')}`。"
    )
    lines.append("")
    lines.extend(_latency_table(latency_report.get("metrics_ms", {})))
    lines.append("")
    rounds = latency_report.get("rounds") or {}
    if rounds:
        lines.append("### 3.1 分轮 P95 / max（ms）")
        lines.append("")
        rows = []
        for round_id in sorted(rounds, key=lambda item: int(item)):
            metrics = rounds[round_id].get("metrics_ms", {})
            e2e = metrics.get("planner_e2e_ms") or {}
            model = metrics.get("model_only_ms") or {}
            rows.append(
                [
                    round_id,
                    rounds[round_id].get("count"),
                    _number(e2e.get("p95")),
                    _number(e2e.get("max")),
                    _number(model.get("p95")),
                ]
            )
        lines.extend(
            _table(["round", "n", "E2E P95", "E2E max", "模型 P95"], rows)
        )
        lines.append("")
    for note in extra_notes:
        lines.append(f"- {note}")
    lines.append("")

    lines.append("## 4. 内存")
    lines.append("")
    memory = (telemetry or {}).get("memory", {})
    lines.extend(
        _table(
            ["指标", "值"],
            [
                ["采样数", memory.get("sample_count")],
                ["进程峰值 RSS (KiB)", _number(memory.get("rss_kib_max"), 1)],
                ["进程峰值 RSS (MiB)", _number(memory.get("peak_rss_mib_max"), 2)],
                ["数据来源", memory.get("source")],
            ],
        )
    )
    lines.append("")
    lines.append("> 运行内存为进程实测峰值 RSS，与模型文件大小无关。")
    lines.append("")

    lines.append("## 5. 功耗")
    lines.append("")
    power = (telemetry or {}).get("power", {})
    if power.get("measured"):
        lines.extend(
            _table(
                ["指标", "值"],
                [
                    ["采样数", power.get("sample_count")],
                    ["平均功率 (W)", _number(power.get("power_w_mean"))],
                    ["峰值功率 (W)", _number(power.get("power_w_max"))],
                    ["取电点", power.get("probe_point")],
                    ["来源", power.get("source")],
                ],
            )
        )
    else:
        lines.append(
            f"`NOT_MEASURED`：本机没有配置功耗探针（`{power.get('source')}`）。"
            "按口径要求，此状态下不给出任何功耗结论。"
        )
    lines.append("")

    lines.append("## 6. 算力利用率")
    lines.append("")
    utilization = (telemetry or {}).get("utilization", {})
    lines.extend(
        _table(
            ["指标", "值"],
            [
                ["采样数", utilization.get("sample_count")],
                ["进程 CPU 峰值 (%)", _number(utilization.get("cpu_percent_max"), 1)],
                ["BPU 均值 (%)", _number(utilization.get("bpu_percent_mean"), 1)],
                ["BPU 是否实测", "是" if utilization.get("bpu_measured") else "否"],
            ],
        )
    )
    lines.append("")
    lines.append(
        "> “异构算力利用率 ≥80%”的正式公式由 A4/B2 确认前，"
        "本报告只提供原始采样值，不给结论行。"
    )
    lines.append("")

    lines.append("## 7. 回放与输入输出一致性")
    lines.append("")
    if replay_summary:
        lines.extend(
            _table(
                ["指标", "值"],
                [
                    ["回放样本数", replay_summary.get("case_count")],
                    ["计划产出率", _number(replay_summary.get("ready_rate"), 4)],
                    ["图像解析成功率", _number(replay_summary.get("rgb_resolution_rate"), 4)],
                    ["结构检查通过率", _number(replay_summary.get("structural_pass_rate"), 4)],
                    ["Teacher 对比", replay_summary.get("teacher_comparison")],
                ],
            )
        )
        lines.append("")
        lines.append(f"> {replay_summary.get('teacher_comparison_reason', '')}")
    else:
        lines.append("（本次运行未执行回放）")
    lines.append("")

    lines.append("## 8. 异常输入")
    lines.append("")
    if failure_summary:
        rows = [
            [item.get("case_id"), item.get("verdict"), item.get("outcome")]
            for item in failure_summary.get("cases", [])
        ]
        lines.extend(_table(["用例", "观察结论", "outcome"], rows))
        lines.append("")
        lines.append(f"> {failure_summary.get('policy_note', '')}")
    else:
        lines.append("（本次运行未执行异常用例）")
    lines.append("")

    lines.append("## 9. 长稳与内存漂移")
    lines.append("")
    if stability_summary:
        latency = stability_summary.get("latency_ms", {})
        lines.extend(
            _table(
                ["指标", "值"],
                [
                    ["请求时长 (s)", _number(stability_summary.get("requested_duration_s"), 1)],
                    ["实测时长 (s)", _number(stability_summary.get("observed_duration_s"), 1)],
                    ["时长达标", stability_summary.get("duration_met")],
                    ["请求数", stability_summary.get("iterations")],
                    ["成功率", _number(stability_summary.get("success_rate"), 5)],
                    ["首窗 P95 (ms)", _number(latency.get("first_window_p95"))],
                    ["末窗 P95 (ms)", _number(latency.get("last_window_p95"))],
                    ["整体 P95 (ms)", _number(latency.get("overall_p95"))],
                    ["内存漂移 (KiB)", _number(stability_summary.get("memory_drift_kib"), 1)],
                    ["内存漂移比例", _number(stability_summary.get("memory_drift_ratio"), 5)],
                    ["recovery probe 失败数", (stability_summary.get("recovery_probe") or {}).get("errors")],
                    ["长稳结论", "通过" if stability_summary.get("success") else "未通过"],
                ],
            )
        )
        lines.append("")
        lines.append("判定条件：" + "；".join(stability_summary.get("criteria", [])))
    else:
        lines.append("（本次运行未执行长稳）")
    lines.append("")

    lines.append("## 10. 运行摘要")
    lines.append("")
    if run_summary:
        lines.extend(
            _table(
                ["字段", "值"],
                [
                    ["轮数", run_summary.get("rounds")],
                    ["measured 记录", run_summary.get("measured_traces")],
                    ["warmup 记录", run_summary.get("warmup_traces")],
                    ["回放记录", run_summary.get("replay_rows")],
                    ["总耗时 (s)", _number(run_summary.get("duration_s"), 2)],
                ],
            )
        )
    lines.append("")

    lines.append("## 11. 可信范围与禁止表述")
    lines.append("")
    lines.append("允许的结论：")
    lines.append("")
    for item in scope["allowed_claims"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("禁止的表述：")
    lines.append("")
    for item in scope["forbidden_claims"]:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## 12. 未解除的外部依赖")
    lines.append("")
    if blocked_on:
        for item in blocked_on:
            lines.append(f"- `{item}`")
    else:
        lines.append("- 无")
    lines.append("")
    return "\n".join(lines) + "\n"


__all__ = [
    "build_report",
    "claim_scope",
    "report_filename",
    "SEGMENT_ORDER",
    "SEGMENT_LABELS",
    "REPORT_FILENAME_J6P",
    "REPORT_FILENAME_X86",
]
