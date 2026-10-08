"""Summarize existing CPU telemetry and keep BPU estimates separately labelled."""
from __future__ import annotations
import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parents[1]
B3 = PACKAGE / '05_B3性能与评测'

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def percentile(values, q):
    values = sorted(values)
    n = (len(values) - 1) * q
    lo, hi = int(n), math.ceil(n)
    return values[lo] + (values[hi] - values[lo]) * (n - lo)

def main():
    rows, sources = [], {}
    for raw_path in sorted((B3 / '02_X86性能报告与原始日志').rglob('utilization_raw.csv')):
        env_path = raw_path.parent / 'hardware_env.json'
        env = json.loads(env_path.read_text(encoding='utf-8-sig')) if env_path.exists() else {}
        cores = env.get('host', {}).get('cpu_cores')
        cores = int(cores) if isinstance(cores, (int, float)) and cores > 0 else None
        rel = raw_path.relative_to(PACKAGE).as_posix()
        sources[rel] = digest(raw_path)
        if env_path.exists():
            sources[env_path.relative_to(PACKAGE).as_posix()] = digest(env_path)
        grouped = defaultdict(list)
        with raw_path.open(encoding='utf-8-sig', newline='') as stream:
            for index, row in enumerate(csv.DictReader(stream), 2):
                grouped[(row.get('run_id', ''), row.get('round', ''))].append((index, row))
        for (run_id, round_id), samples in sorted(grouped.items()):
            values, anomalies, empty = [], [], 0
            for index, sample in samples:
                try:
                    value = float(sample['cpu_percent'])
                    if not math.isfinite(value) or value < 0 or (cores and value > 100 * cores + 1):
                        anomalies.append({'csv_line': index, 'cpu_percent': sample['cpu_percent'], 'reason': 'outside_physical_range'})
                        continue
                    values.append(value)
                except (KeyError, ValueError, TypeError):
                    empty += 1
            if not values:
                continue
            row = {
                'run_id': run_id, 'round': round_id, 'source_csv': rel,
                'environment_source': env_path.relative_to(PACKAGE).as_posix() if env_path.exists() else None,
                'cpu_cores': cores, 'samples_total': len(samples), 'samples_valid': len(values),
                'samples_missing': empty, 'samples_invalid': len(anomalies), 'invalid_samples': anomalies,
                'process_cpu_percent_mean': statistics.fmean(values),
                'process_cpu_percent_p95': percentile(values, 0.95),
                'process_cpu_percent_max': max(values),
                'mean_equivalent_cpu_cores': statistics.fmean(values) / 100,
                'normalized_host_capacity_percent_mean': statistics.fmean(values) / cores if cores else None,
                'normalized_host_capacity_percent_p95': percentile(values, .95) / cores if cores else None,
                'scope': 'planner_process_cpu_time_over_monotonic_wall_window',
                'aggregation': 'arithmetic_mean_of_valid_raw_samples; initialization_zero_retained',
                'bpu_measured': any(s.get('bpu_percent', '').strip() for _, s in samples),
            }
            rows.append(row)
    tool_path = B3 / '03_BPU工具原报告/01_bpu_performance_estimate_v3.json'
    tool = json.loads(tool_path.read_text(encoding='utf-8-sig'))
    sources[tool_path.relative_to(PACKAGE).as_posix()] = digest(tool_path)
    report = {
        'schema_version': '1.0', 'operation': 'summary_of_existing_telemetry_only',
        'new_inference_or_hardware_measurement_performed': False,
        'cpu_results': rows,
        'cpu_definition': 'Per-process CPU seconds / wall seconds * 100; a multi-thread process can exceed 100%. Host-capacity normalization divides by the captured logical-core count.',
        'bpu_analysis': {
            'scope': 'BPU_ESTIMATED', 'placement': tool['placement'],
            'performance_estimate': tool['estimate'],
            'interval_compute_utilization': tool['basis']['interval_compute_utilization'],
            'source': tool_path.relative_to(PACKAGE).as_posix(),
        },
        'official_heterogeneous_utilization': {
            'value': None, 'status': 'NOT_DECLARED_FROM_PROXY_STATISTICS',
            'reason': 'The published rule describes end-to-end CPU/GPU/NPU/DSP use but provides no device aggregation formula. Captured process CPU use, BPU operator placement and simulated BPU compute occupancy are separate quantities.',
            'board_required_for_initial_material_submission': False,
            'real_bpu_counter_measured': False,
        },
        'raw_evidence_sha256': sources,
    }
    (HERE / 'utilization_summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    fields = ['run_id', 'round', 'cpu_cores', 'samples_valid', 'process_cpu_percent_mean', 'mean_equivalent_cpu_cores', 'normalized_host_capacity_percent_mean', 'normalized_host_capacity_percent_p95', 'samples_invalid', 'source_csv']
    with (HERE / 'cpu_utilization_summary.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader(); writer.writerows(rows)
    lines = [
        '# X86 利用率实测汇总与 BPU 口径说明', '',
        '本文件直接统计 B3 已有官方 X86 环境的 CPU 原始记录，未运行新模型或新增板端测量。原始 CSV、环境 JSON 与文件哈希一并保留，结果可用本目录脚本复算。', '',
        '| 运行与轮次 | 逻辑核数 | 有效采样 | 平均占用核数 | 占整机 CPU 容量均值 |',
        '| --- | --- | --- | --- | --- |',
    ]
    for r in rows:
        normalized = f"{r['normalized_host_capacity_percent_mean']:.3f}%" if r['cpu_cores'] else '环境未记录核数，不归一化'
        lines.append(f"| {r['run_id']} / {r['round']} | {r['cpu_cores'] or '未记录'} | {r['samples_valid']} | {r['mean_equivalent_cpu_cores']:.3f} | {normalized} |")
    lines.extend([
        '', 'CPU 数值是规划进程用户态与内核态 CPU 时间相对于单调时钟窗口的比例。多线程原始读数可超过 100%；例如在 20 个逻辑核的环境中 1000% 约等于占用 10 核、整机 CPU 容量的 50%。初始化的 0 值保留，缺失值和超过已知物理上限的值单列，不修改原始记录。采样均值不是官方定义的多设备合成评分值。', '',
        'BPU 原件位于 ../03_BPU工具原报告。59/59 节点落 BPU 是算子放置结果；0.615 ms 是工具预估；区间计算单元利用率均值 13.8%、峰值 24.3% 也是工具模拟的单次推理内部占用，均不改称官方端到端异构算力利用率。', '',
        '官方初审以 X86 Docker 和配套工具链为基准，实板/HIL 数据为具备条件时的补充。因此没有开发板仍可提交本汇总和工具原件。真实 BPU/NPU 计数器没有采集，明确为 NOT_MEASURED；多设备聚合公式与正式计分值须以组委会统一口径及官方平台测量为准，不要求参赛者先购买开发板。', '',
        '复算命令：`python summarize_utilization.py`。本目录输出 utilization_summary.json 和 cpu_utilization_summary.csv；原始文件路径与 SHA256 在 JSON 中逐项列出。',
    ])
    (HERE / '利用率实测汇总与官方口径说明.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({'runs': len(rows), 'new_measurement': False, 'summary': str(HERE / 'utilization_summary.json')}, ensure_ascii=False))

if __name__ == '__main__':
    main()
