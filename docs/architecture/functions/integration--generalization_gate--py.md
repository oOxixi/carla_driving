# generalization_gate：功能记录

上级模块：[模块说明](../modules/vehicle-scenarios.md) · 实现：[integration/generalization_gate.py](../../../integration/generalization_gate.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [场景触发、车辆行为与验收分离](scenario-evidence-contract.md)

## 功能职责与范围

Deterministic scenario perturbations for pre-CARLA generalization gates.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `PerturbationCase.case_id: str`；默认：`未在声明处设置`。
- `PerturbationCase.map_name: str`；默认：`未在声明处设置`。
- `PerturbationCase.weather: str`；默认：`未在声明处设置`。
- `PerturbationCase.seed: int`；默认：`未在声明处设置`。
- `PerturbationCase.fixed_delta_s: float`；默认：`未在声明处设置`。
- `PerturbationCase.actor_longitudinal_offset_m: float`；默认：`未在声明处设置`。
- `PerturbationCase.actor_lateral_offset_m: float`；默认：`未在声明处设置`。
- `PerturbationCase.actor_speed_scale: float`；默认：`未在声明处设置`。
- `PerturbationCase.brake_time_offset_s: float`；默认：`未在声明处设置`。
- `PerturbationCase.pedestrian_start_offset_s: float`；默认：`未在声明处设置`。
- `PerturbationCase.actor_count_scale: float`；默认：`未在声明处设置`。
- `PerturbationCase.target_lane_relation: str`；默认：`未在声明处设置`。
- `PerturbationCase.sensor_condition: str`；默认：`未在声明处设置`。
- `GeneralizationMatrix.source_path: Path`；默认：`未在声明处设置`。
- `GeneralizationMatrix.maps: tuple[str, ...]`；默认：`未在声明处设置`。
- `GeneralizationMatrix.weather_profiles: tuple[str, ...]`；默认：`未在声明处设置`。
- `GeneralizationMatrix.seeds: tuple[int, ...]`；默认：`未在声明处设置`。
- `GeneralizationMatrix.fixed_delta_seconds: tuple[float, ...]`；默认：`未在声明处设置`。
- `GeneralizationMatrix.actor_longitudinal_offsets_m: tuple[float, ...]`；默认：`未在声明处设置`。
- `GeneralizationMatrix.actor_lateral_offsets_m: tuple[float, ...]`；默认：`未在声明处设置`。
- `GeneralizationMatrix.actor_speed_scales: tuple[float, ...]`；默认：`未在声明处设置`。
- `GeneralizationMatrix.brake_time_offsets_s: tuple[float, ...]`；默认：`未在声明处设置`。
- `GeneralizationMatrix.pedestrian_start_offsets_s: tuple[float, ...]`；默认：`未在声明处设置`。
- `GeneralizationMatrix.actor_count_scales: tuple[float, ...]`；默认：`未在声明处设置`。
- `GeneralizationMatrix.target_lane_relations: tuple[str, ...]`；默认：`未在声明处设置`。
- `GeneralizationMatrix.sensor_conditions: tuple[str, ...]`；默认：`未在声明处设置`。
- `GeneralizationMatrix.samples_per_scenario: int`；默认：`未在声明处设置`。
- `GeneralizationMatrix.holdout_scenarios: tuple[str, ...]`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

### `_sequence`

源码位置：[integration/generalization_gate.py 第 17 行](../../../integration/generalization_gate.py#L17)。类型：`FunctionDef`。

```python
_sequence(raw: object, name: str) -> tuple[object, ...]
```

要求矩阵字段是非空 `list`，返回保持顺序的 tuple；空列表、tuple 或其他类型均抛 `ValueError`。元素类型由各字段的后续解析负责。

### `PerturbationCase`

源码位置：[integration/generalization_gate.py 第 24 行](../../../integration/generalization_gate.py#L24)。类型：`ClassDef`。

冻结的一次泛化扰动参数集，绑定派生 case ID、地图/天气/种子、仿真步长、actor 纵横偏移、速度/数量比例、制动/行人时间偏移、目标车道关系及传感器条件。dataclass 直接构造不校验范围，正常来源应为已验证的 `GeneralizationMatrix.cases`。

### `GeneralizationMatrix`

源码位置：[integration/generalization_gate.py 第 41 行](../../../integration/generalization_gate.py#L41)。类型：`ClassDef`。

冻结矩阵配置及其来源路径，保存每一扰动维度的候选 tuple、每场景采样数和 holdout ID。它描述候选空间而非笛卡尔积结果；内部值在 `load_generalization_matrix` 校验，直接实例化不会重复校验。

### `GeneralizationMatrix.cases`

源码位置：[integration/generalization_gate.py 第 58 行](../../../integration/generalization_gate.py#L58)。类型：`FunctionDef`。

```python
GeneralizationMatrix.cases(self, scenario_id: str) -> Iterator[PerturbationCase]
```

Yield a bounded Latin-cycle sample instead of an explosive product.

### `load_generalization_matrix`

源码位置：[integration/generalization_gate.py 第 78 行](../../../integration/generalization_gate.py#L78)。类型：`FunctionDef`。

```python
load_generalization_matrix(path: str | Path | None=None) -> GeneralizationMatrix
```

读取默认或指定 UTF-8 JSON，要求根对象和 schema 1.0、所有维度非空、seed 为精确整数、采样数正整数，车道关系仅 CURRENT/左右相邻，传感器条件仅 nominal/reduced_rgb/sparse_lidar。路径解析、JSON 和数值转换异常直接传播；本入口不检查地图/天气是否被当前 CARLA 安装支持。

### `load_generalization_matrix.numbers`

源码位置：[integration/generalization_gate.py 第 89 行](../../../integration/generalization_gate.py#L89)。类型：`FunctionDef`。

```python
load_generalization_matrix.numbers(name: str, *, positive: bool=False) -> tuple[float, ...]
```

从当前 JSON 根读取指定非空列表并把每项转 float，拒绝非有限值；`positive=True` 时还要求严格大于零。布尔值会被 `float` 接受为 0/1，只有正值分支会因 False=0 被拒绝，矩阵作者应避免布尔数值。

### `_referenced_actor_ids`

源码位置：[integration/generalization_gate.py 第 133 行](../../../integration/generalization_gate.py#L133)。类型：`FunctionDef`。

```python
_referenced_actor_ids(scenario: Mapping[str, Any]) -> set[str]
```

递归扫描 commands、expected、qwen_expected 和 extensions 中键名精确为 `actor_id`/`target_actor_id` 的字符串值，返回被语义或验收引用的 actor ID 集合。actors 本身不扫描，其他别名如 target_id 也不计入保护集。

### `_referenced_actor_ids.visit`

源码位置：[integration/generalization_gate.py 第 136 行](../../../integration/generalization_gate.py#L136)。类型：`FunctionDef`。

```python
_referenced_actor_ids.visit(value: object) -> None
```

深度遍历 mapping 和非字符串 sequence；命中 actor 引用键时加入结果而不继续遍历该字符串，其余子值递归。该闭包只读输入并修改外层 set，没有循环引用保护。

### `_scale_auxiliary_vehicles`

源码位置：[integration/generalization_gate.py 第 152 行](../../../integration/generalization_gate.py#L152)。类型：`FunctionDef`。

```python
_scale_auxiliary_vehicles(actors: list[dict[str, Any]], scale: float, referenced_actor_ids: set[str]) -> list[dict[str, Any]]
```

按 `round(车辆数*scale)` 且至少 1 计算目标车辆数，只删除/克隆未被语义引用的辅助车辆。缩小时从 auxiliary 尾部删除；放大时循环复制原 auxiliary，沿路线每个 clone 增加 12 m 并生成 density ID。没有车辆或没有可用 auxiliary 时保持原样，因此比例是目标而非必达保证，非车辆 actor 不参与数量缩放。

### `_apply_sensor_condition`

源码位置：[integration/generalization_gate.py 第 182 行](../../../integration/generalization_gate.py#L182)。类型：`FunctionDef`。

```python
_apply_sensor_condition(scenario: dict[str, Any], condition: str) -> None
```

原地修改派生 scenario 的 sensors：reduced_rgb 将 ID 含 rgb 的 width/height 缩为 75%且不低于64；sparse_lidar 将 `sensors.lidar.channels` 减半且不低于8；nominal 或无对象配置不动作。只改变声明配置，不证明仿真实际采用或传感质量达到预期。

### `perturb_scenario`

源码位置：[integration/generalization_gate.py 第 199 行](../../../integration/generalization_gate.py#L199)。类型：`FunctionDef`。

```python
perturb_scenario(raw_scenario: Mapping[str, Any], case: PerturbationCase) -> dict[str, Any]
```

Return an in-memory variant without changing semantic commands/oracles.

## 内部调用与异常路径

- `_sequence` 调用：`ValueError`, `isinstance`, `tuple`.
- `load_generalization_matrix` 调用：`GeneralizationMatrix`, `Path`, `Path(path).expanduser`, `Path(path).expanduser().resolve`, `TypeError`, `ValueError`, `_sequence`, `any`, `float`, `int`, `isinstance`, `json.loads`, `math.isfinite`, `numbers`, `raw.get`, `source.read_text`, `str`, `str(item).strip`, `str(item).strip().lower`, `str(item).strip().upper`, `tuple`, `type`.
- `_referenced_actor_ids` 调用：`isinstance`, `result.add`, `scenario.get`, `set`, `str`, `value.items`, `visit`.
- `_scale_auxiliary_vehicles` 调用：`actor.get`, `auxiliary.pop`, `float`, `item.get`, `len`, `list`, `max`, `offset_actor_route_position`, `result.append`, `result.remove`, `round`, `source.get`, `str`, `str(actor.get('type', '')).lower`, `str(item.get('type', '')).lower`.
- `_apply_sensor_condition` 调用：`float`, `isinstance`, `max`, `round`, `scenario.get`, `sensors.get`, `sensors.items`, `str`, `str(sensor_id).lower`.
- `perturb_scenario` 调用：`TypeError`, `_apply_sensor_condition`, `_referenced_actor_ids`, `_scale_auxiliary_vehicles`, `actor.get`, `deepcopy`, `dict`, `extensions.pop`, `float`, `isinstance`, `len`, `materialized_actors.append`, `max`, `offset_actor_route_position`, `parameterization.get`, `raw_scenario.get`, `scenario.get`, `scenario.setdefault`, `str`, `str(actor.get('type', '')).lower`, `str(actor.get('type', '')).lower().startswith`, `str(item).upper`, `tuple`.
- `cases` 调用：`PerturbationCase`, `len`, `range`.
- `numbers` 调用：`ValueError`, `_sequence`, `any`, `float`, `math.isfinite`, `raw.get`, `tuple`.
- `visit` 调用：`isinstance`, `result.add`, `str`, `value.items`, `visit`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_sequence`，第 19 行：`ValueError(f'generalization matrix {name} must be a non-empty list')`。
- `load_generalization_matrix`，第 82 行：`ValueError("generalization matrix schema_version must be '1.0'")`。
- `load_generalization_matrix`，第 87 行：`TypeError('generalization matrix seeds must be integers')`。
- `load_generalization_matrix`，第 93 行：`ValueError(f'generalization matrix {name} contains invalid values')`。
- `load_generalization_matrix`，第 98 行：`ValueError('samples_per_scenario must be a positive integer')`。
- `load_generalization_matrix`，第 106 行：`ValueError('generalization matrix target_lane_relations contains an unsupported lane')`。
- `load_generalization_matrix`，第 113 行：`ValueError('generalization matrix sensor_conditions contains an unsupported profile')`。
- `numbers`，第 93 行：`ValueError(f'generalization matrix {name} contains invalid values')`。
- `perturb_scenario`，第 208 行：`TypeError('scenario runtime must be an object')`。
- `perturb_scenario`，第 212 行：`TypeError('scenario actors must be a list')`。
- `perturb_scenario`，第 216 行：`TypeError('scenario actor must be an object')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [integration/scenario_builder.py](../../../integration/scenario_builder.py)

静态 import 消费者（含测试）：

- [integration/tests/test_generalization_gate.py](../../../integration/tests/test_generalization_gate.py)
- [tools/run_generalization_gate.py](../../../tools/run_generalization_gate.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-scenarios.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `integration/generalization_gate.py`

来源 SHA256：`8aec79afe64e3d891f56446df85f5e05c154784d155b8f9d6ccbdc9df5f832b7`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `PerturbationCase.case_id` | `str` | `无声明默认；构造/赋值方提供` |
| `PerturbationCase.map_name` | `str` | `无声明默认；构造/赋值方提供` |
| `PerturbationCase.weather` | `str` | `无声明默认；构造/赋值方提供` |
| `PerturbationCase.seed` | `int` | `无声明默认；构造/赋值方提供` |
| `PerturbationCase.fixed_delta_s` | `float` | `无声明默认；构造/赋值方提供` |
| `PerturbationCase.actor_longitudinal_offset_m` | `float` | `无声明默认；构造/赋值方提供` |
| `PerturbationCase.actor_lateral_offset_m` | `float` | `无声明默认；构造/赋值方提供` |
| `PerturbationCase.actor_speed_scale` | `float` | `无声明默认；构造/赋值方提供` |
| `PerturbationCase.brake_time_offset_s` | `float` | `无声明默认；构造/赋值方提供` |
| `PerturbationCase.pedestrian_start_offset_s` | `float` | `无声明默认；构造/赋值方提供` |
| `PerturbationCase.actor_count_scale` | `float` | `无声明默认；构造/赋值方提供` |
| `PerturbationCase.target_lane_relation` | `str` | `无声明默认；构造/赋值方提供` |
| `PerturbationCase.sensor_condition` | `str` | `无声明默认；构造/赋值方提供` |
| `GeneralizationMatrix.source_path` | `Path` | `无声明默认；构造/赋值方提供` |
| `GeneralizationMatrix.maps` | `tuple[str, ...]` | `无声明默认；构造/赋值方提供` |
| `GeneralizationMatrix.weather_profiles` | `tuple[str, ...]` | `无声明默认；构造/赋值方提供` |
| `GeneralizationMatrix.seeds` | `tuple[int, ...]` | `无声明默认；构造/赋值方提供` |
| `GeneralizationMatrix.fixed_delta_seconds` | `tuple[float, ...]` | `无声明默认；构造/赋值方提供` |
| `GeneralizationMatrix.actor_longitudinal_offsets_m` | `tuple[float, ...]` | `无声明默认；构造/赋值方提供` |
| `GeneralizationMatrix.actor_lateral_offsets_m` | `tuple[float, ...]` | `无声明默认；构造/赋值方提供` |
| `GeneralizationMatrix.actor_speed_scales` | `tuple[float, ...]` | `无声明默认；构造/赋值方提供` |
| `GeneralizationMatrix.brake_time_offsets_s` | `tuple[float, ...]` | `无声明默认；构造/赋值方提供` |
| `GeneralizationMatrix.pedestrian_start_offsets_s` | `tuple[float, ...]` | `无声明默认；构造/赋值方提供` |
| `GeneralizationMatrix.actor_count_scales` | `tuple[float, ...]` | `无声明默认；构造/赋值方提供` |
| `GeneralizationMatrix.target_lane_relations` | `tuple[str, ...]` | `无声明默认；构造/赋值方提供` |
| `GeneralizationMatrix.sensor_conditions` | `tuple[str, ...]` | `无声明默认；构造/赋值方提供` |
| `GeneralizationMatrix.samples_per_scenario` | `int` | `无声明默认；构造/赋值方提供` |
| `GeneralizationMatrix.holdout_scenarios` | `tuple[str, ...]` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_sequence` / 19 | `not isinstance(raw, list) or not raw` | `raise ValueError(f'generalization matrix {name} must be a non-empty list')` |
| `load_generalization_matrix` / 82 | `not isinstance(raw, dict) or raw.get('schema_version') != '1.0'` | `raise ValueError("generalization matrix schema_version must be '1.0'")` |
| `load_generalization_matrix` / 87 | `any((type(item) is not int or isinstance(item, bool) for item in seeds_raw))` | `raise TypeError('generalization matrix seeds must be integers')` |
| `load_generalization_matrix` / 98 | `type(samples) is not int or samples < 1` | `raise ValueError('samples_per_scenario must be a positive integer')` |
| `load_generalization_matrix` / 106 | `any((item not in allowed_lanes for item in lane_relations))` | `raise ValueError('generalization matrix target_lane_relations contains an unsupported lane')` |
| `load_generalization_matrix` / 113 | `any((item not in allowed_sensors for item in sensor_conditions))` | `raise ValueError('generalization matrix sensor_conditions contains an unsupported profile')` |
| `load_generalization_matrix.numbers` / 93 | `any((not math.isfinite(item) or (positive and item <= 0.0) for item in result))` | `raise ValueError(f'generalization matrix {name} contains invalid values')` |
| `perturb_scenario` / 208 | `not isinstance(runtime, dict)` | `raise TypeError('scenario runtime must be an object')` |
| `perturb_scenario` / 212 | `not isinstance(actors, list)` | `raise TypeError('scenario actors must be a list')` |
| `perturb_scenario` / 216 | `not isinstance(actor, dict)` | `raise TypeError('scenario actor must be an object')` |
