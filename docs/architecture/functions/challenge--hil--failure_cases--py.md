# failure_cases：功能记录

上级模块：[模块说明](../modules/challenge-hil.md) · 实现：[challenge/hil/failure_cases.py](../../../challenge/hil/failure_cases.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [Adapter能力、时钟域与测量范围](hil-trace-semantics.md)

## 功能职责与范围

Deterministic abnormal-input suite.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `FailureCase.case_id: str`；默认：`未在声明处设置`。
- `FailureCase.description: str`；默认：`未在声明处设置`。
- `FailureCase.expectation: str`；默认：`未在声明处设置`。
- `FailureCase.expectation_code: str`；默认：`未在声明处设置`。
- `FailureCase.request: dict[str, Any]`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

### `FailureCase`

源码位置：[challenge/hil/failure_cases.py 第 22 行](../../../challenge/hil/failure_cases.py#L22)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_jsonable`

源码位置：[challenge/hil/failure_cases.py 第 30 行](../../../challenge/hil/failure_cases.py#L30)。类型：`FunctionDef`。

```python
_jsonable(value: Any) -> Any
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `build_failure_cases`

源码位置：[challenge/hil/failure_cases.py 第 44 行](../../../challenge/hil/failure_cases.py#L44)。类型：`FunctionDef`。

```python
build_failure_cases(base_request: Mapping[str, Any]) -> list[FailureCase]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `run_failure_cases`

源码位置：[challenge/hil/failure_cases.py 第 179 行](../../../challenge/hil/failure_cases.py#L179)。类型：`FunctionDef`。

```python
run_failure_cases(runtime: PlannerRuntime, cases: Sequence[FailureCase], *, run_id: str, output_dir: str | Path, latency_budget_ms: float=1000.0) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_jsonable` 调用：`_jsonable`, `isinstance`, `math.isinf`, `math.isnan`, `str`, `value.items`.
- `build_failure_cases` 调用：`FailureCase`, `base.get`, `cases.append`, `copy.deepcopy`, `dict`, `float`, `range`, `request.get`, `request.pop`, `request.setdefault`.
- `run_failure_cases` 调用：`Path`, `_jsonable`, `bool`, `durations.get`, `isinstance`, `len`, `list`, `output.mkdir`, `plan.get`, `records.append`, `runtime.infer`, `step.get`, `str`, `structural_checks`, `sum`, `trace.durations_ms`, `trace.missing_stages`, `type`, `verdicts.get`, `write_json`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [challenge/hil/replay.py](../../../challenge/hil/replay.py)
- [challenge/hil/run_io.py](../../../challenge/hil/run_io.py)
- [challenge/hil/runtime_adapter.py](../../../challenge/hil/runtime_adapter.py)

静态 import 消费者（含测试）：

- [challenge/hil/cli.py](../../../challenge/hil/cli.py)
- [challenge/hil/tests/test_replay_and_failures.py](../../../challenge/hil/tests/test_replay_and_failures.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-hil.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/hil/failure_cases.py`

来源 SHA256：`1f4020ec462b5fa060f81f178ceb82be04993449febff3c64134aefe7040bb59`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `FailureCase.case_id` | `str` | `无声明默认；构造/赋值方提供` |
| `FailureCase.description` | `str` | `无声明默认；构造/赋值方提供` |
| `FailureCase.expectation` | `str` | `无声明默认；构造/赋值方提供` |
| `FailureCase.expectation_code` | `str` | `无声明默认；构造/赋值方提供` |
| `FailureCase.request` | `dict[str, Any]` | `无声明默认；构造/赋值方提供` |
