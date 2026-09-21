# validate_official_scenes：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/validate_official_scenes.py](../../../tools/validate_official_scenes.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

CARLA-independent contract checks for the three official competition scenes.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `ContractFailure`

源码位置：[tools/validate_official_scenes.py 第 27 行](../../../tools/validate_official_scenes.py#L27)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_require`

源码位置：[tools/validate_official_scenes.py 第 31 行](../../../tools/validate_official_scenes.py#L31)。类型：`FunctionDef`。

```python
_require(condition: bool, message: str) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_load`

源码位置：[tools/validate_official_scenes.py 第 36 行](../../../tools/validate_official_scenes.py#L36)。类型：`FunctionDef`。

```python
_load(path: Path) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_route_length`

源码位置：[tools/validate_official_scenes.py 第 40 行](../../../tools/validate_official_scenes.py#L40)。类型：`FunctionDef`。

```python
_route_length(points: Iterable[Iterable[float]]) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_actor_ids`

源码位置：[tools/validate_official_scenes.py 第 45 行](../../../tools/validate_official_scenes.py#L45)。类型：`FunctionDef`。

```python
_actor_ids(data: dict[str, Any]) -> set[str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_trigger_actor_ids`

源码位置：[tools/validate_official_scenes.py 第 49 行](../../../tools/validate_official_scenes.py#L49)。类型：`FunctionDef`。

```python
_trigger_actor_ids(trigger: Any) -> set[str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_trigger_route_progress_m`

源码位置：[tools/validate_official_scenes.py 第 64 行](../../../tools/validate_official_scenes.py#L64)。类型：`FunctionDef`。

```python
_trigger_route_progress_m(trigger: Any) -> float | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_validate_common`

源码位置：[tools/validate_official_scenes.py 第 79 行](../../../tools/validate_official_scenes.py#L79)。类型：`FunctionDef`。

```python
_validate_common(label: str, path: Path, data: dict[str, Any]) -> ScenarioSpec
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `validate_all`

源码位置：[tools/validate_official_scenes.py 第 123 行](../../../tools/validate_official_scenes.py#L123)。类型：`FunctionDef`。

```python
validate_all() -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[tools/validate_official_scenes.py 第 370 行](../../../tools/validate_official_scenes.py#L370)。类型：`FunctionDef`。

```python
main() -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_require` 调用：`ContractFailure`.
- `_load` 调用：`json.loads`, `path.read_text`.
- `_route_length` 调用：`map`, `math.dist`, `sum`, `tuple`, `zip`.
- `_actor_ids` 调用：`actor.get`, `data.get`, `str`.
- `_trigger_actor_ids` 调用：`_trigger_actor_ids`, `isinstance`, `result.update`, `set`, `str`, `trigger.get`.
- `_trigger_route_progress_m` 调用：`_trigger_route_progress_m`, `float`, `isinstance`, `max`, `str`, `str(trigger.get('type', '')).lower`, `trigger.get`.
- `_validate_common` 调用：`ScenarioSpec.load`, `_actor_ids`, `_require`, `_trigger_actor_ids`, `all`, `command.get`, `data.get`, `data.get('logging', {}).get`, `data['extensions'].get`, `data['logging'].get`, `isinstance`, `len`, `qwen_policy.get`, `required_qwen_metrics.issubset`, `required_summary.issubset`, `set`, `validate_one`.
- `validate_all` 调用：`SCENES.items`, `_actor_ids`, `_load`, `_require`, `_route_length`, `_trigger_route_progress_m`, `_validate_common`, `abs`, `actor.get`, `actor.get('activation_trigger', {}).get`, `actor.get('behavior', {}).get`, `actor.get('deactivation_trigger', {}).get`, `all`, `any`, `bicycle['route_position'].get`, `bus['route_position'].get`, `command.get`, `command_distance_trigger.get`, `cut_in['behavior'].get`, `cut_in_events[0].get`, `cut_in_trigger.get`, `float`, `isinstance`, `item.get`, `lane_profile.get`, `len`, `loaded.items`, `next`, `pedestrian.get`, `pedestrian.get('deactivation_trigger', {}).get`, `pedestrian_recovery.get`, `required_s2.issubset`, `required_s3.issubset`, `s1['route'].get`, `s2['commands'][2].get`, `s2_extensions.get`, `set`, `sorted`, `specs.values`, `speed_policy.get`, `str`, `str(actor.get('actor_id', '')).startswith`, `zip`, `{'KEEP_LANE', 'TURN_RIGHT', 'CHANGE_LANE_LEFT'}.issubset`, `{'dynamic_out_and_back_route', 'per_actor_minimum_distance_acceptance', 'route_progress_actor_activation', 'route_progress_actor_lifecycle', 'route_progress_speed_acceptance'}.issubset`, `{'front_rgb', 'left_rgb', 'right_rgb', 'rear_rgb', 'lidar'}.issubset`.
- `main` 调用：`SystemExit`, `json.dumps`, `print`, `validate_all`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_require`，第 33 行：`ContractFailure(message)`。
- `main`，第 375 行：`SystemExit(1)`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [integration/scenario_execution.py](../../../integration/scenario_execution.py)
- [tools/validate_scenarios.py](../../../tools/validate_scenarios.py)

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/validate_official_scenes.py`

来源 SHA256：`12ce1fe95d4722119d861f9665590e795e1a27fbd9ebc5eda3fb8d3b739de0a0`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_require` / 33 | `not condition` | `raise ContractFailure(message)` |
| `main` / 375 | `except (ContractFailure, KeyError, TypeError, ValueError)` | `raise SystemExit(1) from error` |
