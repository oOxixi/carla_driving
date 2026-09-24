"""Build the Markdown test report and guard the claim scope."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .gate import (
    J6P_MEASURED_SCOPES,
    SCOPE_J6P_BRINGUP,
    SCOPE_J6P_ON_DEVICE,
    SCOPE_J6P_UNVERIFIED,
    failed_names,
    scope_checks,
    scope_decision,
)
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
REPORT_FILENAME_J6P_BRINGUP = "j6p_bringup_report.md"
REPORT_FILENAME_J6P_UNVERIFIED = "j6p_unverified_report.md"
REPORT_FILENAME_X86 = "x86_test_report.md"

SCOPE_FILENAMES: dict[str, str] = {
    SCOPE_J6P_ON_DEVICE: REPORT_FILENAME_J6P,
    SCOPE_J6P_BRINGUP: REPORT_FILENAME_J6P_BRINGUP,
    SCOPE_J6P_UNVERIFIED: REPORT_FILENAME_J6P_UNVERIFIED,
}


def report_filename(scope: str | Mapping[str, Any]) -> str:
    """Name the report after the scope the evidence actually supports.

    The challenge deliverable is ``j6p_test_report.md``.  Only a scope that was
    derived from a complete board evidence chain may produce that name: a bare
    ``--device-class J6P_BOARD`` string has no evidence behind it, so it maps to
    the X86 pre-validation name instead of being mistaken for board evidence.
    """
    value = scope.get("scope") if isinstance(scope, Mapping) else scope
    return SCOPE_FILENAMES.get(str(value or ""), REPORT_FILENAME_X86)


_FORBIDDEN_BASE: tuple[str, ...] = (
    "把 X86 或桌面 GPU 结果写成 J6P 实机达标",
    "把模型文件大小当作运行内存",
    "用 INT8 体积下降代替 FLOPs 下降",
    "用估算值或 TDP 代替实测功耗",
    "用未确认公式给出“异构算力利用率 = xx%”结论",
)


def claim_scope(
    *,
    device_class: str,
    identity: Any = None,
    artifact: Mapping[str, Any] | None = None,
    runtime: Mapping[str, Any] | None = None,
    hardware_env: Mapping[str, Any] | None = None,
    telemetry: Mapping[str, Any] | None = None,
    board_runtime: Mapping[str, Any] | None = None,
    rounds_measured: int | None = None,
    stability: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Derive the claim scope from verified evidence.

    There is deliberately no flag that can raise the scope on its own: every
    input is either material produced by the run (artifact digest, trace source,
    board log, telemetry probe source, verified weight manifest) or a summary of
    it.  Missing evidence lowers the scope, so a board-classified run without the
    full chain is reported as unverified rather than as measured.
    """
    capabilities = (runtime or {}).get("capabilities") if isinstance(runtime, Mapping) else None
    checks = scope_checks(
        device_class=device_class,
        identity=identity,
        artifact=artifact,
        capabilities=capabilities if isinstance(capabilities, Mapping) else None,
        hardware_env=hardware_env,
        telemetry=telemetry,
        board_runtime=board_runtime,
        rounds_measured=rounds_measured,
        stability=stability,
    )
    decision = scope_decision(device_class=device_class, checks=checks)
    passed = {str(item["name"]): bool(item.get("passed")) for item in checks}
    power_ok = passed.get("power_probe_verified", False)
    bpu_ok = passed.get("bpu_probe_verified", False)

    if decision.scope == SCOPE_J6P_ON_DEVICE:
        allowed = ["J6P 板端实测延时与内存结论"]
        if power_ok:
            allowed.append("J6P 实测评均/峰值功耗结论")
        if bpu_ok:
            allowed.append("J6P BPU 利用率原始采样值（公式未确认前不给结论）")
    elif decision.scope == SCOPE_J6P_BRINGUP:
        allowed = [
            "J6P bring-up：模型加载与功能一致性",
            "被测 Runtime 的请求/计划接口通过性",
        ]
    elif decision.scope == SCOPE_J6P_UNVERIFIED:
        allowed = ["仅记录本次运行的原始事实，不得据此给出任何 J6P 结论"]
    else:
        allowed = [
            "工具链与测量流程的正确性",
            "相对趋势（同一主机、同一配置下的版本间比较）",
        ]
        if decision.scope == "X86_CANDIDATE_PREVALIDATED":
            allowed.append("已核验身份的 candidate 在 X86 上的同机复现与预验证")

    forbidden = list(_FORBIDDEN_BASE)
    if decision.scope not in J6P_MEASURED_SCOPES:
        forbidden.append("把本次运行写成 J6P 实机达标")
    if not power_ok:
        forbidden.append("在功耗未实测时给出功耗达标结论")
    if not bpu_ok:
        forbidden.append("在 BPU 未实测时给出 BPU 利用率结论")
    return {
        "scope": decision.scope,
        "evidence_level": decision.evidence_level,
        "j6p_status": decision.j6p_status,
        "checks": checks,
        "failed_checks": failed_names(checks),
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


def _group_lines(groups: Mapping[str, Any] | None) -> list[str]:
    """Render the per-group table; labels come from B2, B3 only counts."""
    if not isinstance(groups, Mapping) or not groups.get("groups"):
        return []
    lines = ["", "### 7.1 分组统计（标签来源：" + str(groups.get("group_map_path") or "冻结输入/未标注") + "）", ""]
    rows = []
    for name in sorted(groups["groups"]):
        item = groups["groups"][name]
        rows.append(
            [
                name,
                item.get("case_count"),
                _number(item.get("ready_rate"), 4),
                _number(item.get("structural_pass_rate"), 4),
                item.get("distinct_student_outputs"),
                item.get("distinct_teacher_outputs"),
                _number(item.get("dominant_student_output_share"), 4),
                "是" if item.get("teacher_varies_student_constant") else "否",
                item.get("distinct_source_texts"),
                _number(item.get("cases_per_distinct_source_text"), 2),
            ]
        )
    lines.extend(
        _table(
            [
                "组",
                "n",
                "产出率",
                "结构通过率",
                "Student 不同输出",
                "Teacher 不同输出",
                "最大同输出占比",
                "Teacher 变而 Student 恒定",
                "不同指令文本",
                "每条指令平均用例数",
            ],
            rows,
        )
    )
    lines.append("")
    labeled = groups.get("labeled_cases")
    total = groups.get("case_count")
    lines.append(
        f"> 已标注用例 {labeled}/{total}；"
        "`UNLABELED` 表示冻结输入没有携带分组标签（B2 的 Seen/Variant/Unseen manifest 到位前"
        "这是正常状态）。分组标签由 B2 定义，B3 只做计数与归因。"
    )
    collapsed = groups.get("template_collapse_groups") or []
    if collapsed:
        lines.append("")
        lines.append(
            "> **模板化信号**：以下组内 Teacher 输出有差异、Student 输出却完全一致——"
            "该组不能支撑泛化结论，需按文档 §11 归因："
            + "、".join(f"`{item}`" for item in collapsed)
        )
    collapsed_text = groups.get("instruction_text_collapsed_groups") or []
    if collapsed_text:
        lines.append("")
        lines.append(
            "> **指令文本重复**：以下组内所有用例的 `source_text` 相同，"
            "行为对比只能说明记忆/查表，不能说明泛化："
            + "、".join(f"`{item}`" for item in collapsed_text)
        )
    reused_text = groups.get("instruction_text_reused_groups") or []
    if reused_text:
        lines.append("")
        lines.append(
            "> **指令文本复用**：以下组内平均每条指令被 ≥2 个用例复用，"
            "该组的行为/目标匹配率不能当作独立指令上的泛化指标："
            + "、".join(f"`{item}`" for item in reused_text)
        )
    unrecognized = groups.get("unrecognized_group_labels") or []
    if unrecognized:
        lines.append("")
        lines.append(
            "> 未识别的分组标签（B3 不解释，原样保留）："
            + "、".join(f"`{item}`" for item in unrecognized)
        )
    return lines


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
    scope: Mapping[str, Any] | None = None,
    board_runtime: Mapping[str, Any] | None = None,
    rounds_measured: int | None = None,
    utilization_policy: Mapping[str, Any] | None = None,
) -> str:
    # The scope comes from `claim_scope`, never from the file name or a flag.  A
    # caller that already derived it passes the same mapping in, so the report
    # and the manifest can never disagree about how far the numbers may be
    # quoted.
    if scope is None:
        scope = claim_scope(
            device_class=str(hardware_env.get("device_class", "X86_WORKSTATION")),
            identity=identity,
            artifact=hardware_env.get("model_artifact"),
            runtime={"name": None, "capabilities": capabilities},
            hardware_env=hardware_env,
            telemetry=telemetry,
            board_runtime=board_runtime,
            rounds_measured=rounds_measured,
            stability=stability_summary,
        )
    lines: list[str] = []
    lines.append(f"# B3 HIL / J6P 实测报告 — `{run_id}`")
    lines.append("")
    lines.append(f"- 生成时间（UTC）：`{datetime.now(timezone.utc).isoformat()}`")
    lines.append(f"- 可信范围：`{scope['scope']}`")
    lines.append(f"- 证据层级：`{scope.get('evidence_level')}`")
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
    if utilization_policy:
        lines.append("")
        status = utilization_policy.get("status")
        lines.append(f"公式接入状态：`{status}`")
        lines.append("")
        lines.append(f"> {utilization_policy.get('detail', '')}")
        policy = utilization_policy.get("policy")
        if isinstance(policy, Mapping):
            lines.append("")
            lines.extend(
                _table(
                    ["策略字段", "值"],
                    [
                        ["policy_id", policy.get("policy_id")],
                        ["signer", policy.get("signer")],
                        ["sampling_window", policy.get("sampling_window")],
                        ["probe_scope", policy.get("probe_scope")],
                        ["exclusive_use", policy.get("exclusive_use")],
                        ["policy_sha256", policy.get("policy_sha256")],
                    ],
                )
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
        gate_failed = replay_summary.get("gate_failed_checks") or []
        if gate_failed:
            lines.append("")
            lines.append("> 未满足的 Gate 核验项：" + "、".join(f"`{item}`" for item in gate_failed))
        lines.extend(_group_lines(replay_summary.get("groups")))
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
                    ["漂移来源", stability_summary.get("memory_drift_source")],
                    ["recovery probe 失败数", (stability_summary.get("recovery_probe") or {}).get("errors")],
                    # The four pass criteria are duration, failures, recovery and
                    # telemetry — none of them is a drift threshold, so the two
                    # rows are kept apart instead of one "结论" that a reader
                    # could mistake for "drift is acceptable".
                    [
                        "长稳判据（时长/失败/恢复/遥测）",
                        "通过" if stability_summary.get("success") else "未通过",
                    ],
                    [
                        "漂移判定",
                        (
                            "阈值未冻结（B2/A4 定义），仅报告数字"
                            if stability_summary.get("memory_drift_kib") is not None
                            else "无漂移数据"
                        ),
                    ],
                ],
            )
        )
        lines.append("")
        lines.append("判定条件：" + "；".join(stability_summary.get("criteria", [])))
        if stability_summary.get("drift_note"):
            lines.append("")
            lines.append(f"> 漂移口径：{stability_summary.get('drift_note')}")
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
    lines.append(
        "范围由 `claim_scope` 依据本次运行的证据逐项核验得出，"
        "任何单项证据缺失都只会降低范围，不会提高范围。核验明细："
    )
    lines.append("")
    lines.extend(
        _table(
            ["核验项", "结果", "依据"],
            [
                [item.get("name"), "通过" if item.get("passed") else "未满足", item.get("detail")]
                for item in scope.get("checks", ())
            ],
        )
    )
    lines.append("")
    if scope.get("failed_checks"):
        lines.append(
            "未满足的核验项："
            + "、".join(f"`{item}`" for item in scope["failed_checks"])
            + "。未满足项决定当前只能给出下面的允许结论。"
        )
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
    "REPORT_FILENAME_J6P_BRINGUP",
    "REPORT_FILENAME_J6P_UNVERIFIED",
    "REPORT_FILENAME_X86",
    "SCOPE_FILENAMES",
]
