# fusion_tracker：功能记录

上级模块：[模块说明](../modules/vehicle-perception.md) · 实现：[perception/fusion_tracker.py](../../../perception/fusion_tracker.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [同帧感知、目标身份与来源](perception-authority.md)

## 功能职责与范围

RGB/radar/LiDAR association, stable IDs, TTC and risk summarization.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `Observation.source: Modality`；默认：`未在声明处设置`。
- `Observation.class_name: str`；默认：`未在声明处设置`。
- `Observation.position_m: tuple[float, float, float]`；默认：`未在声明处设置`。
- `Observation.velocity_mps: tuple[float, float, float]`；默认：`未在声明处设置`。
- `Observation.confidence: float`；默认：`未在声明处设置`。
- `Observation.source_id: str | None`；默认：`None`。
- `Observation.bbox_xyxy_norm: tuple[float, float, float, float] | None`；默认：`None`。
- `FusedObject.track_id: str`；默认：`未在声明处设置`。
- `FusedObject.class_name: str`；默认：`未在声明处设置`。
- `FusedObject.position_m: tuple[float, float, float]`；默认：`未在声明处设置`。
- `FusedObject.velocity_mps: tuple[float, float, float]`；默认：`未在声明处设置`。
- `FusedObject.distance_m: float`；默认：`未在声明处设置`。
- `FusedObject.ttc_s: float | None`；默认：`未在声明处设置`。
- `FusedObject.confidence: float`；默认：`未在声明处设置`。
- `FusedObject.sources: tuple[Modality, ...]`；默认：`未在声明处设置`。
- `FusedObject.bbox_xyxy_norm: tuple[float, float, float, float] | None`；默认：`未在声明处设置`。
- `FusedObject.last_frame_id: int`；默认：`未在声明处设置`。
- `FusionTrackerConfig.observation_association_m: float`；默认：`2.5`。
- `FusionTrackerConfig.track_association_m: float`；默认：`4.0`。
- `FusionTrackerConfig.max_track_age_frames: int`；默认：`5`。
- `FusionTrackerConfig.emergency_ttc_s: float`；默认：`1.5`。
- `FusionTrackerConfig.high_ttc_s: float`；默认：`2.5`。
- `FusionTrackerConfig.emergency_gap_m: float`；默认：`5.0`。
- `FusionTrackerConfig.caution_gap_m: float`；默认：`10.0`。
- `FusionResult.objects: tuple[FusedObject, ...]`；默认：`未在声明处设置`。
- `FusionResult.min_gap_m: float | None`；默认：`未在声明处设置`。
- `FusionResult.ttc_s: float | None`；默认：`未在声明处设置`。
- `FusionResult.risk_level: str`；默认：`未在声明处设置`。
- `FusionResult.perception_state: Mapping[str, Any]`；默认：`未在声明处设置`。
- `_TrackState.fused: FusedObject`；默认：`未在声明处设置`。
- `_TrackState.misses: int`；默认：`0`。

## 功能入口：输入、输出与实现说明

### `Observation`

源码位置：[perception/fusion_tracker.py 第 23 行](../../../perception/fusion_tracker.py#L23)。类型：`ClassDef`。

单模态目标观测，位置/速度采用 ego 前x、左y、上z坐标；只允许 RGB/RADAR/LIDAR，类别限定为五种内部类别。`source_id` 和框用于追溯，不直接成为最终 fused track ID。

### `Observation.__post_init__`

源码位置：[perception/fusion_tracker.py 第 32 行](../../../perception/fusion_tracker.py#L32)。类型：`FunctionDef`。

```python
Observation.__post_init__(self) -> None
```

拒绝 VEHICLE_STATE 来源和未支持类别；位置、速度必须是长度3的有限数 tuple，并标准化为 float；置信度必须为非布尔有限数且在 `[0,1]`。当前不校验 `source_id` 与可选框的格式。

### `FusedObject`

源码位置：[perception/fusion_tracker.py 第 51 行](../../../perception/fusion_tracker.py#L51)。类型：`ClassDef`。

融合后的内部不可变目标：稳定 `fused-xxxxxx` ID、加权位置/速度、原点欧氏距离、可空 TTC、合成置信度、参与模态、一个代表框及最后帧号。它由 tracker 构造，本 dataclass 自身没有 post-init 校验。

### `FusionTrackerConfig`

源码位置：[perception/fusion_tracker.py 第 65 行](../../../perception/fusion_tracker.py#L65)。类型：`ClassDef`。

定义同帧观测聚类半径、跨帧 track 半径/寿命以及 TTC/距离风险阈值；数值单位分别为米、帧和秒，不等同于生产 `ConservativeSensorFusion` 的策略配置。

### `FusionTrackerConfig.__post_init__`

源码位置：[perception/fusion_tracker.py 第 74 行](../../../perception/fusion_tracker.py#L74)。类型：`FunctionDef`。

```python
FusionTrackerConfig.__post_init__(self) -> None
```

六个连续阈值必须为非布尔、有限正数，最大 track 丢失帧数必须为正整数。当前没有检查 emergency 阈值必小于 high/caution 阈值，因此反序配置不会在构造时拒绝。

### `FusionResult`

源码位置：[perception/fusion_tracker.py 第 84 行](../../../perception/fusion_tracker.py#L84)。类型：`ClassDef`。

一次融合返回的四项集合：当前可见目标、前向目标最小 gap、所有有效目标最小 TTC、风险等级，以及经 `InterfaceRegistry` 验证后的 canonical perception_state。

### `_TrackState`

源码位置：[perception/fusion_tracker.py 第 93 行](../../../perception/fusion_tracker.py#L93)。类型：`ClassDef`。

内部可变包装，保存最后一次 fused 目标及连续 misses；丢失期 track 可留在内部表中，但不会出现在本帧 `objects` 输出。

### `FusionTracker`

源码位置：[perception/fusion_tracker.py 第 98 行](../../../perception/fusion_tracker.py#L98)。类型：`ClassDef`。

独立的 RGB/雷达/LiDAR 聚类、跨帧关联和 schema 输出实现。它属于 `perception/` 参考管线；生产 CARLA runner 是否使用它必须由调用链证明，不能因类名相似就等同于 `CarlaPerceptionBridge`。

### `FusionTracker.__init__`

源码位置：[perception/fusion_tracker.py 第 99 行](../../../perception/fusion_tracker.py#L99)。类型：`FunctionDef`。

```python
FusionTracker.__init__(self, config: FusionTrackerConfig | None=None, *, registry: InterfaceRegistry | None=None) -> None
```

采用给定或默认配置和接口注册器，初始化空 track 表并从 `fused-000001` 编号。没有 reset 方法；独立 episode 需新建实例或显式管理对象生命周期。

### `FusionTracker.update`

源码位置：[perception/fusion_tracker.py 第 105 行](../../../perception/fusion_tracker.py#L105)。类型：`FunctionDef`。

```python
FusionTracker.update(self, aligned: AlignedSensorFrame, observations: Iterable[Observation], *, ego_speed_mps: float, traffic_light: str='UNKNOWN', distance_to_stop_line_m: float | None=None, speed_limit_mps: float | None=None) -> FusionResult
```

校验 aligned 类型、自车速度和灯态后，将观测转 tuple、同帧聚类、加权融合并跨帧关联。`min_gap_m` 只看 `position_m[0] > 0` 的目标，TTC 取最小有效值；风险由同步/车辆状态和阈值决定。最后组装含模态有效性、同步和降级原因的 state，经 registry 的 `perception_state` schema 验证后返回。

### `FusionTracker._cluster`

源码位置：[perception/fusion_tracker.py 第 161 行](../../../perception/fusion_tracker.py#L161)。类型：`FunctionDef`。

```python
FusionTracker._cluster(self, observations: tuple[Observation, ...]) -> list[list[Observation]]
```

按类别、原点距离、模态和 source ID 确定性排序；对类别兼容且到现有簇算术中心不超过 `observation_association_m` 的最近簇做贪心归并，否则新建簇。结果依赖排序和贪心顺序，不是全局最优匹配。

### `FusionTracker._fuse_cluster`

源码位置：[perception/fusion_tracker.py 第 180 行](../../../perception/fusion_tracker.py#L180)。类型：`FunctionDef`。

```python
FusionTracker._fuse_cluster(self, cluster: list[Observation], frame_id: int, ego_speed_mps: float) -> FusedObject
```

以 `SOURCE_WEIGHT * max(confidence,0.05)` 加权位置/速度；类别选置信度和来源权重最大的观测，置信度按互补概率合成并封顶1。TTC 只在前向位置为正且 closing speed 大于0.05 m/s时计算；代表框取有框观测中置信度最高者。此时 track ID 留空，下一步再关联。

### `FusionTracker._associate_tracks`

源码位置：[perception/fusion_tracker.py 第 194 行](../../../perception/fusion_tracker.py#L194)。类型：`FunctionDef`。

```python
FusionTracker._associate_tracks(self, candidates: list[FusedObject], frame_id: int) -> tuple[FusedObject, ...]
```

候选按距离/类别排序，贪心选择类别兼容且三维距离不超过 `track_association_m` 的未占用旧 track，否则分配新 ID。未匹配旧 track 的 misses 加1并最多保留配置帧数，但输出只包含 misses=0 的当前可见目标，按距离和ID排序。

### `FusionTracker._risk`

源码位置：[perception/fusion_tracker.py 第 227 行](../../../perception/fusion_tracker.py#L227)。类型：`FunctionDef`。

```python
FusionTracker._risk(self, gap: float | None, ttc: float | None, aligned: AlignedSensorFrame) -> str
```

感知 stale 或 VEHICLE_STATE 无效时优先返回 UNKNOWN；否则 TTC/距离任一触发紧急阈值为 EMERGENCY，接着是 TTC HIGH、距离 CAUTION，最后 LOW。缺失 gap/TTC 本身不会变成 UNKNOWN，只由同步和车辆状态有效性决定。

### `FusionTracker._class_compatible`

源码位置：[perception/fusion_tracker.py 第 239 行](../../../perception/fusion_tracker.py#L239)。类型：`FunctionDef`。

```python
FusionTracker._class_compatible(first: str, second: str) -> bool
```

完全相同类别可关联；任一类别为 `unknown` 或 `obstacle` 也视为兼容。它可能把泛化障碍与具体道路参与者合并，因此类别和来源证据都应保留。

### `FusionTracker._object_payload`

源码位置：[perception/fusion_tracker.py 第 243 行](../../../perception/fusion_tracker.py#L243)。类型：`FunctionDef`。

```python
FusionTracker._object_payload(item: FusedObject) -> dict[str, Any]
```

把 fused 对象转成 schema JSON 形态：tuple 转 list、模态枚举转字符串，可空框保持 null。该函数不重新校验数值，最终由 registry 统一验证。

## 内部调用与异常路径

- `__post_init__` 调用：`ValueError`, `all`, `float`, `getattr`, `isinstance`, `len`, `math.isfinite`, `object.__setattr__`, `tuple`, `type`.
- `__init__` 调用：`FusionTrackerConfig`, `InterfaceRegistry`.
- `update` 调用：`FusionResult`, `TypeError`, `ValueError`, `aligned.modality_valid.get`, `any`, `bool`, `float`, `isinstance`, `list`, `math.isfinite`, `min`, `self._associate_tracks`, `self._cluster`, `self._fuse_cluster`, `self._object_payload`, `self._risk`, `self.registry.validate`, `tuple`, `type`.
- `_cluster` 调用：`clusters.append`, `clusters[best[1]].append`, `enumerate`, `len`, `math.dist`, `range`, `self._class_compatible`, `sorted`, `sum`, `tuple`.
- `_fuse_cluster` 调用：`FusedObject`, `math.dist`, `math.prod`, `max`, `min`, `next`, `range`, `sorted`, `sum`, `tuple`, `zip`.
- `_associate_tracks` 调用：`FusedObject`, `_TrackState`, `math.dist`, `min`, `next_tracks.values`, `self._class_compatible`, `set`, `sorted`, `tuple`, `unmatched.remove`, `visible.sort`.
- `_risk` 调用：`aligned.modality_valid.get`.
- `_object_payload` 调用：`list`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__post_init__`，第 34 行：`ValueError('observation source must be RGB/RADAR/LIDAR')`。
- `__post_init__`，第 36 行：`ValueError('unsupported observation class')`。
- `__post_init__`，第 43 行：`ValueError(f'{name} must be a finite three-number tuple')`。
- `__post_init__`，第 46 行：`ValueError('confidence must be finite and in [0, 1]')`。
- `__post_init__`，第 78 行：`ValueError(f'{name} must be finite and positive')`。
- `__post_init__`，第 80 行：`ValueError('max_track_age_frames must be positive')`。
- `update`，第 116 行：`TypeError('aligned must be AlignedSensorFrame')`。
- `update`，第 118 行：`ValueError('ego_speed_mps must be finite and non-negative')`。
- `update`，第 120 行：`ValueError('traffic_light is invalid')`。
- `update`，第 123 行：`TypeError('observations must contain Observation values')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [perception/sensor_adapter.py](../../../perception/sensor_adapter.py)
- [runtime/interface_registry.py](../../../runtime/interface_registry.py)

静态 import 消费者（含测试）：

- [perception/__init__.py](../../../perception/__init__.py)
- [perception/fault_injection.py](../../../perception/fault_injection.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-perception.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `perception/fusion_tracker.py`

来源 SHA256：`757e6feda187bfbf5db97f3b2be63464b750e58ac16cd79c395376ff439a67bd`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `Observation.source` | `Modality` | `无声明默认；构造/赋值方提供` |
| `Observation.class_name` | `str` | `无声明默认；构造/赋值方提供` |
| `Observation.position_m` | `tuple[float, float, float]` | `无声明默认；构造/赋值方提供` |
| `Observation.velocity_mps` | `tuple[float, float, float]` | `无声明默认；构造/赋值方提供` |
| `Observation.confidence` | `float` | `无声明默认；构造/赋值方提供` |
| `Observation.source_id` | `str &#124; None` | `None` |
| `Observation.bbox_xyxy_norm` | `tuple[float, float, float, float] &#124; None` | `None` |
| `FusedObject.track_id` | `str` | `无声明默认；构造/赋值方提供` |
| `FusedObject.class_name` | `str` | `无声明默认；构造/赋值方提供` |
| `FusedObject.position_m` | `tuple[float, float, float]` | `无声明默认；构造/赋值方提供` |
| `FusedObject.velocity_mps` | `tuple[float, float, float]` | `无声明默认；构造/赋值方提供` |
| `FusedObject.distance_m` | `float` | `无声明默认；构造/赋值方提供` |
| `FusedObject.ttc_s` | `float &#124; None` | `无声明默认；构造/赋值方提供` |
| `FusedObject.confidence` | `float` | `无声明默认；构造/赋值方提供` |
| `FusedObject.sources` | `tuple[Modality, ...]` | `无声明默认；构造/赋值方提供` |
| `FusedObject.bbox_xyxy_norm` | `tuple[float, float, float, float] &#124; None` | `无声明默认；构造/赋值方提供` |
| `FusedObject.last_frame_id` | `int` | `无声明默认；构造/赋值方提供` |
| `FusionTrackerConfig.observation_association_m` | `float` | `2.5` |
| `FusionTrackerConfig.track_association_m` | `float` | `4.0` |
| `FusionTrackerConfig.max_track_age_frames` | `int` | `5` |
| `FusionTrackerConfig.emergency_ttc_s` | `float` | `1.5` |
| `FusionTrackerConfig.high_ttc_s` | `float` | `2.5` |
| `FusionTrackerConfig.emergency_gap_m` | `float` | `5.0` |
| `FusionTrackerConfig.caution_gap_m` | `float` | `10.0` |
| `FusionResult.objects` | `tuple[FusedObject, ...]` | `无声明默认；构造/赋值方提供` |
| `FusionResult.min_gap_m` | `float &#124; None` | `无声明默认；构造/赋值方提供` |
| `FusionResult.ttc_s` | `float &#124; None` | `无声明默认；构造/赋值方提供` |
| `FusionResult.risk_level` | `str` | `无声明默认；构造/赋值方提供` |
| `FusionResult.perception_state` | `Mapping[str, Any]` | `无声明默认；构造/赋值方提供` |
| `_TrackState.fused` | `FusedObject` | `无声明默认；构造/赋值方提供` |
| `_TrackState.misses` | `int` | `0` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `Observation.__post_init__` / 34 | `self.source not in {Modality.RGB, Modality.RADAR, Modality.LIDAR}` | `raise ValueError('observation source must be RGB/RADAR/LIDAR')` |
| `Observation.__post_init__` / 36 | `self.class_name not in {'vehicle', 'pedestrian', 'cyclist', 'obstacle', 'unknown'}` | `raise ValueError('unsupported observation class')` |
| `Observation.__post_init__` / 43 | `type(values) is not tuple or len(values) != 3 or (not all((type(value) in (int, float) and (not isinstance(value, bool)) and math.isfinite(float(value)) for value in values)))` | `raise ValueError(f'{name} must be a finite three-number tuple')` |
| `Observation.__post_init__` / 46 | `type(self.confidence) not in (int, float) or isinstance(self.confidence, bool) or (not math.isfinite(float(self.confidence))) or (not 0 <= self.confidence <= 1)` | `raise ValueError('confidence must be finite and in [0, 1]')` |
| `FusionTrackerConfig.__post_init__` / 78 | `type(value) not in (int, float) or isinstance(value, bool) or (not math.isfinite(float(value))) or (value <= 0)` | `raise ValueError(f'{name} must be finite and positive')` |
| `FusionTrackerConfig.__post_init__` / 80 | `type(self.max_track_age_frames) is not int or self.max_track_age_frames < 1` | `raise ValueError('max_track_age_frames must be positive')` |
| `FusionTracker.update` / 116 | `not isinstance(aligned, AlignedSensorFrame)` | `raise TypeError('aligned must be AlignedSensorFrame')` |
| `FusionTracker.update` / 118 | `type(ego_speed_mps) not in (int, float) or isinstance(ego_speed_mps, bool) or (not math.isfinite(float(ego_speed_mps))) or (ego_speed_mps < 0)` | `raise ValueError('ego_speed_mps must be finite and non-negative')` |
| `FusionTracker.update` / 120 | `traffic_light not in {'RED', 'YELLOW', 'GREEN', 'UNKNOWN'}` | `raise ValueError('traffic_light is invalid')` |
| `FusionTracker.update` / 123 | `any((not isinstance(item, Observation) for item in observations))` | `raise TypeError('observations must contain Observation values')` |
