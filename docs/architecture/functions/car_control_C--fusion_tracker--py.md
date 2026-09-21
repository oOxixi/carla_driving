# fusion_tracker：功能记录

上级模块：[模块说明](../modules/vehicle-longitudinal.md) · 实现：[car_control_C/fusion_tracker.py](../../../car_control_C/fusion_tracker.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [目标速度、跟车风险与D交接](longitudinal-safety-contract.md)

## 功能职责与范围

C-role multi-sensor association and risk summary helpers.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `PerceptionTarget.class_name: str`；默认：`未在声明处设置`。
- `PerceptionTarget.distance_m: float`；默认：`未在声明处设置`。
- `PerceptionTarget.speed_mps: float`；默认：`未在声明处设置`。
- `PerceptionTarget.confidence: float`；默认：`未在声明处设置`。
- `PerceptionTarget.source: str`；默认：`未在声明处设置`。
- `PerceptionTarget.x_m: float | None`；默认：`None`。
- `PerceptionTarget.y_m: float | None`；默认：`None`。
- `PerceptionTarget.target_id: str | None`；默认：`None`。
- `PerceptionTarget.ttc_s: float | None`；默认：`None`。
- `PerceptionTarget.risk_level: str`；默认：`'CLEAR'`。

## 功能入口：输入、输出与实现说明

### `PerceptionTarget`

源码位置：[car_control_C/fusion_tracker.py 第 10 行](../../../car_control_C/fusion_tracker.py#L10)。类型：`ClassDef`。

冻结的目标摘要，保存类别、距离、速度、置信度、来源及可选位置/ID/TTC/风险级别；它不是生产 `PerceptionFrame`，主要用于 C 交付辅助记录。

### `PerceptionTarget.__post_init__`

源码位置：[car_control_C/fusion_tracker.py 第 22 行](../../../car_control_C/fusion_tracker.py#L22)。类型：`FunctionDef`。

```python
PerceptionTarget.__post_init__(self) -> None
```

要求类别和来源去空白后非空、距离非负、置信度在 `[0,1]`。当前未显式检查速度、位置和 TTC 是否有限，调用方不能据构造成功推断所有数值都可靠。

### `PerceptionTarget.to_dict`

源码位置：[car_control_C/fusion_tracker.py 第 32 行](../../../car_control_C/fusion_tracker.py#L32)。类型：`FunctionDef`。

```python
PerceptionTarget.to_dict(self) -> dict[str, object]
```

返回 JSON-ready 目标字典，把位置组织为 `{x,y}` 并保留可空字段；不附 schema version，也不修改 tracker。

### `StableTargetTracker`

源码位置：[car_control_C/fusion_tracker.py 第 46 行](../../../car_control_C/fusion_tracker.py#L46)。类型：`ClassDef`。

Assign stable target IDs using class and nearest-range continuity.

### `StableTargetTracker.__init__`

源码位置：[car_control_C/fusion_tracker.py 第 49 行](../../../car_control_C/fusion_tracker.py#L49)。类型：`FunctionDef`。

```python
StableTargetTracker.__init__(self, *, ego_speed_mps: float=4.0, road_curvature_per_m: float=0.0, sensor_margin_scale: float=1.0, max_association_distance_m: float=2.0) -> None
```

保存自车速度、曲率、传感器 margin scale 和最大距离关联阈值，ID 从 `C-001` 开始并创建内存轨迹表。构造器当前只转 float，未独立拒绝负值或非有限值。

### `StableTargetTracker.update`

源码位置：[car_control_C/fusion_tracker.py 第 60 行](../../../car_control_C/fusion_tracker.py#L60)。类型：`FunctionDef`。

```python
StableTargetTracker.update(self, target: PerceptionTarget) -> PerceptionTarget
```

优先复用显式已知 ID，否则按类别和最近距离连续性关联；未命中则分配新 ID。随后计算 TTC/风险，以 `replace` 返回富化目标并覆盖该 ID 的最新轨迹。

### `StableTargetTracker._match_target`

源码位置：[car_control_C/fusion_tracker.py 第 74 行](../../../car_control_C/fusion_tracker.py#L74)。类型：`FunctionDef`。

```python
StableTargetTracker._match_target(self, target: PerceptionTarget) -> str | None
```

显式 target_id 已在轨迹表时直接复用；否则按插入顺序找第一个类别忽略大小写相同、距离差不超过阈值的轨迹。没有位置、速度或一对一全局匹配，邻近同类目标可能换 ID。

### `StableTargetTracker._ttc_s`

源码位置：[car_control_C/fusion_tracker.py 第 84 行](../../../car_control_C/fusion_tracker.py#L84)。类型：`FunctionDef`。

```python
StableTargetTracker._ttc_s(self, target: PerceptionTarget) -> float | None
```

用固定构造时自车速度减目标速度得到接近速度；小于等于零返回 `None`，否则返回距离/接近速度并四舍五入到 3 位。不会随 update 自动刷新自车速度。

### `StableTargetTracker._risk_level`

源码位置：[car_control_C/fusion_tracker.py 第 90 行](../../../car_control_C/fusion_tracker.py#L90)。类型：`FunctionDef`。

```python
StableTargetTracker._risk_level(self, target: PerceptionTarget) -> str
```

结合 TTC 阈值与 `dynamic_safety_distance` 的 caution/emergency 距离，按 EMERGENCY→CAUTION→CLEAR 优先级分类；类别和 sensor margin 会影响动态包络，但结果只是摘要标签，不直接执行控制。

## 内部调用与异常路径

- `__post_init__` 调用：`ValueError`, `float`, `self.class_name.strip`, `self.source.strip`.
- `to_dict` 调用：`float`.
- `__init__` 调用：`float`.
- `update` 调用：`replace`, `self._match_target`, `self._risk_level`, `self._ttc_s`.
- `_match_target` 调用：`abs`, `previous.class_name.lower`, `self._tracks.items`, `target.class_name.lower`.
- `_ttc_s` 调用：`float`, `round`.
- `_risk_level` 调用：`dynamic_safety_distance`, `float`, `max`, `self._ttc_s`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__post_init__`，第 24 行：`ValueError('class_name must be non-empty')`。
- `__post_init__`，第 26 行：`ValueError('distance_m must be non-negative')`。
- `__post_init__`，第 28 行：`ValueError('confidence must be in [0, 1]')`。
- `__post_init__`，第 30 行：`ValueError('source must be non-empty')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [config/strategy.py](../../../config/strategy.py)

静态 import 消费者（含测试）：

- [car_control_C/tests/test_c_deliverables.py](../../../car_control_C/tests/test_c_deliverables.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-longitudinal.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_C/fusion_tracker.py`

来源 SHA256：`34dd6f42313ebcb9685d6c790039bf25996f312b29270131f71984b01fb60085`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `PerceptionTarget.class_name` | `str` | `无声明默认；构造/赋值方提供` |
| `PerceptionTarget.distance_m` | `float` | `无声明默认；构造/赋值方提供` |
| `PerceptionTarget.speed_mps` | `float` | `无声明默认；构造/赋值方提供` |
| `PerceptionTarget.confidence` | `float` | `无声明默认；构造/赋值方提供` |
| `PerceptionTarget.source` | `str` | `无声明默认；构造/赋值方提供` |
| `PerceptionTarget.x_m` | `float &#124; None` | `None` |
| `PerceptionTarget.y_m` | `float &#124; None` | `None` |
| `PerceptionTarget.target_id` | `str &#124; None` | `None` |
| `PerceptionTarget.ttc_s` | `float &#124; None` | `None` |
| `PerceptionTarget.risk_level` | `str` | `'CLEAR'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `PerceptionTarget.__post_init__` / 24 | `not self.class_name.strip()` | `raise ValueError('class_name must be non-empty')` |
| `PerceptionTarget.__post_init__` / 26 | `float(self.distance_m) < 0.0` | `raise ValueError('distance_m must be non-negative')` |
| `PerceptionTarget.__post_init__` / 28 | `not 0.0 <= float(self.confidence) <= 1.0` | `raise ValueError('confidence must be in [0, 1]')` |
| `PerceptionTarget.__post_init__` / 30 | `not self.source.strip()` | `raise ValueError('source must be non-empty')` |
