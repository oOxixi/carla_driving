# simulator：功能记录

上级模块：[模块说明](../modules/vehicle-behavior.md) · 实现：[car_control_A/simulator.py](../../../car_control_A/simulator.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [授权、确认、过期与停车保持](command-lifecycle.md)
- [前置条件锁存、步骤完成与重规划](maneuver-progress.md)

## 功能职责与范围

CARLA lifecycle primitives owned by member A.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `ActorRegistry._actors: list[Any]`；默认：`field(default_factory=list)`。

## 功能入口：输入、输出与实现说明

### `_clone_world_settings`

源码位置：[car_control_A/simulator.py 第 17 行](../../../car_control_A/simulator.py#L17)。类型：`FunctionDef`。

```python
_clone_world_settings(settings: Any) -> Any
```

Clone CARLA ``WorldSettings`` without relying on Python pickling.

CARLA 0.9.16's Boost.Python ``WorldSettings`` explicitly rejects
``copy.copy``.  Its public properties are nevertheless ordinary readable
and writable fields.  Reconstructing through the concrete settings class
keeps this module CARLA-import-free and also works with the fake settings
used in unit tests.

### `SensorFrameBuffer`

源码位置：[car_control_A/simulator.py 第 48 行](../../../car_control_A/simulator.py#L48)。类型：`ClassDef`。

Thread-safe, bounded sensor callback storage keyed by CARLA frame number.

### `SensorFrameBuffer.__init__`

源码位置：[car_control_A/simulator.py 第 51 行](../../../car_control_A/simulator.py#L51)。类型：`FunctionDef`。

```python
SensorFrameBuffer.__init__(self, *, max_frames: int=32) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SensorFrameBuffer.pending_frames`

源码位置：[car_control_A/simulator.py 第 62 行](../../../car_control_A/simulator.py#L62)。类型：`FunctionDef`。

```python
SensorFrameBuffer.pending_frames(self) -> tuple[int, ...]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SensorFrameBuffer.push`

源码位置：[car_control_A/simulator.py 第 66 行](../../../car_control_A/simulator.py#L66)。类型：`FunctionDef`。

```python
SensorFrameBuffer.push(self, sensor_id: str, frame: int, payload: Any) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SensorFrameBuffer.callback`

源码位置：[car_control_A/simulator.py 第 85 行](../../../car_control_A/simulator.py#L85)。类型：`FunctionDef`。

```python
SensorFrameBuffer.callback(self, sensor_id: str) -> Callable[[Any], None]
```

Return a CARLA sensor callback without importing CARLA itself.

### `SensorFrameBuffer.callback.receive`

源码位置：[car_control_A/simulator.py 第 90 行](../../../car_control_A/simulator.py#L90)。类型：`FunctionDef`。

```python
SensorFrameBuffer.callback.receive(measurement: Any) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SensorFrameBuffer.pop_aligned`

源码位置：[car_control_A/simulator.py 第 95 行](../../../car_control_A/simulator.py#L95)。类型：`FunctionDef`。

```python
SensorFrameBuffer.pop_aligned(self, sensor_ids: Iterable[str], frame: int, *, timeout_s: float) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SensorFrameBuffer.pop_aligned_optional`

源码位置：[car_control_A/simulator.py 第 100 行](../../../car_control_A/simulator.py#L100)。类型：`FunctionDef`。

```python
SensorFrameBuffer.pop_aligned_optional(self, required_sensor_ids: Iterable[str], optional_sensor_ids: Iterable[str], frame: int, *, timeout_s: float, optional_grace_s: float=0.01) -> dict[str, Any]
```

Return exact-frame required data plus any bounded-wait optional data.

### `ActorRegistry`

源码位置：[car_control_A/simulator.py 第 161 行](../../../car_control_A/simulator.py#L161)。类型：`ClassDef`。

Owns spawned CARLA actors and releases them in safe reverse order.

### `ActorRegistry.track`

源码位置：[car_control_A/simulator.py 第 166 行](../../../car_control_A/simulator.py#L166)。类型：`FunctionDef`。

```python
ActorRegistry.track(self, actor: Any) -> Any
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ActorRegistry.release`

源码位置：[car_control_A/simulator.py 第 172 行](../../../car_control_A/simulator.py#L172)。类型：`FunctionDef`。

```python
ActorRegistry.release(self, actor: Any) -> bool
```

Destroy and forget one owned actor before session shutdown.

Long scenarios may activate temporary traffic participants for a
bounded event.  Releasing them here keeps ownership centralized and
prevents ``cleanup()`` from destroying the same actor a second time.
Identity comparison is intentional because CARLA actor wrappers do
not promise useful equality semantics.

### `ActorRegistry.cleanup`

源码位置：[car_control_A/simulator.py 第 188 行](../../../car_control_A/simulator.py#L188)。类型：`FunctionDef`。

```python
ActorRegistry.cleanup(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ActorRegistry.dispose`

源码位置：[car_control_A/simulator.py 第 194 行](../../../car_control_A/simulator.py#L194)。类型：`FunctionDef`。

```python
ActorRegistry.dispose(actor: Any) -> None
```

Best-effort listener stop and actor destruction used on all failures.

### `SynchronousWorld`

源码位置：[car_control_A/simulator.py 第 210 行](../../../car_control_A/simulator.py#L210)。类型：`ClassDef`。

Temporarily makes one CARLA World synchronous; this is the sole tick API.

### `SynchronousWorld.__init__`

源码位置：[car_control_A/simulator.py 第 213 行](../../../car_control_A/simulator.py#L213)。类型：`FunctionDef`。

```python
SynchronousWorld.__init__(self, world: Any, *, traffic_manager: Any | None=None, fixed_delta_seconds: float=0.05, tm_previous_synchronous_mode: bool | None=None) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SynchronousWorld.__enter__`

源码位置：[car_control_A/simulator.py 第 236 行](../../../car_control_A/simulator.py#L236)。类型：`FunctionDef`。

```python
SynchronousWorld.__enter__(self) -> SynchronousWorld
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SynchronousWorld.tick`

源码位置：[car_control_A/simulator.py 第 263 行](../../../car_control_A/simulator.py#L263)。类型：`FunctionDef`。

```python
SynchronousWorld.tick(self, timeout_s: float | None=None) -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SynchronousWorld.__exit__`

源码位置：[car_control_A/simulator.py 第 270 行](../../../car_control_A/simulator.py#L270)。类型：`FunctionDef`。

```python
SynchronousWorld.__exit__(self, exc_type: object, exc: object, traceback: object) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `CarlaSession`

源码位置：[car_control_A/simulator.py 第 292 行](../../../car_control_A/simulator.py#L292)。类型：`ClassDef`。

One owner for a synchronous world, its sensor actors, and world ticks.

### `CarlaSession.__init__`

源码位置：[car_control_A/simulator.py 第 295 行](../../../car_control_A/simulator.py#L295)。类型：`FunctionDef`。

```python
CarlaSession.__init__(self, world: Any, **synchronous_world_options: Any) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `CarlaSession.__enter__`

源码位置：[car_control_A/simulator.py 第 302 行](../../../car_control_A/simulator.py#L302)。类型：`FunctionDef`。

```python
CarlaSession.__enter__(self) -> CarlaSession
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `CarlaSession.track_actor`

源码位置：[car_control_A/simulator.py 第 307 行](../../../car_control_A/simulator.py#L307)。类型：`FunctionDef`。

```python
CarlaSession.track_actor(self, actor: Any) -> Any
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `CarlaSession.tick`

源码位置：[car_control_A/simulator.py 第 312 行](../../../car_control_A/simulator.py#L312)。类型：`FunctionDef`。

```python
CarlaSession.tick(self, timeout_s: float | None=None) -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `CarlaSession.spawn_ego`

源码位置：[car_control_A/simulator.py 第 317 行](../../../car_control_A/simulator.py#L317)。类型：`FunctionDef`。

```python
CarlaSession.spawn_ego(self, blueprint: Any, transform: Any) -> Any
```

Spawn and register the sole ego vehicle for this session.

### `CarlaSession.attach_sensor`

源码位置：[car_control_A/simulator.py 第 323 行](../../../car_control_A/simulator.py#L323)。类型：`FunctionDef`。

```python
CarlaSession.attach_sensor(self, blueprint: Any, transform: Any, parent: Any, sensor_id: str) -> Any
```

Spawn a sensor, register it, and wire its callback into frame alignment.

### `CarlaSession.__exit__`

源码位置：[car_control_A/simulator.py 第 342 行](../../../car_control_A/simulator.py#L342)。类型：`FunctionDef`。

```python
CarlaSession.__exit__(self, exc_type: object, exc: object, traceback: object) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_clone_world_settings` 调用：`callable`, `dir`, `getattr`, `name.startswith`, `setattr`, `type`, `type(settings)`, `values.items`.
- `__init__` 调用：`ActorRegistry`, `OrderedDict`, `SensorFrameBuffer`, `SynchronousWorld`, `TypeError`, `ValueError`, `float`, `threading.Condition`, `type`.
- `pending_frames` 调用：`sorted`, `tuple`.
- `push` 调用：`ValueError`, `len`, `min`, `self._condition.notify_all`, `self._frames.setdefault`, `type`.
- `callback` 调用：`ValueError`, `self.push`, `type`.
- `pop_aligned` 调用：`self.pop_aligned_optional`.
- `pop_aligned_optional` 调用：`TimeoutError`, `ValueError`, `all`, `any`, `float`, `len`, `max`, `min`, `self._condition.wait`, `self._frames.get`, `set`, `time.monotonic`, `tuple`, `type`.
- `track` 调用：`ValueError`, `self._actors.append`.
- `release` 调用：`enumerate`, `self.dispose`.
- `cleanup` 调用：`reversed`, `self.dispose`.
- `dispose` 调用：`callable`, `destroy`, `getattr`, `stop`.
- `__enter__` 调用：`RuntimeError`, `_clone_world_settings`, `self._sync.__enter__`, `self._traffic_manager.set_synchronous_mode`, `self._world.apply_settings`, `self._world.get_settings`.
- `tick` 调用：`RuntimeError`, `self._sync.tick`, `self._world.tick`.
- `__exit__` 调用：`_clone_world_settings`, `self._sync.__exit__`, `self._traffic_manager.set_synchronous_mode`, `self._world.apply_settings`, `self.actors.cleanup`.
- `track_actor` 调用：`RuntimeError`, `self.actors.track`.
- `spawn_ego` 调用：`RuntimeError`, `self._world.spawn_actor`, `self.track_actor`.
- `attach_sensor` 调用：`ActorRegistry.dispose`, `RuntimeError`, `TypeError`, `ValueError`, `callable`, `getattr`, `listen`, `self._world.spawn_actor`, `self.frame_buffer.callback`, `self.track_actor`.
- `receive` 调用：`self.push`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__enter__`，第 238 行：`RuntimeError('SynchronousWorld is already active')`。
- `__exit__`，第 289 行：`restore_error`。
- `__init__`，第 53 行：`ValueError('max_frames must be a positive integer')`。
- `__init__`，第 222 行：`ValueError('world must not be None')`。
- `__init__`，第 224 行：`ValueError('fixed_delta_seconds must be positive')`。
- `__init__`，第 226 行：`ValueError('tm_previous_synchronous_mode must be explicitly provided with traffic_manager')`。
- `__init__`，第 228 行：`TypeError('tm_previous_synchronous_mode must be bool')`。
- `attach_sensor`，第 326 行：`RuntimeError('attach_sensor() requires an active CarlaSession')`。
- `attach_sensor`，第 328 行：`ValueError('parent must not be None')`。
- `attach_sensor`，第 334 行：`TypeError('sensor actor must provide listen(callback)')`。
- `callback`，第 88 行：`ValueError('sensor_id must be a non-empty string')`。
- `pop_aligned_optional`，第 114 行：`ValueError('sensor_ids must be non-empty and required sensors cannot be empty')`。
- `pop_aligned_optional`，第 116 行：`ValueError('required and optional sensor_ids must be unique and disjoint')`。
- `pop_aligned_optional`，第 118 行：`ValueError('frame must be a non-negative integer')`。
- `pop_aligned_optional`，第 120 行：`ValueError('timeout_s must be a non-negative number')`。
- `pop_aligned_optional`，第 122 行：`ValueError('optional_grace_s must be a non-negative number')`。
- `pop_aligned_optional`，第 156 行：`TimeoutError(f'timed out waiting for aligned sensors at frame={frame}')`。
- `push`，第 68 行：`ValueError('sensor_id must be a non-empty string')`。
- `push`，第 70 行：`ValueError('frame must be a non-negative integer')`。
- `spawn_ego`，第 320 行：`RuntimeError('spawn_ego() requires an active CarlaSession')`。
- `tick`，第 265 行：`RuntimeError('SynchronousWorld.tick() requires an active context')`。
- `tick`，第 314 行：`RuntimeError('tick() requires an active CarlaSession')`。
- `track`，第 168 行：`ValueError('actor must not be None')`。
- `track_actor`，第 309 行：`RuntimeError('track_actor() requires an active CarlaSession')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [car_control_A/__init__.py](../../../car_control_A/__init__.py)
- [car_control_A/tests/test_simulator.py](../../../car_control_A/tests/test_simulator.py)
- [car_control_A/tests/test_simulator_smoke.py](../../../car_control_A/tests/test_simulator_smoke.py)
- [integration/tests/test_carla_perception.py](../../../integration/tests/test_carla_perception.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-behavior.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_A/simulator.py`

来源 SHA256：`afe4fb6a19d4fa0dd0d7c86a103f12a9072258941cb2547abe53556ef233942c`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `ActorRegistry._actors` | `list[Any]` | `field(default_factory=list)` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `SensorFrameBuffer.__init__` / 53 | `type(max_frames) is not int or max_frames < 1` | `raise ValueError('max_frames must be a positive integer')` |
| `SensorFrameBuffer.push` / 68 | `type(sensor_id) is not str or not sensor_id` | `raise ValueError('sensor_id must be a non-empty string')` |
| `SensorFrameBuffer.push` / 70 | `type(frame) is not int or frame < 0` | `raise ValueError('frame must be a non-negative integer')` |
| `SensorFrameBuffer.callback` / 88 | `type(sensor_id) is not str or not sensor_id` | `raise ValueError('sensor_id must be a non-empty string')` |
| `SensorFrameBuffer.pop_aligned_optional` / 114 | `not required or any((type(sensor_id) is not str or not sensor_id for sensor_id in requested))` | `raise ValueError('sensor_ids must be non-empty and required sensors cannot be empty')` |
| `SensorFrameBuffer.pop_aligned_optional` / 116 | `len(set(requested)) != len(requested)` | `raise ValueError('required and optional sensor_ids must be unique and disjoint')` |
| `SensorFrameBuffer.pop_aligned_optional` / 118 | `type(frame) is not int or frame < 0` | `raise ValueError('frame must be a non-negative integer')` |
| `SensorFrameBuffer.pop_aligned_optional` / 120 | `type(timeout_s) not in (int, float) or timeout_s < 0` | `raise ValueError('timeout_s must be a non-negative number')` |
| `SensorFrameBuffer.pop_aligned_optional` / 122 | `type(optional_grace_s) not in (int, float) or optional_grace_s < 0` | `raise ValueError('optional_grace_s must be a non-negative number')` |
| `SensorFrameBuffer.pop_aligned_optional` / 156 | `remaining <= 0` | `raise TimeoutError(f'timed out waiting for aligned sensors at frame={frame}')` |
| `ActorRegistry.track` / 168 | `actor is None` | `raise ValueError('actor must not be None')` |
| `SynchronousWorld.__init__` / 222 | `world is None` | `raise ValueError('world must not be None')` |
| `SynchronousWorld.__init__` / 224 | `type(fixed_delta_seconds) not in (int, float) or fixed_delta_seconds <= 0` | `raise ValueError('fixed_delta_seconds must be positive')` |
| `SynchronousWorld.__init__` / 226 | `traffic_manager is not None and tm_previous_synchronous_mode is None` | `raise ValueError('tm_previous_synchronous_mode must be explicitly provided with traffic_manager')` |
| `SynchronousWorld.__init__` / 228 | `tm_previous_synchronous_mode is not None and type(tm_previous_synchronous_mode) is not bool` | `raise TypeError('tm_previous_synchronous_mode must be bool')` |
| `SynchronousWorld.__enter__` / 238 | `self._active` | `raise RuntimeError('SynchronousWorld is already active')` |
| `SynchronousWorld.__enter__` / 259 | `except Exception` | `raise` |
| `SynchronousWorld.tick` / 265 | `not self._active` | `raise RuntimeError('SynchronousWorld.tick() requires an active context')` |
| `SynchronousWorld.__exit__` / 289 | `exc_type is None and restore_error is not None` | `raise restore_error` |
| `CarlaSession.track_actor` / 309 | `not self._active` | `raise RuntimeError('track_actor() requires an active CarlaSession')` |
| `CarlaSession.tick` / 314 | `not self._active` | `raise RuntimeError('tick() requires an active CarlaSession')` |
| `CarlaSession.spawn_ego` / 320 | `not self._active` | `raise RuntimeError('spawn_ego() requires an active CarlaSession')` |
| `CarlaSession.attach_sensor` / 326 | `not self._active` | `raise RuntimeError('attach_sensor() requires an active CarlaSession')` |
| `CarlaSession.attach_sensor` / 328 | `parent is None` | `raise ValueError('parent must not be None')` |
| `CarlaSession.attach_sensor` / 334 | `not callable(listen)` | `raise TypeError('sensor actor must provide listen(callback)')` |
| `CarlaSession.attach_sensor` / 339 | `except Exception` | `raise` |
