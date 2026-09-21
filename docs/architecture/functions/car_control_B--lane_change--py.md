# lane_change：功能记录

上级模块：[模块说明](../modules/vehicle-lateral.md) · 实现：[car_control_B/lane_change.py](../../../car_control_B/lane_change.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [路线、跟踪控制与完成里程](route-control-progress.md)

## 功能职责与范围

Simple lane-change/local-offset path helpers for B.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `smoothstep5`

源码位置：[car_control_B/lane_change.py 第 18 行](../../../car_control_B/lane_change.py#L18)。类型：`FunctionDef`。

```python
smoothstep5(t: float) -> float
```

先把 `t` 截断到 `[0,1]`，再计算五次 smoothstep `10t³-15t⁴+6t⁵`；端点值和一、二阶导数连续，用作横向偏移比例。

### `offset_path`

源码位置：[car_control_B/lane_change.py 第 23 行](../../../car_control_B/lane_change.py#L23)。类型：`FunctionDef`。

```python
offset_path(points: Sequence[Point2D], lateral_offset_m: float) -> List[Point2D]
```

Offset path to its left by positive lateral_offset_m.

### `generate_lane_change_path`

源码位置：[car_control_B/lane_change.py 第 36 行](../../../car_control_B/lane_change.py#L36)。类型：`FunctionDef`。

```python
generate_lane_change_path(base_points: Sequence[Point2D], lateral_offset_m: float, start_s_ratio: float=0.15, end_s_ratio: float=0.85, spacing_m: float=0.5) -> List[Point2D]
```

Generate a smooth lateral offset transition along a base path.

start_s_ratio/end_s_ratio define where the lateral transition begins/ends
over the path index progression. Positive offset means target path is left of
the base path. For CARLA right lane change, use negative offset depending on
map coordinate convention.

## 内部调用与异常路径

- `smoothstep5` 调用：`max`, `min`.
- `offset_path` 调用：`ValueError`, `compute_path_heading`, `enumerate`, `len`, `math.cos`, `math.sin`, `out.append`.
- `generate_lane_change_path` 调用：`ValueError`, `compute_path_heading`, `enumerate`, `int`, `len`, `math.cos`, `math.sin`, `max`, `min`, `out.append`, `resample_path`, `smoothstep5`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `generate_lane_change_path`，第 47 行：`ValueError('path must contain at least two points')`。
- `offset_path`，第 26 行：`ValueError('path must contain at least two points')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_B/path_utils.py](../../../car_control_B/path_utils.py)

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-lateral.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_B/lane_change.py`

来源 SHA256：`4b251978bbf2ea21a00bf5a95ed438fbc999ac6ca42baaf9bdb1d06f3efd2a1b`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `offset_path` / 26 | `len(points) < 2` | `raise ValueError('path must contain at least two points')` |
| `generate_lane_change_path` / 47 | `n < 2` | `raise ValueError('path must contain at least two points')` |
