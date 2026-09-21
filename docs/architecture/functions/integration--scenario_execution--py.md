# scenario_execution：功能记录

上级模块：[模块说明](../modules/vehicle-scenarios.md) · 实现：[integration/scenario_execution.py](../../../integration/scenario_execution.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [场景触发、车辆行为与验收分离](scenario-evidence-contract.md)

## 功能职责与范围

Validated scenario-file loading and deterministic execution helpers.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `ScheduledCommand.time_s: float`；默认：`未在声明处设置`。
- `ScheduledCommand.envelope: dict[str, object]`；默认：`未在声明处设置`。
- `ScheduledCommand.phase_id: str | None`；默认：`None`。
- `ScheduledCommand.trigger: dict[str, object] | None`；默认：`None`。
- `ScenarioSpec.source_path: Path`；默认：`未在声明处设置`。
- `ScenarioSpec.scenario_id: str`；默认：`未在声明处设置`。
- `ScenarioSpec.category: str`；默认：`未在声明处设置`。
- `ScenarioSpec.official_level: str`；默认：`未在声明处设置`。
- `ScenarioSpec.map_name: str`；默认：`未在声明处设置`。
- `ScenarioSpec.weather: str`；默认：`未在声明处设置`。
- `ScenarioSpec.seed: int`；默认：`未在声明处设置`。
- `ScenarioSpec.fixed_delta_s: float`；默认：`未在声明处设置`。
- `ScenarioSpec.duration_s: float`；默认：`未在声明处设置`。
- `ScenarioSpec.ego_spawn_xyzyaw: tuple[float, float, float, float]`；默认：`未在声明处设置`。
- `ScenarioSpec.local_route_xy_m: tuple[tuple[float, float], ...]`；默认：`未在声明处设置`。
- `ScenarioSpec.route_resample_interval_m: float`；默认：`未在声明处设置`。
- `ScenarioSpec.finish_radius_m: float`；默认：`未在声明处设置`。
- `ScenarioSpec.commands: tuple[ScheduledCommand, ...]`；默认：`未在声明处设置`。
- `ScenarioSpec.actors: tuple[dict[str, object], ...]`；默认：`未在声明处设置`。
- `ScenarioSpec.sensors: dict[str, object]`；默认：`未在声明处设置`。
- `ScenarioSpec.qwen_fault: dict[str, object] | None`；默认：`未在声明处设置`。
- `ScenarioSpec.qwen_expected: dict[str, object] | None`；默认：`未在声明处设置`。
- `ScenarioSpec.expected: dict[str, object]`；默认：`未在声明处设置`。
- `ScenarioSpec.extensions: dict[str, object]`；默认：`未在声明处设置`。
- `ScenarioSpec.route_contract: dict[str, object]`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

### `_finite_number`

源码位置：[integration/scenario_execution.py 第 29 行](../../../integration/scenario_execution.py#L29)。类型：`FunctionDef`。

```python
_finite_number(value: object, name: str, *, minimum: float | None=None) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_nonempty_text`

源码位置：[integration/scenario_execution.py 第 40 行](../../../integration/scenario_execution.py#L40)。类型：`FunctionDef`。

```python
_nonempty_text(value: object, name: str) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScheduledCommand`

源码位置：[integration/scenario_execution.py 第 47 行](../../../integration/scenario_execution.py#L47)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioSpec`

源码位置：[integration/scenario_execution.py 第 55 行](../../../integration/scenario_execution.py#L55)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioSpec.load`

源码位置：[integration/scenario_execution.py 第 79 行](../../../integration/scenario_execution.py#L79)。类型：`FunctionDef`。

```python
ScenarioSpec.load(cls, path: str | Path) -> 'ScenarioSpec'
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioSpec.frame_count`

源码位置：[integration/scenario_execution.py 第 195 行](../../../integration/scenario_execution.py#L195)。类型：`FunctionDef`。

```python
ScenarioSpec.frame_count(self) -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioSpec.route_distance_contract_m`

源码位置：[integration/scenario_execution.py 第 199 行](../../../integration/scenario_execution.py#L199)。类型：`FunctionDef`。

```python
ScenarioSpec.route_distance_contract_m(self) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioSpec.route_planning_mode`

源码位置：[integration/scenario_execution.py 第 209 行](../../../integration/scenario_execution.py#L209)。类型：`FunctionDef`。

```python
ScenarioSpec.route_planning_mode(self) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioSpec.control_policy`

源码位置：[integration/scenario_execution.py 第 221 行](../../../integration/scenario_execution.py#L221)。类型：`FunctionDef`。

```python
ScenarioSpec.control_policy(self) -> Mapping[str, object]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioSpec.world_destination`

源码位置：[integration/scenario_execution.py 第 227 行](../../../integration/scenario_execution.py#L227)。类型：`FunctionDef`。

```python
ScenarioSpec.world_destination(self, origin_x_m: float, origin_y_m: float, yaw_deg: float) -> tuple[float, float] | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioSpec.requires_qwen_semantics`

源码位置：[integration/scenario_execution.py 第 244 行](../../../integration/scenario_execution.py#L244)。类型：`FunctionDef`。

```python
ScenarioSpec.requires_qwen_semantics(self) -> bool
```

Whether scenario commands must reach Qwen without local rewriting.

### `ScenarioSpec.world_route`

源码位置：[integration/scenario_execution.py 第 254 行](../../../integration/scenario_execution.py#L254)。类型：`FunctionDef`。

```python
ScenarioSpec.world_route(self, origin_x_m: float, origin_y_m: float, yaw_deg: float) -> tuple[tuple[float, float], ...]
```

Rotate, anchor and contract-resample the local scenario route.

### `_resample_polyline`

源码位置：[integration/scenario_execution.py 第 270 行](../../../integration/scenario_execution.py#L270)。类型：`FunctionDef`。

```python
_resample_polyline(points: Sequence[tuple[float, float]], spacing_m: float) -> tuple[tuple[float, float], ...]
```

Return approximately uniform arc-length samples, preserving both ends.

### `CommandTimeline`

源码位置：[integration/scenario_execution.py 第 292 行](../../../integration/scenario_execution.py#L292)。类型：`ClassDef`。

Return each scheduled command once its time and optional event trigger hold.

### `CommandTimeline.__init__`

源码位置：[integration/scenario_execution.py 第 295 行](../../../integration/scenario_execution.py#L295)。类型：`FunctionDef`。

```python
CommandTimeline.__init__(self, commands: Iterable[ScheduledCommand]) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `CommandTimeline.completed`

源码位置：[integration/scenario_execution.py 第 300 行](../../../integration/scenario_execution.py#L300)。类型：`FunctionDef`。

```python
CommandTimeline.completed(self) -> bool
```

Whether every declared command has been emitted exactly once.

### `CommandTimeline.due`

源码位置：[integration/scenario_execution.py 第 304 行](../../../integration/scenario_execution.py#L304)。类型：`FunctionDef`。

```python
CommandTimeline.due(self, elapsed_s: float, context: Mapping[str, object] | None=None) -> tuple[dict[str, object], ...]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `scenario_trigger_satisfied`

源码位置：[integration/scenario_execution.py 第 325 行](../../../integration/scenario_execution.py#L325)。类型：`FunctionDef`。

```python
scenario_trigger_satisfied(trigger: Mapping[str, object], *, elapsed_s: float, context: Mapping[str, object] | None=None) -> bool
```

Evaluate the declarative trigger vocabulary used by acceptance-suite v2.

### `select_best_route_anchor`

源码位置：[integration/scenario_execution.py 第 380 行](../../../integration/scenario_execution.py#L380)。类型：`FunctionDef`。

```python
select_best_route_anchor(anchors_xyzyaw: Sequence[tuple[float, float, float, float]], local_route_xy_m: Sequence[tuple[float, float]], distance_to_drivable_m: Callable[[float, float, float], float], *, sample_interval_m: float=1.0) -> tuple[int, float]
```

Choose the CARLA spawn whose real road best supports a local B route.

### `resolve_scenario_command`

源码位置：[integration/scenario_execution.py 第 417 行](../../../integration/scenario_execution.py#L417)。类型：`FunctionDef`。

```python
resolve_scenario_command(envelope: Mapping[str, object], *, requested_speed_mps: float, relative_speed_step_mps: float=DEFAULT_RELATIVE_SPEED_STEP_MPS, preserve_high_level: bool=False) -> dict[str, object]
```

Resolve trusted scenario shorthand into a concrete runtime command.

Production voice input never calls this function.  Complex live commands
therefore retain the new runtime's confirmation/fail-closed behaviour.

### `_parse_command`

源码位置：[integration/scenario_execution.py 第 487 行](../../../integration/scenario_execution.py#L487)。类型：`FunctionDef`。

```python
_parse_command(raw: object, index: int) -> ScheduledCommand
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_finite_number` 调用：`TypeError`, `ValueError`, `float`, `isinstance`, `math.isfinite`, `type`.
- `_nonempty_text` 调用：`ValueError`, `type`, `value.strip`.
- `_resample_polyline` 调用：`ValueError`, `_finite_number`, `len`, `map`, `math.ceil`, `math.hypot`, `max`, `range`, `samples.extend`, `tuple`, `zip`.
- `scenario_trigger_satisfied` 调用：`TypeError`, `ValueError`, `all`, `bool`, `distances.get`, `float`, `isinstance`, `scenario_trigger_satisfied`, `set`, `str`, `str(trigger.get('state', '')).upper`, `str(trigger.get('type', '')).strip`, `str(trigger.get('type', '')).strip().lower`, `str(values.get('traffic_light_state', 'UNKNOWN')).upper`, `trigger.get`, `values.get`.
- `select_best_route_anchor` 调用：`ValueError`, `_finite_number`, `distance_to_drivable_m`, `enumerate`, `float`, `len`, `map`, `math.ceil`, `math.cos`, `math.hypot`, `math.radians`, `math.sin`, `max`, `range`, `samples.extend`, `sum`, `tuple`, `zip`.
- `resolve_scenario_command` 调用：`TypeError`, `ValueError`, `_finite_number`, `dict`, `max`, `parameters.get`, `resolved.get`, `str`, `str(parameters.get('direction', '')).strip`, `str(parameters.get('direction', '')).strip().upper`, `str(parameters.get('unit', 'km/h')).strip`, `str(parameters.get('unit', 'km/h')).strip().lower`, `str(parameters.get('unit', 'km/h')).strip().lower().replace`, `str(resolved.get('intent', '')).upper`, `type`.
- `_parse_command` 调用：`ScheduledCommand`, `TypeError`, `ValueError`, `_finite_number`, `_nonempty_text`, `_nonempty_text(raw.get('intent'), f'commands[{index}].intent').upper`, `dict`, `max`, `normalized_parameters.pop`, `raw.get`, `str`, `type`.
- `load` 调用：`Path`, `Path(path).resolve`, `ScheduledCommand`, `TypeError`, `ValueError`, `_finite_number`, `_nonempty_text`, `_nonempty_text(data.get('official_level'), 'official_level').lower`, `_parse_command`, `any`, `cls`, `data.get`, `dict`, `ego_spawn.get`, `enumerate`, `float`, `isinstance`, `json.loads`, `len`, `max`, `parsed_points.append`, `route.get`, `runtime.get`, `sorted`, `source.read_text`, `tuple`, `type`.
- `frame_count` 调用：`math.ceil`, `max`.
- `route_distance_contract_m` 调用：`_finite_number`, `math.dist`, `self.route_contract.get`, `sum`, `zip`.
- `route_planning_mode` 调用：`ValueError`, `_nonempty_text`, `_nonempty_text(explicit, 'route.planning_mode').lower`, `self.route_contract.get`.
- `control_policy` 调用：`TypeError`, `isinstance`, `self.extensions.get`.
- `world_destination` 调用：`TypeError`, `_finite_number`, `isinstance`, `len`, `math.cos`, `math.radians`, `math.sin`, `self.route_contract.get`.
- `requires_qwen_semantics` 调用：`isinstance`, `policy.get`, `self.extensions.get`.
- `world_route` 调用：`_finite_number`, `_resample_polyline`, `math.cos`, `math.radians`, `math.sin`, `tuple`.
- `__init__` 调用：`sorted`, `tuple`.
- `completed` 调用：`len`.
- `due` 调用：`_finite_number`, `dict`, `due.append`, `len`, `scenario_trigger_satisfied`, `tuple`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_finite_number`，第 31 行：`TypeError(f'{name} must be a number')`。
- `_finite_number`，第 34 行：`ValueError(f'{name} must be finite')`。
- `_finite_number`，第 36 行：`ValueError(f'{name} must be >= {minimum}')`。
- `_nonempty_text`，第 42 行：`ValueError(f'{name} must be a non-empty string')`。
- `_parse_command`，第 489 行：`TypeError(f'commands[{index}] must be an object')`。
- `_parse_command`，第 494 行：`TypeError(f'commands[{index}].parameters must be an object')`。
- `_parse_command`，第 501 行：`ValueError(f'commands[{index}].intent_confidence must be <= 1.0')`。
- `_parse_command`，第 505 行：`TypeError(f'commands[{index}].confirm_required must be bool')`。
- `_parse_command`，第 527 行：`TypeError(f'commands[{index}].trigger must be an object')`。
- `_resample_polyline`，第 275 行：`ValueError('route needs at least two points')`。
- `_resample_polyline`，第 288 行：`ValueError('route length must be positive')`。
- `control_policy`，第 224 行：`TypeError('extensions.control_policy must be an object')`。
- `load`，第 83 行：`TypeError('scenario root must be an object')`。
- `load`，第 85 行：`ValueError("scenario schema_version must be '1.0'")`。
- `load`，第 89 行：`ValueError(f'unsupported official_level: {level}')`。
- `load`，第 92 行：`TypeError('seed must be an integer')`。
- `load`，第 98 行：`TypeError('runtime, ego_spawn and route must be objects')`。
- `load`，第 100 行：`ValueError('only scenario_local_xy_m routes are currently supported')`。
- `load`，第 103 行：`ValueError('route.points_xy_m must contain at least two points')`。
- `load`，第 107 行：`ValueError(f'route point {index} must be [x, y]')`。
- `load`，第 115 行：`TypeError('commands must be a list')`。
- `load`，第 151 行：`TypeError('actors must be a list of objects')`。
- `load`，第 153 行：`TypeError('sensors and expected must be objects')`。
- `load`，第 155 行：`TypeError('extensions must be an object')`。
- `load`，第 157 行：`TypeError('qwen_fault must be an object when provided')`。
- `load`，第 159 行：`TypeError('qwen_expected must be an object when provided')`。
- `resolve_scenario_command`，第 432 行：`TypeError('preserve_high_level must be bool')`。
- `resolve_scenario_command`，第 437 行：`TypeError('scenario command parameters must be an object')`。
- `resolve_scenario_command`，第 475 行：`ValueError(f'unsupported scenario speed unit: {unit!r}')`。
- `route_planning_mode`，第 217 行：`ValueError(f'unsupported route.planning_mode: {mode}')`。
- `scenario_trigger_satisfied`，第 333 行：`TypeError('scenario trigger must be an object')`。
- `scenario_trigger_satisfied`，第 338 行：`TypeError('scenario trigger.all must be a list')`。
- `scenario_trigger_satisfied`，第 377 行：`ValueError(f"unsupported scenario trigger type: {trigger_type or '<missing>'}")`。
- `select_best_route_anchor`，第 389 行：`ValueError('at least one route anchor is required')`。
- `select_best_route_anchor`，第 391 行：`ValueError('local route needs at least two points')`。
- `world_destination`，第 234 行：`TypeError('route.destination_xy_m must be [x, y]')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/planning_stage.py](../../../integration/planning_stage.py)
- [integration/scenario_extensions.py](../../../integration/scenario_extensions.py)
- [integration/scoring_stage.py](../../../integration/scoring_stage.py)
- [integration/tests/test_acceptance_suite_contracts.py](../../../integration/tests/test_acceptance_suite_contracts.py)
- [integration/tests/test_carla_runner_helpers.py](../../../integration/tests/test_carla_runner_helpers.py)
- [integration/tests/test_generalization_gate.py](../../../integration/tests/test_generalization_gate.py)
- [integration/tests/test_qwen_scenario_contracts.py](../../../integration/tests/test_qwen_scenario_contracts.py)
- [integration/tests/test_runtime_stages.py](../../../integration/tests/test_runtime_stages.py)
- [integration/tests/test_scenario_execution.py](../../../integration/tests/test_scenario_execution.py)
- [integration/tests/test_scenario_extensions.py](../../../integration/tests/test_scenario_extensions.py)
- [tools/run_generalization_gate.py](../../../tools/run_generalization_gate.py)
- [tools/validate_official_scenes.py](../../../tools/validate_official_scenes.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-scenarios.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `integration/scenario_execution.py`

来源 SHA256：`af5a3422416868b0acf70008336ed8fc5c8604159c1d99841d5d6dca06491b10`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `ScheduledCommand.time_s` | `float` | `无声明默认；构造/赋值方提供` |
| `ScheduledCommand.envelope` | `dict[str, object]` | `无声明默认；构造/赋值方提供` |
| `ScheduledCommand.phase_id` | `str &#124; None` | `None` |
| `ScheduledCommand.trigger` | `dict[str, object] &#124; None` | `None` |
| `ScenarioSpec.source_path` | `Path` | `无声明默认；构造/赋值方提供` |
| `ScenarioSpec.scenario_id` | `str` | `无声明默认；构造/赋值方提供` |
| `ScenarioSpec.category` | `str` | `无声明默认；构造/赋值方提供` |
| `ScenarioSpec.official_level` | `str` | `无声明默认；构造/赋值方提供` |
| `ScenarioSpec.map_name` | `str` | `无声明默认；构造/赋值方提供` |
| `ScenarioSpec.weather` | `str` | `无声明默认；构造/赋值方提供` |
| `ScenarioSpec.seed` | `int` | `无声明默认；构造/赋值方提供` |
| `ScenarioSpec.fixed_delta_s` | `float` | `无声明默认；构造/赋值方提供` |
| `ScenarioSpec.duration_s` | `float` | `无声明默认；构造/赋值方提供` |
| `ScenarioSpec.ego_spawn_xyzyaw` | `tuple[float, float, float, float]` | `无声明默认；构造/赋值方提供` |
| `ScenarioSpec.local_route_xy_m` | `tuple[tuple[float, float], ...]` | `无声明默认；构造/赋值方提供` |
| `ScenarioSpec.route_resample_interval_m` | `float` | `无声明默认；构造/赋值方提供` |
| `ScenarioSpec.finish_radius_m` | `float` | `无声明默认；构造/赋值方提供` |
| `ScenarioSpec.commands` | `tuple[ScheduledCommand, ...]` | `无声明默认；构造/赋值方提供` |
| `ScenarioSpec.actors` | `tuple[dict[str, object], ...]` | `无声明默认；构造/赋值方提供` |
| `ScenarioSpec.sensors` | `dict[str, object]` | `无声明默认；构造/赋值方提供` |
| `ScenarioSpec.qwen_fault` | `dict[str, object] &#124; None` | `无声明默认；构造/赋值方提供` |
| `ScenarioSpec.qwen_expected` | `dict[str, object] &#124; None` | `无声明默认；构造/赋值方提供` |
| `ScenarioSpec.expected` | `dict[str, object]` | `无声明默认；构造/赋值方提供` |
| `ScenarioSpec.extensions` | `dict[str, object]` | `无声明默认；构造/赋值方提供` |
| `ScenarioSpec.route_contract` | `dict[str, object]` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_finite_number` / 31 | `type(value) not in (int, float) or isinstance(value, bool)` | `raise TypeError(f'{name} must be a number')` |
| `_finite_number` / 34 | `not math.isfinite(result)` | `raise ValueError(f'{name} must be finite')` |
| `_finite_number` / 36 | `minimum is not None and result < minimum` | `raise ValueError(f'{name} must be >= {minimum}')` |
| `_nonempty_text` / 42 | `type(value) is not str or not value.strip()` | `raise ValueError(f'{name} must be a non-empty string')` |
| `ScenarioSpec.load` / 83 | `type(data) is not dict` | `raise TypeError('scenario root must be an object')` |
| `ScenarioSpec.load` / 85 | `data.get('schema_version') != '1.0'` | `raise ValueError("scenario schema_version must be '1.0'")` |
| `ScenarioSpec.load` / 89 | `level not in SUPPORTED_LEVELS` | `raise ValueError(f'unsupported official_level: {level}')` |
| `ScenarioSpec.load` / 92 | `type(seed) is not int or isinstance(seed, bool)` | `raise TypeError('seed must be an integer')` |
| `ScenarioSpec.load` / 98 | `type(runtime) is not dict or type(route) is not dict or type(ego_spawn) is not dict` | `raise TypeError('runtime, ego_spawn and route must be objects')` |
| `ScenarioSpec.load` / 100 | `route.get('coordinate_type') != 'scenario_local_xy_m'` | `raise ValueError('only scenario_local_xy_m routes are currently supported')` |
| `ScenarioSpec.load` / 103 | `type(points) is not list or len(points) < 2` | `raise ValueError('route.points_xy_m must contain at least two points')` |
| `ScenarioSpec.load` / 107 | `type(point) is not list or len(point) != 2` | `raise ValueError(f'route point {index} must be [x, y]')` |
| `ScenarioSpec.load` / 115 | `type(raw_commands) is not list` | `raise TypeError('commands must be a list')` |
| `ScenarioSpec.load` / 151 | `type(actors) is not list or any((type(item) is not dict for item in actors))` | `raise TypeError('actors must be a list of objects')` |
| `ScenarioSpec.load` / 153 | `type(sensors) is not dict or type(expected) is not dict` | `raise TypeError('sensors and expected must be objects')` |
| `ScenarioSpec.load` / 155 | `type(extensions) is not dict` | `raise TypeError('extensions must be an object')` |
| `ScenarioSpec.load` / 157 | `qwen_fault is not None and type(qwen_fault) is not dict` | `raise TypeError('qwen_fault must be an object when provided')` |
| `ScenarioSpec.load` / 159 | `qwen_expected is not None and type(qwen_expected) is not dict` | `raise TypeError('qwen_expected must be an object when provided')` |
| `ScenarioSpec.route_planning_mode` / 217 | `mode not in {'distance_coverage', 'destination', 'local_polyline', 'topology_coverage'}` | `raise ValueError(f'unsupported route.planning_mode: {mode}')` |
| `ScenarioSpec.control_policy` / 224 | `not isinstance(policy, Mapping)` | `raise TypeError('extensions.control_policy must be an object')` |
| `ScenarioSpec.world_destination` / 234 | `not isinstance(raw, list) or len(raw) != 2` | `raise TypeError('route.destination_xy_m must be [x, y]')` |
| `_resample_polyline` / 275 | `len(points) < 2` | `raise ValueError('route needs at least two points')` |
| `_resample_polyline` / 288 | `len(samples) < 2` | `raise ValueError('route length must be positive')` |
| `scenario_trigger_satisfied` / 333 | `not isinstance(trigger, Mapping)` | `raise TypeError('scenario trigger must be an object')` |
| `scenario_trigger_satisfied` / 338 | `children is not None AND not isinstance(children, Sequence) or isinstance(children, (str, bytes))` | `raise TypeError('scenario trigger.all must be a list')` |
| `scenario_trigger_satisfied` / 377 | `本地无直接if；检查上下文` | `raise ValueError(f"unsupported scenario trigger type: {trigger_type or '<missing>'}")` |
| `select_best_route_anchor` / 389 | `not anchors_xyzyaw` | `raise ValueError('at least one route anchor is required')` |
| `select_best_route_anchor` / 391 | `len(local_route_xy_m) < 2` | `raise ValueError('local route needs at least two points')` |
| `resolve_scenario_command` / 432 | `type(preserve_high_level) is not bool` | `raise TypeError('preserve_high_level must be bool')` |
| `resolve_scenario_command` / 437 | `type(parameters) is not dict` | `raise TypeError('scenario command parameters must be an object')` |
| `resolve_scenario_command` / 475 | `NOT (intent == 'SLOW_DOWN' and (not preserve_command_semantics)) AND NOT (intent == 'SPEED_UP' and (not preserve_command_semantics)) AND intent in ROUTE_FOLLOWING_INTENTS and (not preserve_command_semantics) AND NOT ('target_speed_mps' in parameters) AND 'speed' in parameters AND NOT (unit in {'km/h', 'kph', 'kmh'}) AND NOT (unit in {'m/s', 'mps'})` | `raise ValueError(f'unsupported scenario speed unit: {unit!r}')` |
| `_parse_command` / 489 | `type(raw) is not dict` | `raise TypeError(f'commands[{index}] must be an object')` |
| `_parse_command` / 494 | `type(parameters) is not dict` | `raise TypeError(f'commands[{index}].parameters must be an object')` |
| `_parse_command` / 501 | `confidence > 1.0` | `raise ValueError(f'commands[{index}].intent_confidence must be <= 1.0')` |
| `_parse_command` / 505 | `type(confirm_required) is not bool` | `raise TypeError(f'commands[{index}].confirm_required must be bool')` |
| `_parse_command` / 527 | `trigger is not None and type(trigger) is not dict` | `raise TypeError(f'commands[{index}].trigger must be an object')` |
