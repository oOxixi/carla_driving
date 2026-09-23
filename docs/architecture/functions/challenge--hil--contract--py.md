# contract：功能记录

上级模块：[模块说明](../modules/challenge-hil.md) · 实现：[challenge/hil/contract.py](../../../challenge/hil/contract.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [Adapter能力、时钟域与测量范围](hil-trace-semantics.md)

## 功能职责与范围

Executable form of the A4 runtime contract.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_check`

源码位置：[challenge/hil/contract.py 第 22 行](../../../challenge/hil/contract.py#L22)。类型：`FunctionDef`。

```python
_check(name: str, status: str, detail: str) -> dict[str, str]
```

`_check` 更新trace/collector状态或派生运行辅助值；阶段顺序、重复mark、能力声明和错误传播受源码条件约束，不能仅凭名称推断。

### `check_runtime_contract`

源码位置：[challenge/hil/contract.py 第 26 行](../../../challenge/hil/contract.py#L26)。类型：`FunctionDef`。

```python
check_runtime_contract(runtime: PlannerRuntime, requests: Sequence[Mapping[str, Any]], *, latency_budget_ms: float=1000.0) -> dict[str, Any]
```

`check_runtime_contract` 检查runtime合同、artifact、输出一致性、结构或身份完整性；结果只覆盖声明能力，model-only与full-chain、宿主与板端证据不得混写。

## 内部调用与异常路径

- `check_runtime_contract` 调用：`'; '.join`, `ValueError`, `_check`, `checks.append`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `enumerate`, `errors.append`, `forbidden.extend`, `isinstance`, `len`, `list`, `missing_keys.extend`, `plans.append`, `runtime.capabilities.to_dict`, `runtime.identity.missing`, `runtime.infer`, `set`, `sorted`, `structural.extend`, `structural_checks`, `trace.durations_ms`, `trace.durations_ms().get`, `traces.append`, `type`, `unknown_stages.extend`, `zip`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `check_runtime_contract`，第 34 行：`ValueError('contract check needs at least one request')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [challenge/hil/replay.py](../../../challenge/hil/replay.py)
- [challenge/hil/runtime_adapter.py](../../../challenge/hil/runtime_adapter.py)
- [challenge/hil/stages.py](../../../challenge/hil/stages.py)

静态 import 消费者（含测试）：

- [challenge/hil/cli.py](../../../challenge/hil/cli.py)
- [challenge/hil/tests/test_contract.py](../../../challenge/hil/tests/test_contract.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-hil.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/hil/contract.py`

来源 SHA256：`0b993acf127ea6c772ef0b71003e6022645374cc49ef1ff95fe133083c62d4ec`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `check_runtime_contract` / 34 | `not requests` | `raise ValueError('contract check needs at least one request')` |
