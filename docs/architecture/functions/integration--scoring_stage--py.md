# scoring_stage：功能记录

上级模块：[模块说明](../modules/vehicle-scenarios.md) · 实现：[integration/scoring_stage.py](../../../integration/scoring_stage.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [场景触发、车辆行为与验收分离](scenario-evidence-contract.md)

## 功能职责与范围

Read-only construction of scoring context from completed runtime evidence.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `build_acceptance_context`

源码位置：[integration/scoring_stage.py 第 9 行](../../../integration/scoring_stage.py#L9)。类型：`FunctionDef`。

```python
build_acceptance_context(spec: ScenarioSpec, *, final_route_end_distance_m: float | None, final_route_remaining_m: float | None, configured_route_deviation_trigger_m: float, spawned_scenario_actor_types: Sequence[str], extension_acceptance: Mapping[str, object] | None, qwen_acceptance: Mapping[str, object] | None, extension_event_count: int=0) -> dict[str, object]
```

Build evaluator inputs without mutating any control-side object.

## 内部调用与异常路径

- `build_acceptance_context` 调用：`any`, `dict`, `extension_acceptance.get`, `extension_evidence.get`, `int`, `isinstance`, `len`, `set`, `sorted`, `str`, `str(item).strip`, `str(item).strip().upper`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [integration/scenario_execution.py](../../../integration/scenario_execution.py)

静态 import 消费者（含测试）：

- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/tests/test_runtime_stages.py](../../../integration/tests/test_runtime_stages.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-scenarios.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `integration/scoring_stage.py`

来源 SHA256：`abf12585e09d9bded5ec2da821116f50c605731c44d8d26b453e79a8550a6f0d`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
