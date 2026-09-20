# scenario_runner_agent：功能记录

上级模块：[模块说明](../modules/vehicle-scenarios.md) · 实现：[integration/scenario_runner_agent.py](../../../integration/scenario_runner_agent.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [场景触发、车辆行为与验收分离](scenario-evidence-contract.md)

## 功能职责与范围

ScenarioRunner 0.9.16 ``--agent`` adapter for evaluator-owned scenarios.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `OfficialAgentConfig.target_speed_mps: float`；默认：`4.0`。
- `OfficialAgentConfig.obstacle_stop_m: float`；默认：`6.0`。
- `OfficialAgentConfig.lidar_corridor_half_width_m: float`；默认：`1.4`。
- `OfficialAgentConfig.route_lookahead_points: int`；默认：`5`。
- `OfficialAgentConfig.command_file: Path | None`；默认：`None`。
- `OfficialAgentConfig.qwen_profile: str | None`；默认：`None`。
- `OfficialAgentConfig.qwen_service_url: str | None`；默认：`None`。
- `OfficialAgentConfig.qwen_voice_command: str`；默认：`'Follow the route safely.'`。
- `OfficialSensorFrame.speed_mps: float`；默认：`未在声明处设置`。
- `OfficialSensorFrame.compass_rad: float`；默认：`未在声明处设置`。
- `OfficialSensorFrame.latitude: float`；默认：`未在声明处设置`。
- `OfficialSensorFrame.longitude: float`；默认：`未在声明处设置`。
- `OfficialSensorFrame.lidar_xyz: np.ndarray`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

### `get_entry_point`

源码位置：[integration/scenario_runner_agent.py 第 41 行](../../../integration/scenario_runner_agent.py#L41)。类型：`FunctionDef`。

```python
get_entry_point() -> str
```

Compatibility hook used by CARLA leaderboard-style loaders.

### `OfficialAgentConfig`

源码位置：[integration/scenario_runner_agent.py 第 47 行](../../../integration/scenario_runner_agent.py#L47)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `OfficialAgentConfig.load`

源码位置：[integration/scenario_runner_agent.py 第 58 行](../../../integration/scenario_runner_agent.py#L58)。类型：`FunctionDef`。

```python
OfficialAgentConfig.load(cls, path: str | Path | None) -> 'OfficialAgentConfig'
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `OfficialSensorFrame`

源码位置：[integration/scenario_runner_agent.py 第 118 行](../../../integration/scenario_runner_agent.py#L118)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `OfficialAgentCore`

源码位置：[integration/scenario_runner_agent.py 第 126 行](../../../integration/scenario_runner_agent.py#L126)。类型：`ClassDef`。

CARLA-independent route following and fail-closed obstacle arbitration.

### `OfficialAgentCore.__init__`

源码位置：[integration/scenario_runner_agent.py 第 129 行](../../../integration/scenario_runner_agent.py#L129)。类型：`FunctionDef`。

```python
OfficialAgentCore.__init__(self, config: OfficialAgentConfig) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `OfficialAgentCore.step`

源码位置：[integration/scenario_runner_agent.py 第 134 行](../../../integration/scenario_runner_agent.py#L134)。类型：`FunctionDef`。

```python
OfficialAgentCore.step(self, frame: OfficialSensorFrame, global_plan: Sequence[tuple[Mapping[str, float], object]], *, high_level_command: Mapping[str, object] | None=None, qwen_error: BaseException | None=None) -> tuple[float, float, float, str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `OfficialAgentCore._target_speed`

源码位置：[integration/scenario_runner_agent.py 第 186 行](../../../integration/scenario_runner_agent.py#L186)。类型：`FunctionDef`。

```python
OfficialAgentCore._target_speed(self, *, high_level_command: Mapping[str, object] | None, qwen_error: BaseException | None) -> tuple[float, bool]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioRunnerAgent`

源码位置：[integration/scenario_runner_agent.py 第 256 行](../../../integration/scenario_runner_agent.py#L256)。类型：`ClassDef`。

Concrete agent loaded by ``scenario_runner.py --agent``.

### `ScenarioRunnerAgent.setup`

源码位置：[integration/scenario_runner_agent.py 第 261 行](../../../integration/scenario_runner_agent.py#L261)。类型：`FunctionDef`。

```python
ScenarioRunnerAgent.setup(self, path_to_conf_file: str) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioRunnerAgent.sensors`

源码位置：[integration/scenario_runner_agent.py 第 277 行](../../../integration/scenario_runner_agent.py#L277)。类型：`FunctionDef`。

```python
ScenarioRunnerAgent.sensors(self) -> list[dict[str, object]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioRunnerAgent.run_step`

源码位置：[integration/scenario_runner_agent.py 第 296 行](../../../integration/scenario_runner_agent.py#L296)。类型：`FunctionDef`。

```python
ScenarioRunnerAgent.run_step(self, input_data: Mapping[str, tuple[int, Any]], timestamp: float) -> Any
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioRunnerAgent._qwen_high_level_command`

源码位置：[integration/scenario_runner_agent.py 第 326 行](../../../integration/scenario_runner_agent.py#L326)。类型：`FunctionDef`。

```python
ScenarioRunnerAgent._qwen_high_level_command(self, frame: OfficialSensorFrame, timestamp: float) -> Mapping[str, object]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioRunnerAgent._sensor_frame`

源码位置：[integration/scenario_runner_agent.py 第 356 行](../../../integration/scenario_runner_agent.py#L356)。类型：`FunctionDef`。

```python
ScenarioRunnerAgent._sensor_frame(self, input_data: Mapping[str, tuple[int, Any]], timestamp: float) -> OfficialSensorFrame
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_front_lidar_distance`

源码位置：[integration/scenario_runner_agent.py 第 404 行](../../../integration/scenario_runner_agent.py#L404)。类型：`FunctionDef`。

```python
_front_lidar_distance(points: np.ndarray, *, corridor_half_width_m: float) -> float | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_route_steer`

源码位置：[integration/scenario_runner_agent.py 第 418 行](../../../integration/scenario_runner_agent.py#L418)。类型：`FunctionDef`。

```python
_route_steer(latitude: float, longitude: float, compass_rad: float, global_plan: Sequence[tuple[Mapping[str, float], object]], lookahead_points: int) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_route_steer.distance_sq`

源码位置：[integration/scenario_runner_agent.py 第 427 行](../../../integration/scenario_runner_agent.py#L427)。类型：`FunctionDef`。

```python
_route_steer.distance_sq(item: tuple[Mapping[str, float], object]) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_route_bearing`

源码位置：[integration/scenario_runner_agent.py 第 436 行](../../../integration/scenario_runner_agent.py#L436)。类型：`FunctionDef`。

```python
_route_bearing(latitude: float, longitude: float, global_plan: Sequence[tuple[Mapping[str, float], object]], lookahead_points: int) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_gps_offset_m`

源码位置：[integration/scenario_runner_agent.py 第 454 行](../../../integration/scenario_runner_agent.py#L454)。类型：`FunctionDef`。

```python
_gps_offset_m(latitude: float, longitude: float, target_latitude: float, target_longitude: float) -> tuple[float, float]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_finite`

源码位置：[integration/scenario_runner_agent.py 第 470 行](../../../integration/scenario_runner_agent.py#L470)。类型：`FunctionDef`。

```python
_finite(value: object, name: str, minimum: float) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_front_lidar_distance` 调用：`float`, `np.abs`, `np.any`, `np.isfinite`, `np.isfinite(points).all`, `np.min`.
- `_route_steer` 调用：`_route_bearing`, `distance_sq`, `float`, `len`, `math.atan2`, `math.cos`, `math.sin`, `max`, `min`, `range`.
- `_route_bearing` 调用：`_gps_offset_m`, `abs`, `float`, `len`, `math.atan2`, `min`.
- `_gps_offset_m` 调用：`math.cos`, `math.radians`.
- `_finite` 调用：`TypeError`, `ValueError`, `float`, `isinstance`, `math.isfinite`, `type`.
- `load` 调用：`(source.parent / candidate).resolve`, `Path`, `Path(command_file).expanduser`, `Path(path).expanduser`, `Path(path).expanduser().resolve`, `TypeError`, `ValueError`, `_finite`, `candidate.is_absolute`, `candidate.resolve`, `cls`, `command_file.strip`, `isinstance`, `json.loads`, `payload.get`, `qwen_profile.strip`, `qwen_service_url.strip`, `qwen_voice_command.strip`, `set`, `set(payload).difference`, `sorted`, `source.read_text`, `str`, `str(path).strip`, `type`.
- `__init__` 调用：`SafetySupervisor`, `self.setup`.
- `step` 调用：`_front_lidar_distance`, `_route_steer`, `max`, `min`, `self._target_speed`, `self.safety.arbitrate`.
- `_target_speed` 调用：`','.join`, `TypeError`, `ValueError`, `_finite`, `float`, `high_level_command.get`, `isinstance`, `json.loads`, `min`, `parameters.get`, `payload.get`, `sorted`, `source.read_text`, `str`, `str(high_level_command.get('action', '')).upper`, `str(payload.get('intent', payload.get('action', 'KEEP_LANE'))).upper`, `str(payload.get('status', 'valid')).lower`, `type`, `{'throttle', 'brake', 'steer'}.intersection`.
- `setup` 调用：`OfficialAgentConfig.load`, `OfficialAgentCore`, `QwenServiceClient`, `resolve_qwen_profile`.
- `run_step` 调用：`SimpleNamespace`, `carla.VehicleControl`, `getattr`, `self._qwen_high_level_command`, `self._sensor_frame`, `self.core.step`, `tuple`, `type`.
- `_qwen_high_level_command` 调用：`QwenInputContext`, `RuntimeError`, `_front_lidar_distance`, `float`, `int`, `max`, `self.qwen_client.infer`.
- `_sensor_frame` 调用：`OfficialSensorFrame`, `ValueError`, `_gps_offset_m`, `_route_bearing`, `all`, `float`, `getattr`, `math.atan2`, `math.hypot`, `math.isfinite`, `np.asarray`, `np.asarray(input_data['gnss'][1], dtype=np.float64).reshape`, `sorted`, `tuple`.
- `distance_sq` 调用：`float`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_finite`，第 472 行：`TypeError(f'{name} must be numeric')`。
- `_finite`，第 475 行：`ValueError(f'{name} must be finite and >= {minimum}')`。
- `_qwen_high_level_command`，第 332 行：`RuntimeError('Qwen client is unavailable in offline command-file mode')`。
- `_sensor_frame`，第 363 行：`ValueError(f'official sensor frame missing: {sorted(missing)}')`。
- `_sensor_frame`，第 367 行：`ValueError('official sensor payload has an invalid shape')`。
- `_sensor_frame`，第 370 行：`ValueError('official sensor payload contains non-finite navigation data')`。
- `_target_speed`，第 199 行：`ValueError('low-level command fields are forbidden: ' + ','.join(sorted(forbidden)))`。
- `_target_speed`，第 204 行：`ValueError('Qwen command requires confirmation')`。
- `_target_speed`，第 217 行：`ValueError(f'unsupported Qwen action: {action}')`。
- `_target_speed`，第 227 行：`TypeError('command root must be an object')`。
- `_target_speed`，第 230 行：`ValueError('low-level command fields are forbidden: ' + ','.join(sorted(forbidden)))`。
- `_target_speed`，第 236 行：`ValueError('command is invalid, low-confidence, or requires confirmation')`。
- `_target_speed`，第 243 行：`TypeError('command parameters must be an object')`。
- `_target_speed`，第 249 行：`ValueError(f'unsupported official command intent: {intent}')`。
- `load`，第 64 行：`TypeError('ScenarioRunner agent config root must be an object')`。
- `load`，第 72 行：`ValueError(f'unsupported ScenarioRunner agent config fields: {sorted(unknown)}')`。
- `load`，第 74 行：`ValueError("ScenarioRunner agent config schema_version must be '1.0'")`。
- `load`，第 84 行：`ValueError('route_lookahead_points must be a positive integer')`。
- `load`，第 89 行：`ValueError('command_file must be a non-empty path')`。
- `load`，第 94 行：`ValueError('qwen_profile must be a non-empty string')`。
- `load`，第 99 行：`ValueError('qwen_service_url must be a non-empty URL')`。
- `load`，第 102 行：`ValueError('qwen_voice_command must be a non-empty string')`。
- `load`，第 104 行：`ValueError('command_file is offline/test-only and cannot be combined with qwen_service_url')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_D/__init__.py](../../../car_control_D/__init__.py)
- [integration/qwen_boundary.py](../../../integration/qwen_boundary.py)
- [integration/qwen_profiles.py](../../../integration/qwen_profiles.py)
- [integration/qwen_service_client.py](../../../integration/qwen_service_client.py)

静态 import 消费者（含测试）：

- [integration/tests/test_official_scenario_runner.py](../../../integration/tests/test_official_scenario_runner.py)
- [integration/tests/test_unseen_scenario_generalization.py](../../../integration/tests/test_unseen_scenario_generalization.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-scenarios.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `integration/scenario_runner_agent.py`

来源 SHA256：`11152bd983e79c83cda96d9cc8d23abbe98389fd9cc9330b42fc821116d3d9a4`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `OfficialAgentConfig.target_speed_mps` | `float` | `4.0` |
| `OfficialAgentConfig.obstacle_stop_m` | `float` | `6.0` |
| `OfficialAgentConfig.lidar_corridor_half_width_m` | `float` | `1.4` |
| `OfficialAgentConfig.route_lookahead_points` | `int` | `5` |
| `OfficialAgentConfig.command_file` | `Path &#124; None` | `None` |
| `OfficialAgentConfig.qwen_profile` | `str &#124; None` | `None` |
| `OfficialAgentConfig.qwen_service_url` | `str &#124; None` | `None` |
| `OfficialAgentConfig.qwen_voice_command` | `str` | `'Follow the route safely.'` |
| `OfficialSensorFrame.speed_mps` | `float` | `无声明默认；构造/赋值方提供` |
| `OfficialSensorFrame.compass_rad` | `float` | `无声明默认；构造/赋值方提供` |
| `OfficialSensorFrame.latitude` | `float` | `无声明默认；构造/赋值方提供` |
| `OfficialSensorFrame.longitude` | `float` | `无声明默认；构造/赋值方提供` |
| `OfficialSensorFrame.lidar_xyz` | `np.ndarray` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `OfficialAgentConfig.load` / 64 | `type(payload) is not dict` | `raise TypeError('ScenarioRunner agent config root must be an object')` |
| `OfficialAgentConfig.load` / 72 | `unknown` | `raise ValueError(f'unsupported ScenarioRunner agent config fields: {sorted(unknown)}')` |
| `OfficialAgentConfig.load` / 74 | `payload.get('schema_version', '1.0') != '1.0'` | `raise ValueError("ScenarioRunner agent config schema_version must be '1.0'")` |
| `OfficialAgentConfig.load` / 84 | `type(lookahead) is not int or isinstance(lookahead, bool) or lookahead < 1` | `raise ValueError('route_lookahead_points must be a positive integer')` |
| `OfficialAgentConfig.load` / 89 | `command_file is not None AND type(command_file) is not str or not command_file.strip()` | `raise ValueError('command_file must be a non-empty path')` |
| `OfficialAgentConfig.load` / 94 | `qwen_profile is not None and (type(qwen_profile) is not str or not qwen_profile.strip())` | `raise ValueError('qwen_profile must be a non-empty string')` |
| `OfficialAgentConfig.load` / 99 | `qwen_service_url is not None and (type(qwen_service_url) is not str or not qwen_service_url.strip())` | `raise ValueError('qwen_service_url must be a non-empty URL')` |
| `OfficialAgentConfig.load` / 102 | `type(qwen_voice_command) is not str or not qwen_voice_command.strip()` | `raise ValueError('qwen_voice_command must be a non-empty string')` |
| `OfficialAgentConfig.load` / 104 | `command_path is not None and qwen_service_url is not None` | `raise ValueError('command_file is offline/test-only and cannot be combined with qwen_service_url')` |
| `OfficialAgentCore._target_speed` / 199 | `high_level_command is not None AND forbidden` | `raise ValueError('low-level command fields are forbidden: ' + ','.join(sorted(forbidden)))` |
| `OfficialAgentCore._target_speed` / 204 | `high_level_command is not None AND high_level_command.get('requires_confirmation') is True` | `raise ValueError('Qwen command requires confirmation')` |
| `OfficialAgentCore._target_speed` / 217 | `high_level_command is not None` | `raise ValueError(f'unsupported Qwen action: {action}')` |
| `OfficialAgentCore._target_speed` / 227 | `type(payload) is not dict` | `raise TypeError('command root must be an object')` |
| `OfficialAgentCore._target_speed` / 230 | `forbidden` | `raise ValueError('low-level command fields are forbidden: ' + ','.join(sorted(forbidden)))` |
| `OfficialAgentCore._target_speed` / 236 | `status != 'valid' or confidence < 0.8 or payload.get('confirm_required') is True` | `raise ValueError('command is invalid, low-confidence, or requires confirmation')` |
| `OfficialAgentCore._target_speed` / 243 | `intent == 'SET_SPEED' AND not isinstance(parameters, Mapping)` | `raise TypeError('command parameters must be an object')` |
| `OfficialAgentCore._target_speed` / 249 | `intent not in {'KEEP_LANE', 'FOLLOW_ROUTE', 'START', 'FORWARD'}` | `raise ValueError(f'unsupported official command intent: {intent}')` |
| `ScenarioRunnerAgent._qwen_high_level_command` / 332 | `self.qwen_client is None` | `raise RuntimeError('Qwen client is unavailable in offline command-file mode')` |
| `ScenarioRunnerAgent._sensor_frame` / 363 | `missing` | `raise ValueError(f'official sensor frame missing: {sorted(missing)}')` |
| `ScenarioRunnerAgent._sensor_frame` / 367 | `gnss.size < 2 or lidar.ndim != 2 or lidar.shape[1] < 3` | `raise ValueError('official sensor payload has an invalid shape')` |
| `ScenarioRunnerAgent._sensor_frame` / 370 | `not all((math.isfinite(value) for value in (timestamp, latitude, longitude)))` | `raise ValueError('official sensor payload contains non-finite navigation data')` |
| `_finite` / 472 | `type(value) not in (int, float) or isinstance(value, bool)` | `raise TypeError(f'{name} must be numeric')` |
| `_finite` / 475 | `not math.isfinite(result) or result < minimum` | `raise ValueError(f'{name} must be finite and >= {minimum}')` |

### integration/scenario_runner_agent.py 数值检查调用

这里保留校验函数的minimum/positive等参数原文；实际可达性由调用分支决定，函数本体异常仍需看对应helper。

| 行 | 校验调用 |
|---|---|
| 75 | `_finite(payload.get('target_speed_mps', 4.0), 'target_speed_mps', 0.0)` |
| 76 | `_finite(payload.get('obstacle_stop_m', 6.0), 'obstacle_stop_m', 0.1)` |
| 77 | `_finite(payload.get('lidar_corridor_half_width_m', 1.4), 'lidar_corridor_half_width_m', 0.1)` |
| 247 | `_finite(value, 'command target speed', 0.0)` |
| 208 | `_finite(high_level_command.get('target_speed_mps'), 'Qwen target speed', 0.0)` |
