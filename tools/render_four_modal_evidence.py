"""Render a concise Markdown evidence report from verified JSON artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _pct(value: float | None) -> str:
    return "N/A" if value is None else f"{value * 100:.2f}%"


def _ms(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("dataset_validation", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    dataset = json.loads(
        args.dataset_validation.read_text(encoding="utf-8")
    )
    latency = report["latency"]
    category_rows = "\n".join(
        "| {name} | {count} | {joint} | {target} | {safety} |".format(
            name=name,
            count=values["count"],
            joint=_pct(values["answerable_joint_accuracy"]),
            target=_pct(
                values["answerable_target_association_accuracy"]
            ),
            safety=_pct(
                values["safety_fault_fail_closed_accuracy"]
            ),
        )
        for name, values in report["categories"].items()
    )
    text = f"""# 四模态真实模型全链路证据（2026-07-28）

## 结论

- 模型保持不变：SenseVoice/FunASR + Qwen2.5-VL-7B-Instruct。
- 实测链路：TTS 音频 → 真实 SenseVoice/NLU → RGB + 原始 CARLA LiDAR 摘要 + 车辆状态 → 真实 Qwen → 严格边界/目标绑定 → D 安全仲裁 → 最终控制。
- 样本数：{report["case_count"]}；可回答样本 {report["answerable_case_count"]}；漏检安全故障 {report["safety_fault_case_count"]}。
- ASR 精确匹配率：{_pct(report["asr_exact_accuracy"])}。
- 高层动作准确率：{_pct(report["answerable_semantic_accuracy"])}。
- 系统目标关联准确率：{_pct(report["answerable_target_association_accuracy"])}。
- 原始 Qwen 目标关联准确率：{_pct(report["raw_qwen_target_association_accuracy"])}。
- 确定性唯一目标纠正次数：{report["grounding_correction_count"]}。
- 漏检 fail-closed 准确率：{_pct(report["safety_fault_fail_closed_accuracy"])}。
- 四模态全链路契约准确率：{_pct(report["full_chain_contract_accuracy"])}。
- 内部门槛：{"PASS" if report["passes_thresholds"] else "FAIL"}。

## 延迟

| 阶段 | mean ms | P95 ms | P99 ms | max ms |
|---|---:|---:|---:|---:|
| SenseVoice/NLU | {_ms(latency["voice"]["mean_ms"])} | {_ms(latency["voice"]["p95_ms"])} | {_ms(latency["voice"]["p99_ms"])} | {_ms(latency["voice"]["max_ms"])} |
| Qwen2.5-VL-7B | {_ms(latency["qwen"]["mean_ms"])} | {_ms(latency["qwen"]["p95_ms"])} | {_ms(latency["qwen"]["p99_ms"])} | {_ms(latency["qwen"]["max_ms"])} |
| Qwen 后安全/控制 | {_ms(latency["post_qwen_control"]["mean_ms"])} | {_ms(latency["post_qwen_control"]["p95_ms"])} | {_ms(latency["post_qwen_control"]["p99_ms"])} | {_ms(latency["post_qwen_control"]["max_ms"])} |
| 音频到最终控制 | {_ms(latency["audio_to_final_control"]["mean_ms"])} | {_ms(latency["audio_to_final_control"]["p95_ms"])} | {_ms(latency["audio_to_final_control"]["p99_ms"])} | {_ms(latency["audio_to_final_control"]["max_ms"])} |

## 鲁棒性分类

| 分类 | 数量 | 可回答联合准确率 | 系统目标关联 | 漏检安全准确率 |
|---|---:|---:|---:|---:|
{category_rows}

## 数据集完整性

- 四模态：语音、RGB、LiDAR、车辆状态。
- 数据：{dataset["case_count"]} 条；RGB {dataset["unique_rgb_files"]} 张；LiDAR {dataset["unique_lidar_files"]} 份；音频 {dataset["unique_audio_files"]} 份。
- 覆盖：密集目标、物理/合成遮挡、低/高曝光、运动模糊、检测误检、漏检、框偏移。
- 唯一文件哈希校验：{dataset["hashed_unique_file_count"]}；错误 {dataset["error_count"]}。
- 划分：{json.dumps(dataset["split_counts"], ensure_ascii=False)}；场景泄漏：{len(dataset["scene_split_leakage"])}。

## 计分口径

可回答样本计算动作、确认和目标关联；故意移除明确目标的漏检样本不进入可回答语义分母，只在 fail-closed 安全分母中计分。原始 Qwen 目标结果与确定性目标绑定分别报告，不把安全纠正冒充为原始模型准确率。

## 边界

- 音频是合成 TTS 经真实 ASR 推理，不是经声级计校准的真人/方言 50 dBA 证据。
- 视觉扰动由真实 CARLA RGB 生成并明确标注；LiDAR 为同步原始 CARLA 点云。
- 每条记录到达最终控制仲裁，但不是每条都单独驱动 CARLA actor；物理闭环由 S01、D03、D08 正式场景矩阵另行证明。
"""
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
