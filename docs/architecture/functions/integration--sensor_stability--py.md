# sensor_stability：功能记录

上级模块：[模块说明](../modules/vehicle-entry.md) · 实现：[integration/sensor_stability.py](../../../integration/sensor_stability.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [一帧控制的实际顺序与执行值](control-frame.md)

## 功能职责与范围

Small, fail-fast CARLA sensor stability probe.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `SensorProbeResult.success: bool`；默认：`未在声明处设置`。
- `SensorProbeResult.reason: str`；默认：`未在声明处设置`。
- `SensorProbeResult.map_name: str`；默认：`未在声明处设置`。
- `SensorProbeResult.mode: str`；默认：`未在声明处设置`。
- `SensorProbeResult.profile: str`；默认：`未在声明处设置`。
- `SensorProbeResult.requested_frames: int`；默认：`未在声明处设置`。
- `SensorProbeResult.aligned_frames: int`；默认：`未在声明处设置`。
- `SensorProbeResult.callback_counts: dict[str, int]`；默认：`未在声明处设置`。
- `SensorProbeResult.frame_bounds: dict[str, tuple[int | None, int | None]]`；默认：`未在声明处设置`。
- `SensorProbeResult.invalid_callbacks: dict[str, int]`；默认：`未在声明处设置`。
- `SensorProbeResult.duration_s: float`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

<a id="fn-map-contract-name"></a>

### `map_contract_name`

源码位置：[integration/sensor_stability.py 第 37 行](../../../integration/sensor_stability.py#L37)。类型：`FunctionDef`。

```python
map_contract_name(name: str) -> str
```

Return the comparable leaf name of a CARLA map path.

<a id="fn-selected-sensor-specs"></a>

### `selected_sensor_specs`

源码位置：[integration/sensor_stability.py 第 42 行](../../../integration/sensor_stability.py#L42)。类型：`FunctionDef`。

```python
selected_sensor_specs(mode: str, profile: str) -> tuple[CarlaSensorSpec, ...]
```

Select the requested continuous sensor specs for a probe invocation.

<a id="fn-sensorframecounter"></a>

### `SensorFrameCounter`

源码位置：[integration/sensor_stability.py 第 56 行](../../../integration/sensor_stability.py#L56)。类型：`ClassDef`。

Thread-safe callback ledger used by the live probe and offline tests.

<a id="fn-sensorframecounter---init--"></a>

### `SensorFrameCounter.__init__`

源码位置：[integration/sensor_stability.py 第 59 行](../../../integration/sensor_stability.py#L59)。类型：`FunctionDef`。

```python
SensorFrameCounter.__init__(self, sensor_ids: Sequence[str]) -> None
```

sensor_ids必须非空、每项精确str且非空、不得重复；为每个ID建帧号set/非法计数，以Condition保护并发回调。重复帧去重，不统计原始回调次数。

<a id="fn-sensorframecounter-callback"></a>

### `SensorFrameCounter.callback`

源码位置：[integration/sensor_stability.py 第 70 行](../../../integration/sensor_stability.py#L70)。类型：`FunctionDef`。

```python
SensorFrameCounter.callback(self, sensor_id: str) -> Callable[[Any], None]
```

拒绝未登记ID（KeyError），返回绑定该ID的receive闭包供sensor.listen注册；不会立即读取帧。

<a id="fn-sensorframecounter-callback-receive"></a>

### `SensorFrameCounter.callback.receive`

源码位置：[integration/sensor_stability.py 第 74 行](../../../integration/sensor_stability.py#L74)。类型：`FunctionDef`。

```python
SensorFrameCounter.callback.receive(measurement: Any) -> None
```

在Condition锁内读取measurement.frame；仅精确int且>=0加入帧号set，否则增加invalid_callbacks，随后notify_all。bool视为非法；重复帧不会增加counts。

<a id="fn-sensorframecounter-wait-for-frame"></a>

### `SensorFrameCounter.wait_for_frame`

源码位置：[integration/sensor_stability.py 第 85 行](../../../integration/sensor_stability.py#L85)。类型：`FunctionDef`。

```python
SensorFrameCounter.wait_for_frame(self, sensor_ids: Sequence[str], frame: int, *, timeout_s: float) -> bool
```

要求请求ID均已注册、frame为非负int、timeout_s是有限非负int/float（bool拒绝）。使用monotonic墙钟等所有请求sensor恰好收到同一frame，满足True、截止False；不以更新的帧替代目标帧。

<a id="fn-sensorframecounter-counts"></a>

### `SensorFrameCounter.counts`

源码位置：[integration/sensor_stability.py 第 112 行](../../../integration/sensor_stability.py#L112)。类型：`FunctionDef`。

```python
SensorFrameCounter.counts(self) -> dict[str, int]
```

锁内返回每sensor唯一合法帧号数量的新dict，不是总回调次数；无数据为0。

<a id="fn-sensorframecounter-frame-bounds"></a>

### `SensorFrameCounter.frame_bounds`

源码位置：[integration/sensor_stability.py 第 119 行](../../../integration/sensor_stability.py#L119)。类型：`FunctionDef`。

```python
SensorFrameCounter.frame_bounds(self) -> dict[str, tuple[int | None, int | None]]
```

锁内返回每sensor的(min_frame,max_frame)，未收到合法帧时(None,None)；不证明区间中每帧连续存在。

<a id="fn-sensorframecounter-invalid-callbacks"></a>

### `SensorFrameCounter.invalid_callbacks`

源码位置：[integration/sensor_stability.py 第 129 行](../../../integration/sensor_stability.py#L129)。类型：`FunctionDef`。

```python
SensorFrameCounter.invalid_callbacks(self) -> dict[str, int]
```

锁内复制各sensor非法frame回调计数；与counts分开，不清零累计值。

<a id="fn-sensorproberesult"></a>

### `SensorProbeResult`

源码位置：[integration/sensor_stability.py 第 135 行](../../../integration/sensor_stability.py#L135)。类型：`ClassDef`。

冻结结果含success/reason、地图/mode/profile、请求/对齐帧数、唯一帧数量/范围/非法回调及墙钟duration_s。callback统计包含启动阶段，aligned_frames是测量阶段，不应直接相等比较。

<a id="fn-sensorproberesult-to-json"></a>

### `SensorProbeResult.to_json`

源码位置：[integration/sensor_stability.py 第 148 行](../../../integration/sensor_stability.py#L148)。类型：`FunctionDef`。

```python
SensorProbeResult.to_json(self) -> str
```

asdict后以ensure_ascii=False、sort_keys=True编码JSON字符串，不保存文件；frame_bounds tuple在JSON中成为数组。

<a id="fn--make-transform"></a>

### `_make_transform`

源码位置：[integration/sensor_stability.py 第 152 行](../../../integration/sensor_stability.py#L152)。类型：`FunctionDef`。

```python
_make_transform(carla_api: Any, spec: CarlaSensorSpec) -> Any
```

将CarlaSensorSpec.mount位置m、pitch/yaw/roll度原样构造成CARLA Location/Rotation/Transform；不做坐标轴翻转或单位换算。

<a id="fn--configure-blueprint"></a>

### `_configure_blueprint`

源码位置：[integration/sensor_stability.py 第 164 行](../../../integration/sensor_stability.py#L164)。类型：`FunctionDef`。

```python
_configure_blueprint(world: Any, spec: CarlaSensorSpec) -> Any
```

按spec.blueprint_id查world蓝图库，缺失LookupError；若支持has_attribute则拒绝未知属性，再逐项set_attribute。返回已修改蓝图，CARLA查找/赋值异常可向上传播。

<a id="fn--spawn-ego"></a>

### `_spawn_ego`

源码位置：[integration/sensor_stability.py 第 175 行](../../../integration/sensor_stability.py#L175)。类型：`FunctionDef`。

```python
_spawn_ego(session: CarlaSession, world: Any, spawn_index: int) -> Any
```

优先vehicle.*model3*，否则任意vehicle首蓝图，role_name可用时设sensor_probe。spawn_index对出生点数取模后循环尝试，成功交session.track_actor管理并关闭autopilot。无蓝图/出生点或全部占用则RuntimeError。

<a id="fn-run-sensor-probe"></a>

### `run_sensor_probe`

源码位置：[integration/sensor_stability.py 第 201 行](../../../integration/sensor_stability.py#L201)。类型：`FunctionDef`。

```python
run_sensor_probe(*, carla_api: Any, host: str='127.0.0.1', port: int=2000, timeout_s: float=10.0, sensor_timeout_s: float=2.0, fixed_delta_s: float=0.05, mode: str='rgb', profile: str='low', frames: int=100, startup_frames: int=10, spawn_index: int=0, expected_map: str | None=None, minimum_wall_duration_s: float=0.0) -> SensorProbeResult
```

Run a live probe against the currently loaded CARLA world.

<a id="fn-build-argument-parser"></a>

### `build_argument_parser`

源码位置：[integration/sensor_stability.py 第 350 行](../../../integration/sensor_stability.py#L350)。类型：`FunctionDef`。

```python
build_argument_parser() -> argparse.ArgumentParser
```

声明probe专用CLI：host127.0.0.1/port2000、连接10s、sensor2s、步长0.05s、rgb/low、测量100帧、startup10次、spawn0、最短墙钟0。只是创建parser，不连接CARLA；参数名与主runner并不完全一致（如--timeout vs --timeout-s）。

<a id="fn-main"></a>

### `main`

源码位置：[integration/sensor_stability.py 第 372 行](../../../integration/sensor_stability.py#L372)。类型：`FunctionDef`。

```python
main(argv: Sequence[str] | None=None) -> int
```

解析argv后导入carla并调用run_sensor_probe；正常success返回0、正常失败返回1，导入/执行异常打印probe error JSON并返回2。argparse解析在try外，参数错误按argparse自身退出；脚本入口将返回值交SystemExit。

## 内部调用与异常路径

- `map_contract_name` 调用：`str`, `str(name).replace`, `str(name).replace('\\', '/').rstrip`, `str(name).replace('\\', '/').rstrip('/').split`.
- `selected_sensor_specs` 调用：`ValueError`, `sensor_specs_for_profile`, `str`, `str(mode).strip`, `str(mode).strip().lower`, `tuple`.
- `_make_transform` 调用：`carla_api.Location`, `carla_api.Rotation`, `carla_api.Transform`.
- `_configure_blueprint` 调用：`LookupError`, `blueprint.has_attribute`, `blueprint.set_attribute`, `hasattr`, `spec.attributes.items`, `world.get_blueprint_library`, `world.get_blueprint_library().find`.
- `_spawn_ego` 调用：`RuntimeError`, `blueprint.has_attribute`, `blueprint.set_attribute`, `callable`, `getattr`, `hasattr`, `len`, `library.filter`, `list`, `range`, `session.track_actor`, `set_autopilot`, `world.get_blueprint_library`, `world.get_map`, `world.get_map().get_spawn_points`, `world.try_spawn_actor`.
- `run_sensor_probe` 调用：`CarlaSession`, `RuntimeError`, `SensorFrameCounter`, `SensorProbeResult`, `ValueError`, `_configure_blueprint`, `_make_transform`, `_spawn_ego`, `carla_api.Client`, `client.get_world`, `client.set_timeout`, `counter.callback`, `counter.counts`, `counter.frame_bounds`, `counter.invalid_callbacks`, `counter.wait_for_frame`, `float`, `int`, `map_contract_name`, `map_contract_name(expected_map).lower`, `map_contract_name(map_name).lower`, `math.isfinite`, `max`, `min`, `print`, `result.to_json`, `round`, `selected_sensor_specs`, `sensor.listen`, `session.tick`, `session.track_actor`, `time.monotonic`, `tuple`, `type`, `world.get_map`, `world.spawn_actor`.
- `build_argument_parser` 调用：`argparse.ArgumentParser`, `parser.add_argument`, `tuple`.
- `main` 调用：`build_argument_parser`, `build_argument_parser().parse_args`, `json.dumps`, `print`, `run_sensor_probe`, `str`, `type`.
- `__init__` 调用：`ValueError`, `any`, `len`, `set`, `threading.Condition`, `tuple`, `type`.
- `callback` 调用：`KeyError`, `getattr`, `self._condition.notify_all`, `self._frames[sensor_id].add`, `type`.
- `wait_for_frame` 调用：`KeyError`, `ValueError`, `all`, `any`, `float`, `math.isfinite`, `self._condition.wait`, `time.monotonic`, `tuple`, `type`.
- `counts` 调用：`len`.
- `frame_bounds` 调用：`max`, `min`, `self._frames.items`.
- `invalid_callbacks` 调用：`dict`.
- `to_json` 调用：`asdict`, `json.dumps`.
- `receive` 调用：`getattr`, `self._condition.notify_all`, `self._frames[sensor_id].add`, `type`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 62 行：`ValueError('sensor_ids must contain non-empty strings')`。
- `__init__`，第 64 行：`ValueError('sensor_ids must be unique')`。
- `_configure_blueprint`，第 167 行：`LookupError(f'CARLA blueprint not found: {spec.blueprint_id}')`。
- `_configure_blueprint`，第 170 行：`LookupError(f'{spec.blueprint_id} does not support attribute {name}')`。
- `_spawn_ego`，第 181 行：`RuntimeError('no vehicle blueprint is available')`。
- `_spawn_ego`，第 187 行：`RuntimeError('current map has no vehicle spawn points')`。
- `_spawn_ego`，第 198 行：`RuntimeError('unable to spawn ego at any current-map spawn point')`。
- `callback`，第 72 行：`KeyError(sensor_id)`。
- `run_sensor_probe`，第 219 行：`ValueError('frames must be a positive integer')`。
- `run_sensor_probe`，第 221 行：`ValueError('startup_frames must be a non-negative integer')`。
- `run_sensor_probe`，第 227 行：`ValueError('minimum_wall_duration_s must be finite and non-negative')`。
- `run_sensor_probe`，第 241 行：`RuntimeError(f'current map is {map_name!r}, expected {expected_map!r}; probe will not call load_world')`。
- `selected_sensor_specs`，第 48 行：`ValueError(f'unknown sensor mode: {mode!r}')`。
- `selected_sensor_specs`，第 53 行：`ValueError(f'sensor profile {profile!r} is missing {error.args[0]!r}')`。
- `wait_for_frame`，第 94 行：`KeyError('unknown sensor id')`。
- `wait_for_frame`，第 96 行：`ValueError('frame must be a non-negative integer')`。
- `wait_for_frame`，第 102 行：`ValueError('timeout_s must be finite and non-negative')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 352 行：`parser.add_argument('--host', default='127.0.0.1')`。
- 第 353 行：`parser.add_argument('--port', type=int, default=2000)`。
- 第 354 行：`parser.add_argument('--timeout', type=float, default=10.0)`。
- 第 355 行：`parser.add_argument('--sensor-timeout', type=float, default=2.0)`。
- 第 356 行：`parser.add_argument('--fixed-delta', type=float, default=0.05)`。
- 第 357 行：`parser.add_argument('--sensor', choices=tuple(SENSOR_MODES), default='rgb')`。
- 第 358 行：`parser.add_argument('--profile', choices=('default', 'low'), default='low')`。
- 第 359 行：`parser.add_argument('--frames', type=int, default=100)`。
- 第 360 行：`parser.add_argument('--startup-frames', type=int, default=10)`。
- 第 361 行：`parser.add_argument('--spawn-index', type=int, default=0)`。
- 第 362 行：`parser.add_argument('--expected-map')`。
- 第 363 行：`parser.add_argument('--minimum-wall-seconds', type=float, default=0.0, help='continue after the frame target until this measured wall time is reached')`。

## 上下游与关联验证

静态导入的项目内实现：

- [car_control_A/__init__.py](../../../car_control_A/__init__.py)
- [integration/carla_perception.py](../../../integration/carla_perception.py)

静态 import 消费者（含测试）：

- [integration/tests/test_sensor_stability.py](../../../integration/tests/test_sensor_stability.py)
- [tools/check_sensor_stability.py](../../../tools/check_sensor_stability.py)
- [tools/run_long_stability.py](../../../tools/run_long_stability.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-entry.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-integration-sensor-stability-py"></a>

### `integration/sensor_stability.py`

来源 SHA256：`7364fa54eed0dfef5af9db7ebea6a07ab337450229f6ddae00eab8b83da77ba9`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `SensorProbeResult.success` | `bool` | `无声明默认；构造/赋值方提供` |
| `SensorProbeResult.reason` | `str` | `无声明默认；构造/赋值方提供` |
| `SensorProbeResult.map_name` | `str` | `无声明默认；构造/赋值方提供` |
| `SensorProbeResult.mode` | `str` | `无声明默认；构造/赋值方提供` |
| `SensorProbeResult.profile` | `str` | `无声明默认；构造/赋值方提供` |
| `SensorProbeResult.requested_frames` | `int` | `无声明默认；构造/赋值方提供` |
| `SensorProbeResult.aligned_frames` | `int` | `无声明默认；构造/赋值方提供` |
| `SensorProbeResult.callback_counts` | `dict[str, int]` | `无声明默认；构造/赋值方提供` |
| `SensorProbeResult.frame_bounds` | `dict[str, tuple[int &#124; None, int &#124; None]]` | `无声明默认；构造/赋值方提供` |
| `SensorProbeResult.invalid_callbacks` | `dict[str, int]` | `无声明默认；构造/赋值方提供` |
| `SensorProbeResult.duration_s` | `float` | `无声明默认；构造/赋值方提供` |

CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 352 | `'--host'` | `default='127.0.0.1'` |
| 353 | `'--port'` | `type=int; default=2000` |
| 354 | `'--timeout'` | `type=float; default=10.0` |
| 355 | `'--sensor-timeout'` | `type=float; default=2.0` |
| 356 | `'--fixed-delta'` | `type=float; default=0.05` |
| 357 | `'--sensor'` | `choices=tuple(SENSOR_MODES); default='rgb'` |
| 358 | `'--profile'` | `choices=('default', 'low'); default='low'` |
| 359 | `'--frames'` | `type=int; default=100` |
| 360 | `'--startup-frames'` | `type=int; default=10` |
| 361 | `'--spawn-index'` | `type=int; default=0` |
| 362 | `'--expected-map'` | `` |
| 363 | `'--minimum-wall-seconds'` | `type=float; default=0.0; help='continue after the frame target until this measured wall time is reached'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `selected_sensor_specs` / 48 | `except KeyError` | `raise ValueError(f'unknown sensor mode: {mode!r}') from error` |
| `selected_sensor_specs` / 53 | `except KeyError` | `raise ValueError(f'sensor profile {profile!r} is missing {error.args[0]!r}') from error` |
| `SensorFrameCounter.__init__` / 62 | `not ids or any((type(sensor_id) is not str or not sensor_id for sensor_id in ids))` | `raise ValueError('sensor_ids must contain non-empty strings')` |
| `SensorFrameCounter.__init__` / 64 | `len(set(ids)) != len(ids)` | `raise ValueError('sensor_ids must be unique')` |
| `SensorFrameCounter.callback` / 72 | `sensor_id not in self._frames` | `raise KeyError(sensor_id)` |
| `SensorFrameCounter.wait_for_frame` / 94 | `any((sensor_id not in self._frames for sensor_id in requested))` | `raise KeyError('unknown sensor id')` |
| `SensorFrameCounter.wait_for_frame` / 96 | `type(frame) is not int or frame < 0` | `raise ValueError('frame must be a non-negative integer')` |
| `SensorFrameCounter.wait_for_frame` / 102 | `type(timeout_s) not in (int, float) or not math.isfinite(float(timeout_s)) or timeout_s < 0` | `raise ValueError('timeout_s must be finite and non-negative')` |
| `_configure_blueprint` / 167 | `blueprint is None` | `raise LookupError(f'CARLA blueprint not found: {spec.blueprint_id}')` |
| `_configure_blueprint` / 170 | `hasattr(blueprint, 'has_attribute') and (not blueprint.has_attribute(name))` | `raise LookupError(f'{spec.blueprint_id} does not support attribute {name}')` |
| `_spawn_ego` / 181 | `not candidates` | `raise RuntimeError('no vehicle blueprint is available')` |
| `_spawn_ego` / 187 | `not spawn_points` | `raise RuntimeError('current map has no vehicle spawn points')` |
| `_spawn_ego` / 198 | `本地无直接if；检查上下文` | `raise RuntimeError('unable to spawn ego at any current-map spawn point')` |
| `run_sensor_probe` / 219 | `type(frames) is not int or frames < 1` | `raise ValueError('frames must be a positive integer')` |
| `run_sensor_probe` / 221 | `type(startup_frames) is not int or startup_frames < 0` | `raise ValueError('startup_frames must be a non-negative integer')` |
| `run_sensor_probe` / 227 | `type(minimum_wall_duration_s) not in (int, float) or not math.isfinite(float(minimum_wall_duration_s)) or minimum_wall_duration_s < 0` | `raise ValueError('minimum_wall_duration_s must be finite and non-negative')` |
| `run_sensor_probe` / 241 | `expected_map and map_contract_name(map_name).lower() != map_contract_name(expected_map).lower()` | `raise RuntimeError(f'current map is {map_name!r}, expected {expected_map!r}; probe will not call load_world')` |

## 逐行核查：启动失败的success误报（M01-01）

run_sensor_probe预热最多startup_frames次，要求min(2,startup_frames)连续精确帧。预热失败会break第一段while并保留失败reason；第二段测量while因warmup_streak不足直接不进入，却执行while的else，将success设True。

2026-09-20使用实际函数、模拟CARLA/session、wait_for_frame固定False复现：frames=3/startup_frames=1，输出success=True、aligned_frames=0，reason为startup did not produce...。没有连接CARLA或修改代码。说明success字段当前不能单独作采集放行依据。修复位置是测量循环成功条件；回归应覆盖预热失败、测量超时、完整成功、最短墙钟窗口四种情况，当前只记录。

map_contract_name会统一反斜杠/去末尾斜杠再取末段，但不去_Opt；与主runner地图合同helper并不相同。selected_sensor_specs只选择mode对应ID并确保profile中存在，不证明传感器已运行。
