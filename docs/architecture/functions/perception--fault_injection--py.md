# fault_injection：功能记录

上级模块：[模块说明](../modules/vehicle-perception.md) · 实现：[perception/fault_injection.py](../../../perception/fault_injection.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [同帧感知、目标身份与来源](perception-authority.md)

## 功能职责与范围

Deterministic sensor and observation fault injection with explicit invalidity.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `inject_sensor_fault`

源码位置：[perception/fault_injection.py 第 24 行](../../../perception/fault_injection.py#L24)。类型：`FunctionDef`。

```python
inject_sensor_fault(sample: SensorSample, fault: str, *, latency_ms: float=250.0, noise_std_m: float=1.0, seed: int=0) -> SensorSample
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `inject_observation_fault`

源码位置：[perception/fault_injection.py 第 52 行](../../../perception/fault_injection.py#L52)。类型：`FunctionDef`。

```python
inject_observation_fault(observations: Iterable[Observation], fault: str, *, seed: int=0) -> tuple[Observation, ...]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[perception/fault_injection.py 第 71 行](../../../perception/fault_injection.py#L71)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `inject_sensor_fault` 调用：`ValueError`, `int`, `isinstance`, `np.asarray`, `np.random.default_rng`, `np.zeros_like`, `replace`, `rng.normal`, `sample.invalidated`.
- `inject_observation_fault` 调用：`Observation`, `ValueError`, `list`, `random.Random`, `random.Random(seed).shuffle`, `tuple`, `values.append`.
- `main` 调用：`SensorRecorder`, `SensorReplayer`, `argparse.ArgumentParser`, `args.output.with_suffix`, `inject_sensor_fault`, `int`, `json.dumps`, `parser.add_argument`, `parser.parse_args`, `print`, `recorder.record`, `report_path.write_text`, `sorted`, `str`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `inject_observation_fault`，第 59 行：`ValueError(f'unsupported observation fault: {fault}')`。
- `inject_sensor_fault`，第 33 行：`ValueError(f'unsupported sensor fault: {fault}')`。
- `inject_sensor_fault`，第 43 行：`ValueError('latency_ms must be non-negative')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 73 行：`parser.add_argument('--input', required=True, type=Path)`。
- 第 74 行：`parser.add_argument('--output', required=True, type=Path)`。
- 第 75 行：`parser.add_argument('--fault', required=True, choices=sorted(SENSOR_FAULTS))`。
- 第 76 行：`parser.add_argument('--seed', type=int, default=0)`。
- 第 77 行：`parser.add_argument('--latency-ms', type=float, default=250.0)`。
- 第 78 行：`parser.add_argument('--noise-std-m', type=float, default=1.0)`。

## 上下游与关联验证

静态导入的项目内实现：

- [perception/fusion_tracker.py](../../../perception/fusion_tracker.py)
- [perception/sensor_adapter.py](../../../perception/sensor_adapter.py)

静态 import 消费者（含测试）：

- [integration/tests/test_role_c_perception.py](../../../integration/tests/test_role_c_perception.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-perception.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `perception/fault_injection.py`

来源 SHA256：`7293778bd4de00320795674f0b0fbd8c300f18820ff5a6668e2e474555ef3248`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 73 | `'--input'` | `required=True; type=Path` |
| 74 | `'--output'` | `required=True; type=Path` |
| 75 | `'--fault'` | `required=True; choices=sorted(SENSOR_FAULTS)` |
| 76 | `'--seed'` | `type=int; default=0` |
| 77 | `'--latency-ms'` | `type=float; default=250.0` |
| 78 | `'--noise-std-m'` | `type=float; default=1.0` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `inject_sensor_fault` / 33 | `fault not in SENSOR_FAULTS` | `raise ValueError(f'unsupported sensor fault: {fault}')` |
| `inject_sensor_fault` / 43 | `fault == 'sensor_latency' AND latency_ms < 0` | `raise ValueError('latency_ms must be non-negative')` |
| `inject_observation_fault` / 59 | `fault not in OBSERVATION_FAULTS` | `raise ValueError(f'unsupported observation fault: {fault}')` |
