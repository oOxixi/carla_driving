# execution_stage：功能记录

上级模块：[模块说明](../modules/vehicle-lateral.md) · 实现：[integration/execution_stage.py](../../../integration/execution_stage.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [路线、跟踪控制与完成里程](route-control-progress.md)

## 功能职责与范围

Stateful execution helpers kept outside the CARLA orchestration shell.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `RouteProgressTracker.points_xy_m: Sequence[tuple[float, float]]`；默认：`未在声明处设置`。
- `RouteProgressTracker.progress_m: float`；默认：`0.0`。
- `DistanceCoverageTracker.progress_m: float`；默认：`0.0`。
- `DistanceCoverageTracker.previous_xy_m: tuple[float, float] | None`；默认：`None`。
- `DistanceCoverageTracker.minimum_jump_gate_m: float`；默认：`2.0`。

## 功能入口：输入、输出与实现说明

### `RouteProgressTracker`

源码位置：[integration/execution_stage.py 第 12 行](../../../integration/execution_stage.py#L12)。类型：`ClassDef`。

保存全局路线点与当前弧长进度的可变跟踪器；`progress_m` 初始 0，路线点由调用方提供且构造时不复制。

### `RouteProgressTracker.update`

源码位置：[integration/execution_stage.py 第 16 行](../../../integration/execution_stage.py#L16)。类型：`FunctionDef`。

```python
RouteProgressTracker.update(self, x_m: float, y_m: float, *, speed_mps: float, delta_s: float) -> float
```

把车辆位置投影到可能自交的路线，并以已有进度禁止回退；前向候选窗取 `max(20m, speed*delta*8)`。速度和 delta 未在本层单独校验，投影函数负责坐标及路线有效性。调用会覆盖并返回 `progress_m`。

### `DistanceCoverageTracker`

源码位置：[integration/execution_stage.py 第 28 行](../../../integration/execution_stage.py#L28)。类型：`ClassDef`。

Accumulate real driven distance while rejecting simulator teleports.

Topology-coverage contracts measure continuous distance travelled, not
closeness to one fixed lane-centre polyline. A legitimate permanent lane
change otherwise makes route projection stall even while the ego keeps
driving. Large discontinuities are ignored so recovery teleports cannot
satisfy the contract.

### `DistanceCoverageTracker.update`

源码位置：[integration/execution_stage.py 第 42 行](../../../integration/execution_stage.py#L42)。类型：`FunctionDef`。

```python
DistanceCoverageTracker.update(self, x_m: float, y_m: float, *, speed_mps: float, delta_s: float) -> float
```

首帧只保存有限位置；后续计算实际位移，跳跃门限为 `max(minimum_jump_gate_m, max(speed,0)*max(delta,0)*3+1)`，只有不超过门限才累计。无论是否累计都更新 previous 位置，因此一次 teleport 不会在下一帧重复计入。

## 内部调用与异常路径

- `update` 调用：`ValueError`, `all`, `float`, `math.dist`, `math.isfinite`, `max`, `project_route_progress_m`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `update`，第 45 行：`ValueError('coverage position must be finite')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [integration/route_geometry.py](../../../integration/route_geometry.py)

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

### `integration/execution_stage.py`

来源 SHA256：`9b2776d784310f4e34efa880b65023df975a0ea99cdd46651b0c8e411d43f5fb`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `RouteProgressTracker.points_xy_m` | `Sequence[tuple[float, float]]` | `无声明默认；构造/赋值方提供` |
| `RouteProgressTracker.progress_m` | `float` | `0.0` |
| `DistanceCoverageTracker.progress_m` | `float` | `0.0` |
| `DistanceCoverageTracker.previous_xy_m` | `tuple[float, float] &#124; None` | `None` |
| `DistanceCoverageTracker.minimum_jump_gate_m` | `float` | `2.0` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `DistanceCoverageTracker.update` / 45 | `not all((math.isfinite(value) for value in current))` | `raise ValueError('coverage position must be finite')` |
