# planning_stage：功能记录

上级模块：[模块说明](../modules/vehicle-lateral.md) · 实现：[integration/planning_stage.py](../../../integration/planning_stage.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [路线、跟踪控制与完成里程](route-control-progress.md)

## 功能职责与范围

Route-contract preparation stage, independent from CARLA actor mutation.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `PreparedScenarioRoute.reference: RouteReference`；默认：`未在声明处设置`。
- `PreparedScenarioRoute.quality: RouteQuality`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

### `PreparedScenarioRoute`

源码位置：[integration/planning_stage.py 第 15 行](../../../integration/planning_stage.py#L15)。类型：`ClassDef`。

不可变准备结果，成对保存控制用 `RouteReference` 与距离/连续性质量摘要 `RouteQuality`；不包含 actor mutation 或 CARLA 控制状态。

### `prepare_scenario_route`

源码位置：[integration/planning_stage.py 第 20 行](../../../integration/planning_stage.py#L20)。类型：`FunctionDef`。

```python
prepare_scenario_route(spec: ScenarioSpec, route_anchor: Any, target_speed_mps: float, topology_route: RouteReference | None) -> PreparedScenarioRoute
```

优先采用拓扑路线并仅替换目标速度，否则从场景局部 world_route 构造参考线；计算距离合同质量，在 `must_finish_route=true` 且长度不足时拒绝，再验证所有 actor 的路线覆盖，最后返回路线与质量。该阶段不生成或移动 actor。

## 内部调用与异常路径

- `prepare_scenario_route` 调用：`PreparedScenarioRoute`, `RouteReference`, `RuntimeError`, `evaluate_route_quality`, `float`, `replace`, `spec.expected.get`, `spec.world_route`, `validate_actor_route_coverage`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `prepare_scenario_route`，第 43 行：`RuntimeError(f'generated CARLA route does not satisfy the declared distance contract: actual={quality.actual_distance_m:.1f} m required={quality.requested_distance_m:.1f} m')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_A/routing.py](../../../car_control_A/routing.py)
- [integration/route_geometry.py](../../../integration/route_geometry.py)
- [integration/scenario_builder.py](../../../integration/scenario_builder.py)
- [integration/scenario_execution.py](../../../integration/scenario_execution.py)

静态 import 消费者（含测试）：

- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/tests/test_runtime_stages.py](../../../integration/tests/test_runtime_stages.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-lateral.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `integration/planning_stage.py`

来源 SHA256：`d8b4bdb1f4927837b1725ea71b3886714618bb25c19c9647234fbce7279c32f5`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `PreparedScenarioRoute.reference` | `RouteReference` | `无声明默认；构造/赋值方提供` |
| `PreparedScenarioRoute.quality` | `RouteQuality` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `prepare_scenario_route` / 43 | `spec.expected.get('must_finish_route') is True and (not quality.reached_contract)` | `raise RuntimeError(f'generated CARLA route does not satisfy the declared distance contract: actual={quality.actual_distance_m:.1f} m required={quality.requested_distance_m:.1f} m')` |
