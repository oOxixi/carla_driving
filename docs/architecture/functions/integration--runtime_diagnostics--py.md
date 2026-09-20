# runtime_diagnostics：功能记录

上级模块：[模块说明](../modules/vehicle-entry.md) · 实现：[integration/runtime_diagnostics.py](../../../integration/runtime_diagnostics.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [一帧控制的实际顺序与执行值](control-frame.md)

## 功能职责与范围

Stable first-failure classification for CARLA run triage.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `RuntimeFailureDiagnosis.stage: FailureStage`；默认：`未在声明处设置`。
- `RuntimeFailureDiagnosis.code: str`；默认：`未在声明处设置`。
- `RuntimeFailureDiagnosis.exception_type: str`；默认：`未在声明处设置`。
- `RuntimeFailureDiagnosis.detail: str`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

<a id="fn-failurestage"></a>

### `FailureStage`

源码位置：[integration/runtime_diagnostics.py 第 8 行](../../../integration/runtime_diagnostics.py#L8)。类型：`ClassDef`。

字符串枚举：SETUP、ROUTE、ACTOR_SPAWN、PERCEPTION、QWEN、PLAN、CONTROL、SCORING、UNKNOWN，用于首故障分类输出，不是运行状态机。

<a id="fn-runtimefailurediagnosis"></a>

### `RuntimeFailureDiagnosis`

源码位置：[integration/runtime_diagnostics.py 第 21 行](../../../integration/runtime_diagnostics.py#L21)。类型：`ClassDef`。

冻结记录stage、code、exception_type、detail；保存异常分类及原始消息，不包含run_id或时间，外层日志必须关联运行身份。

<a id="fn-runtimefailurediagnosis-to-dict"></a>

### `RuntimeFailureDiagnosis.to_dict`

源码位置：[integration/runtime_diagnostics.py 第 27 行](../../../integration/runtime_diagnostics.py#L27)。类型：`FunctionDef`。

```python
RuntimeFailureDiagnosis.to_dict(self) -> dict[str, str]
```

把stage转为枚举.value，其余字段原样返回四个字符串键，用于runner的runtime_failure_diagnosis JSON；不裁剪原始detail。

<a id="fn-diagnose-runtime-failure"></a>

### `diagnose_runtime_failure`

源码位置：[integration/runtime_diagnostics.py 第 36 行](../../../integration/runtime_diagnostics.py#L36)。类型：`FunctionDef`。

```python
diagnose_runtime_failure(error: BaseException) -> RuntimeFailureDiagnosis
```

对str(error).lower()按ROUTE→ACTOR_SPAWN→PERCEPTION→QWEN→PLAN→CONTROL→SCORING→SETUP顺序做关键词子串匹配，首个命中即返回。无命中为UNKNOWN/UNCLASSIFIED_RUNTIME_FAILURE；多种关键词不会同时报告，因此这是启发式归类，不能替代堆栈/首故障证据。

## 内部调用与异常路径

- `diagnose_runtime_failure` 调用：`RuntimeFailureDiagnosis`, `any`, `message.lower`, `str`, `type`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/tests/test_runtime_diagnostics.py](../../../integration/tests/test_runtime_diagnostics.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-entry.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-integration-runtime-diagnostics-py"></a>

### `integration/runtime_diagnostics.py`

来源 SHA256：`fe7becb72177c0e97d9193da6f70b297bc474a8e57d7f1482850f78574ac7408`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `RuntimeFailureDiagnosis.stage` | `FailureStage` | `无声明默认；构造/赋值方提供` |
| `RuntimeFailureDiagnosis.code` | `str` | `无声明默认；构造/赋值方提供` |
| `RuntimeFailureDiagnosis.exception_type` | `str` | `无声明默认；构造/赋值方提供` |
| `RuntimeFailureDiagnosis.detail` | `str` | `无声明默认；构造/赋值方提供` |
