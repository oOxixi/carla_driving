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

冻结的外部 ScenarioRunner agent 配置：基础目标速度、LiDAR停车距离/走廊半宽、路线前视点数，以及互斥的离线 command file 或在线 Qwen profile/service/固定 voice command。默认速度4 m/s、停车6 m，不等同仓库主 runner 的 DrivingPolicy。

### `OfficialAgentConfig.load`

源码位置：[integration/scenario_runner_agent.py 第 58 行](../../../integration/scenario_runner_agent.py#L58)。类型：`FunctionDef`。

```python
OfficialAgentConfig.load(cls, path: str | Path | None) -> 'OfficialAgentConfig'
```

空路径返回默认配置；否则读取 schema 1.0 JSON，拒绝未知字段，验证三个有限下界数、正整数前视点、路径/字符串，并把相对 command_file 解析到配置文件目录。离线 command file 与 qwen_service_url 禁止并用；文件存在性在每帧读取时才暴露。

### `OfficialSensorFrame`

源码位置：[integration/scenario_runner_agent.py 第 118 行](../../../integration/scenario_runner_agent.py#L118)。类型：`ClassDef`。

冻结的 agent 内部帧，只含估算速度 m/s、航向弧度、经纬度和 LiDAR XYZ ndarray。虽然 sensors 声明 front_rgb，此结构不携带 RGB、帧号或传感同步状态。

### `OfficialAgentCore`

源码位置：[integration/scenario_runner_agent.py 第 126 行](../../../integration/scenario_runner_agent.py#L126)。类型：`ClassDef`。

CARLA-independent route following and fail-closed obstacle arbitration.

### `OfficialAgentCore.__init__`

源码位置：[integration/scenario_runner_agent.py 第 129 行](../../../integration/scenario_runner_agent.py#L129)。类型：`FunctionDef`。

```python
OfficialAgentCore.__init__(self, config: OfficialAgentConfig) -> None
```

保存配置，创建默认 `SafetySupervisor` 并清空最近命令错误。core 无 PID 积分、命令缓存或跨帧安全锁存；速度估算和 Qwen client 位于外层 agent。

### `OfficialAgentCore.step`

源码位置：[integration/scenario_runner_agent.py 第 134 行](../../../integration/scenario_runner_agent.py#L134)。类型：`FunctionDef`。

```python
OfficialAgentCore.step(self, frame: OfficialSensorFrame, global_plan: Sequence[tuple[Mapping[str, float], object]], *, high_level_command: Mapping[str, object] | None=None, qwen_error: BaseException | None=None) -> tuple[float, float, float, str]
```

解析高层命令目标速度，取 LiDAR 前走廊最近距离和 GNSS 全局路线转向，用比例速度误差生成限幅 raw control，再将命令错误作为 watchdog 交 D 仲裁。最后额外执行可配置 LiDAR 距离全制动 guard（只会比 D 更严）。返回 throttle/brake/steer/reason，不写 evidence 或实际 apply 确认。

### `OfficialAgentCore._target_speed`

源码位置：[integration/scenario_runner_agent.py 第 186 行](../../../integration/scenario_runner_agent.py#L186)。类型：`FunctionDef`。

```python
OfficialAgentCore._target_speed(self, *, high_level_command: Mapping[str, object] | None, qwen_error: BaseException | None) -> tuple[float, bool]
```

Qwen 异常立即记错并返回0/invalid；在线高层命令禁止低层控制字段、需确认命令，支持停止、SET_SPEED、SLOW_DOWN及有限路线动作。无在线命令时使用默认速度或每帧读取离线 JSON，离线再检查 status、置信≥0.8和参数。任何受控解析/IO错误均 fail closed 为0/invalid；不支持变道/转弯多步执行。

### `ScenarioRunnerAgent`

源码位置：[integration/scenario_runner_agent.py 第 256 行](../../../integration/scenario_runner_agent.py#L256)。类型：`ClassDef`。

Concrete agent loaded by ``scenario_runner.py --agent``.

### `ScenarioRunnerAgent.setup`

源码位置：[integration/scenario_runner_agent.py 第 261 行](../../../integration/scenario_runner_agent.py#L261)。类型：`FunctionDef`。

```python
ScenarioRunnerAgent.setup(self, path_to_conf_file: str) -> None
```

加载配置并解析 Qwen profile；若没有 command_file，就选择显式 URL 或 profile 默认端口创建 HTTP client，否则保持离线模式。初始化 core、接口错误和 GNSS/航向历史。setup 不做服务 health、模型身份或 CARLA 传感器可用性检查。

### `ScenarioRunnerAgent.sensors`

源码位置：[integration/scenario_runner_agent.py 第 277 行](../../../integration/scenario_runner_agent.py#L277)。类型：`FunctionDef`。

```python
ScenarioRunnerAgent.sensors(self) -> list[dict[str, object]]
```

声明 front RGB 640×360@90°、32线 LiDAR（20 Hz、50 m、56k points/s）和 GNSS 三种 evaluator 传感器。当前 `_sensor_frame/_qwen_high_level_command` 实际只消费 GNSS 与 LiDAR，RGB 数据未送入 Qwen。

### `ScenarioRunnerAgent.run_step`

源码位置：[integration/scenario_runner_agent.py 第 296 行](../../../integration/scenario_runner_agent.py#L296)。类型：`FunctionDef`。

```python
ScenarioRunnerAgent.run_step(self, input_data: Mapping[str, tuple[int, Any]], timestamp: float) -> Any
```

每个 evaluator tick 解析传感帧；在线模式每帧同步调用一次 Qwen，受控 Qwen异常转 fail-closed command error，再由 core+D 生成控制。接口 Key/Type/Value 错误直接全制动；返回 CARLA VehicleControl 或 CI fallback namespace。没有异步去重、命令事件门控或证据记录，网络耗时处于官方 agent 的逐帧路径。

### `ScenarioRunnerAgent._qwen_high_level_command`

源码位置：[integration/scenario_runner_agent.py 第 326 行](../../../integration/scenario_runner_agent.py#L326)。类型：`FunctionDef`。

```python
ScenarioRunnerAgent._qwen_high_level_command(self, frame: OfficialSensorFrame, timestamp: float) -> Mapping[str, object]
```

为当前 tick 生成 request ID/估算 frame，使用固定 voice command，scene 仅含 speed，perception 仅含 LiDAR前距且 `rgb_ref=None`、`visual_valid=False`、无检测目标；近障碍时给 safety recommended STOP，然后同步 `client.infer`。因此该路径经过 Qwen，但不是比赛要求的 RGB+LiDAR 多模态输入，也不是事件触发一次请求。

### `ScenarioRunnerAgent._sensor_frame`

源码位置：[integration/scenario_runner_agent.py 第 356 行](../../../integration/scenario_runner_agent.py#L356)。类型：`FunctionDef`。

```python
ScenarioRunnerAgent._sensor_frame(self, input_data: Mapping[str, tuple[int, Any]], timestamp: float) -> OfficialSensorFrame
```

要求 input_data 有 gnss/lidar，转为 float64/float32 并检查形状和 timestamp/GNSS 有限；LiDAR只截前三列。速度由相邻 GNSS 位移除 dt 估算，位移≥2 cm 时用位移方向更新航向；首帧从全局路线 bearing 初始化。LiDAR坐标有限性不在这里整体拒绝，走廊函数逐点过滤。

### `_front_lidar_distance`

源码位置：[integration/scenario_runner_agent.py 第 404 行](../../../integration/scenario_runner_agent.py#L404)。类型：`FunctionDef`。

```python
_front_lidar_distance(points: np.ndarray, *, corridor_half_width_m: float) -> float | None
```

空点云返回 None；筛选 XYZ 全有限、前方 x>0、横向绝对值不超走廊半宽、z在[-2.2,0.5]的点，返回最小 x 米。未验证 ndarray 至少三列，正常由 `_sensor_frame` 保证；没有聚类/地面分割，单个噪点可触发停车。

### `_route_steer`

源码位置：[integration/scenario_runner_agent.py 第 418 行](../../../integration/scenario_runner_agent.py#L418)。类型：`FunctionDef`。

```python
_route_steer(latitude: float, longitude: float, compass_rad: float, global_plan: Sequence[tuple[Mapping[str, float], object]], lookahead_points: int) -> float
```

无全局计划输出0；否则按经纬度平方差找最近 plan 点，从其后序列取 lookahead bearing，与当前 compass 做包角，乘0.9并限幅[-0.6,0.6]。经纬度距离未做纬度缩放，仅用于最近索引；没有转向变化率限制。

### `_route_steer.distance_sq`

源码位置：[integration/scenario_runner_agent.py 第 427 行](../../../integration/scenario_runner_agent.py#L427)。类型：`FunctionDef`。

```python
_route_steer.distance_sq(item: tuple[Mapping[str, float], object]) -> float
```

读取 plan item 的 lat/lon 与当前坐标计算度数空间平方差，供 `min` 选最近索引。缺键/不可转换/非有限值会传播或影响排序，不转换为米。

### `_route_bearing`

源码位置：[integration/scenario_runner_agent.py 第 436 行](../../../integration/scenario_runner_agent.py#L436)。类型：`FunctionDef`。

```python
_route_bearing(latitude: float, longitude: float, global_plan: Sequence[tuple[Mapping[str, float], object]], lookahead_points: int) -> float
```

空计划返回0；否则取索引 `min(last, lookahead_points)` 的目标，经球面局部近似得到 north/east，位移足够时返回 `atan2(east,north)`，近零返回0。lookahead 按点数而非米，负值未在 helper 内拒绝（配置 loader保证正数）。

### `_gps_offset_m`

源码位置：[integration/scenario_runner_agent.py 第 454 行](../../../integration/scenario_runner_agent.py#L454)。类型：`FunctionDef`。

```python
_gps_offset_m(latitude: float, longitude: float, target_latitude: float, target_longitude: float) -> tuple[float, float]
```

用固定111,320 m/degree换算北向差，东向差再乘平均纬度余弦；适合短距离局部近似，不处理跨日期变更线、极区或高精度大地测量。

### `_finite`

源码位置：[integration/scenario_runner_agent.py 第 470 行](../../../integration/scenario_runner_agent.py#L470)。类型：`FunctionDef`。

```python
_finite(value: object, name: str, minimum: float) -> float
```

要求精确 int/float 且非 bool，转换后有限并不低于给定 minimum；类型错误与数值错误分别抛 TypeError/ValueError，返回 float。

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

来源 SHA256：`5d2cfb1ba0108e3eb77a699eeb9f867f92af7b551fb90a81b9badf392adc182e`。


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
