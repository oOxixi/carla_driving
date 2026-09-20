# benchmark：功能记录

上级模块：[模块说明](../modules/vehicle-safety.md) · 实现：[car_control_D/benchmark.py](../../../car_control_D/benchmark.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [C/D分工与实时仲裁](longitudinal-safety-contract.md)
- [安全覆盖的生命周期影响](control-frame.md)

## 功能职责与范围

Deterministic latency benchmark for D and the integrated control step.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_percentile_ms`

源码位置：[car_control_D/benchmark.py 第 19 行](../../../car_control_D/benchmark.py#L19)。类型：`FunctionDef`。

```python
_percentile_ms(samples_ns: list[int], percentile: float) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_summary`

源码位置：[car_control_D/benchmark.py 第 25 行](../../../car_control_D/benchmark.py#L25)。类型：`FunctionDef`。

```python
_summary(samples_ns: list[int]) -> dict[str, float | int]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_measure`

源码位置：[car_control_D/benchmark.py 第 36 行](../../../car_control_D/benchmark.py#L36)。类型：`FunctionDef`。

```python
_measure(operation: Callable[[int], object], *, iterations: int, warmup: int) -> list[int]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `run_control_safety_benchmark`

源码位置：[car_control_D/benchmark.py 第 47 行](../../../car_control_D/benchmark.py#L47)。类型：`FunctionDef`。

```python
run_control_safety_benchmark(*, iterations: int=10000, warmup: int=1000, threshold_ms: float=5.0) -> dict[str, object]
```

Benchmark CARLA-independent hot paths and return machine-readable evidence.

### `run_control_safety_benchmark.arbitrate`

源码位置：[car_control_D/benchmark.py 第 90 行](../../../car_control_D/benchmark.py#L90)。类型：`FunctionDef`。

```python
run_control_safety_benchmark.arbitrate(index: int) -> object
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `run_control_safety_benchmark.integrated_step`

源码位置：[car_control_D/benchmark.py 第 97 行](../../../car_control_D/benchmark.py#L97)。类型：`FunctionDef`。

```python
run_control_safety_benchmark.integrated_step(index: int) -> object
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_percentile_ms` 调用：`len`, `math.ceil`, `max`, `sorted`.
- `_summary` 调用：`_percentile_ms`, `fmean`, `len`, `max`.
- `_measure` 调用：`operation`, `perf_counter_ns`, `range`, `samples.append`.
- `run_control_safety_benchmark` 调用：`ControlRuntime`, `PerceptionFrame`, `PurePursuitController`, `RouteReference`, `RuntimeVehicleState`, `SafetySupervisor`, `ValueError`, `_measure`, `_summary`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `float`, `len`, `math.isfinite`, `min`, `platform.platform`, `platform.python_version`, `runtime.step`, `supervisor.arbitrate`, `type`.
- `arbitrate` 调用：`len`, `supervisor.arbitrate`.
- `integrated_step` 调用：`PerceptionFrame`, `RuntimeVehicleState`, `float`, `min`, `runtime.step`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `run_control_safety_benchmark`，第 55 行：`ValueError('iterations must be a positive integer')`。
- `run_control_safety_benchmark`，第 57 行：`ValueError('warmup must be a non-negative integer')`。
- `run_control_safety_benchmark`，第 59 行：`ValueError('threshold_ms must be a positive finite number')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_A/__init__.py](../../../car_control_A/__init__.py)
- [car_control_A/routing.py](../../../car_control_A/routing.py)
- [car_control_B/pure_pursuit.py](../../../car_control_B/pure_pursuit.py)
- [car_control_D/safety_supervisor.py](../../../car_control_D/safety_supervisor.py)
- [integration/__init__.py](../../../integration/__init__.py)

静态 import 消费者（含测试）：

- [car_control_D/tests/test_benchmark.py](../../../car_control_D/tests/test_benchmark.py)
- [tools/run_control_safety_benchmark.py](../../../tools/run_control_safety_benchmark.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-safety.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_D/benchmark.py`

来源 SHA256：`9274c0aa8232f1d076cd9f1cc535568cd01f328a9ce298dd3d3b1c92f196e1aa`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `run_control_safety_benchmark` / 55 | `type(iterations) is not int or iterations <= 0` | `raise ValueError('iterations must be a positive integer')` |
| `run_control_safety_benchmark` / 57 | `type(warmup) is not int or warmup < 0` | `raise ValueError('warmup must be a non-negative integer')` |
| `run_control_safety_benchmark` / 59 | `type(threshold_ms) not in (int, float) or not math.isfinite(float(threshold_ms)) or threshold_ms <= 0` | `raise ValueError('threshold_ms must be a positive finite number')` |
