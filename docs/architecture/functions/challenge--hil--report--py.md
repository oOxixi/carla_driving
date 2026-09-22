# report：功能记录

上级模块：[模块说明](../modules/challenge-hil.md) · 实现：[challenge/hil/report.py](../../../challenge/hil/report.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [Adapter能力、时钟域与测量范围](hil-trace-semantics.md)

## 功能职责与范围

Build the Markdown test report and guard the claim scope.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `report_filename`

源码位置：[challenge/hil/report.py 第 51 行](../../../challenge/hil/report.py#L51)。类型：`FunctionDef`。

```python
report_filename(device_class: str) -> str
```

Name the report after the environment it actually measured.

The challenge deliverable is named ``j6p_test_report.md``; an X86
pre-validation run must not produce a file with that name, or a reader will
mistake it for board evidence.

### `claim_scope`

源码位置：[challenge/hil/report.py 第 61 行](../../../challenge/hil/report.py#L61)。类型：`FunctionDef`。

```python
claim_scope(*, device_class: str, power_measured: bool, bpu_measured: bool) -> dict[str, Any]
```

`claim_scope` 构造或汇总HIL身份、阶段、统计、环境或报告字段；计算口径依赖有效样本和单一时钟域，UNKNOWN与缺测需原样保留。

### `_table`

源码位置：[challenge/hil/report.py 第 101 行](../../../challenge/hil/report.py#L101)。类型：`FunctionDef`。

```python
_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> list[str]
```

`_table` 构造或汇总HIL身份、阶段、统计、环境或报告字段；计算口径依赖有效样本和单一时钟域，UNKNOWN与缺测需原样保留。

### `_number`

源码位置：[challenge/hil/report.py 第 108 行](../../../challenge/hil/report.py#L108)。类型：`FunctionDef`。

```python
_number(value: Any, digits: int=3) -> str
```

`_number` 构造或汇总HIL身份、阶段、统计、环境或报告字段；计算口径依赖有效样本和单一时钟域，UNKNOWN与缺测需原样保留。

### `_latency_table`

源码位置：[challenge/hil/report.py 第 114 行](../../../challenge/hil/report.py#L114)。类型：`FunctionDef`。

```python
_latency_table(metrics: Mapping[str, Any]) -> list[str]
```

`_latency_table` 构造或汇总HIL身份、阶段、统计、环境或报告字段；计算口径依赖有效样本和单一时钟域，UNKNOWN与缺测需原样保留。

### `build_report`

源码位置：[challenge/hil/report.py 第 136 行](../../../challenge/hil/report.py#L136)。类型：`FunctionDef`。

```python
build_report(*, run_id: str, identity: CandidateIdentity, capabilities: Mapping[str, Any], hardware_env: Mapping[str, Any], latency_report: Mapping[str, Any], replay_summary: Mapping[str, Any] | None, telemetry: Mapping[str, Any] | None, failure_summary: Mapping[str, Any] | None, run_summary: Mapping[str, Any] | None, blocked_on: Sequence[str], extra_notes: Sequence[str]=(), stability_summary: Mapping[str, Any] | None=None) -> str
```

`build_report` 构造或汇总HIL身份、阶段、统计、环境或报告字段；计算口径依赖有效样本和单一时钟域，UNKNOWN与缺测需原样保留。

## 内部调用与异常路径

- `claim_scope` 调用：`allowed.append`, `forbidden.append`.
- `_table` 调用：`' | '.join`, `len`, `lines.append`, `str`.
- `_number` 调用：`float`, `isinstance`.
- `_latency_table` 调用：`SEGMENT_LABELS.get`, `_number`, `_table`, `metrics.get`, `rows.append`, `stats.get`.
- `build_report` 调用：`', '.join`, `'\n'.join`, `'；'.join`, `(hardware_env.get('clock') or {}).get`, `(hardware_env.get('runtime_libraries') or {}).get`, `(stability_summary.get('recovery_probe') or {}).get`, `(telemetry or {}).get`, `(telemetry or {}).get('power', {}).get`, `(telemetry or {}).get('utilization', {}).get`, `_latency_table`, `_number`, `_table`, `bool`, `capabilities.get`, `claim_scope`, `clock.get`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `e2e.get`, `failure_summary.get`, `hardware_env.get`, `hardware_env.get('accelerator', {}).get`, `hardware_env.get('host', {}).get`, `identity.missing`, `int`, `isinstance`, `item.get`, `latency.get`, `latency_report.get`, `lines.append`, `lines.extend`, `memory.get`, `metrics.get`, `model.get`, `power.get`, `replay_summary.get`, `rounds[round_id].get`, `rows.append`, `run_summary.get`, `sorted`, `stability_summary.get`, `str`, `utilization.get`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [challenge/hil/identity.py](../../../challenge/hil/identity.py)
- [challenge/hil/stages.py](../../../challenge/hil/stages.py)

静态 import 消费者（含测试）：

- [challenge/hil/cli.py](../../../challenge/hil/cli.py)
- [challenge/hil/tests/test_report.py](../../../challenge/hil/tests/test_report.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-hil.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/hil/report.py`

来源 SHA256：`5917e2ba0a7c16f3b0f1c82dd651b89de0769bf837881fc37c6b8e600a86f4b7`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。

### challenge/hil/report.py 数值检查调用

这里保留校验函数的minimum/positive等参数原文；实际可达性由调用分支决定，函数本体异常仍需看对应helper。

| 行 | 校验调用 |
|---|---|
| 124 | `_number(stats.get('mean'))` |
| 125 | `_number(stats.get('p50'))` |
| 126 | `_number(stats.get('p95'))` |
| 127 | `_number(stats.get('p99'))` |
| 128 | `_number(stats.get('max'))` |
| 271 | `_number(e2e.get('p95'))` |
| 272 | `_number(e2e.get('max'))` |
| 273 | `_number(model.get('p95'))` |
| 292 | `_number(memory.get('rss_kib_max'), 1)` |
| 293 | `_number(memory.get('peak_rss_mib_max'), 2)` |
| 333 | `_number(utilization.get('cpu_percent_max'), 1)` |
| 334 | `_number(utilization.get('bpu_percent_mean'), 1)` |
| 311 | `_number(power.get('power_w_mean'))` |
| 312 | `_number(power.get('power_w_max'))` |
| 354 | `_number(replay_summary.get('ready_rate'), 4)` |
| 355 | `_number(replay_summary.get('rgb_resolution_rate'), 4)` |
| 356 | `_number(replay_summary.get('structural_pass_rate'), 4)` |
| 389 | `_number(stability_summary.get('requested_duration_s'), 1)` |
| 390 | `_number(stability_summary.get('observed_duration_s'), 1)` |
| 393 | `_number(stability_summary.get('success_rate'), 5)` |
| 394 | `_number(latency.get('first_window_p95'))` |
| 395 | `_number(latency.get('last_window_p95'))` |
| 396 | `_number(latency.get('overall_p95'))` |
| 397 | `_number(stability_summary.get('memory_drift_kib'), 1)` |
| 398 | `_number(stability_summary.get('memory_drift_ratio'), 5)` |
| 421 | `_number(run_summary.get('duration_s'), 2)` |
