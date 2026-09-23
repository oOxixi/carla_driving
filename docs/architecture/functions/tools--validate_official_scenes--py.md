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

【ContractFailure】定义维护工具的数据检查、生成、评测或证据处理所需的对象边界；类字段、构造校验和方法才是完整合同，实例化本身不代表外部资源或运行门禁已通过。

### `_require`

源码位置：[tools/validate_official_scenes.py 第 31 行](../../../tools/validate_official_scenes.py#L31)。类型：`FunctionDef`。

```python
_require(condition: bool, message: str) -> None
```

【_require】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_load`

源码位置：[tools/validate_official_scenes.py 第 36 行](../../../tools/validate_official_scenes.py#L36)。类型：`FunctionDef`。

```python
_load(path: Path) -> dict[str, Any]
```

【_load】从参数、文件、环境或缓存解析维护工具的数据检查、生成、评测或证据处理所需输入；路径优先级、默认值和缺失处理以函数体为准，读取成功不自动证明内容身份正确。

### `_route_length`

源码位置：[tools/validate_official_scenes.py 第 40 行](../../../tools/validate_official_scenes.py#L40)。类型：`FunctionDef`。

```python
_route_length(points: Iterable[Iterable[float]]) -> float
```

【_route_length】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_actor_ids`

源码位置：[tools/validate_official_scenes.py 第 45 行](../../../tools/validate_official_scenes.py#L45)。类型：`FunctionDef`。

```python
_actor_ids(data: dict[str, Any]) -> set[str]
```

【_actor_ids】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_trigger_actor_ids`

源码位置：[tools/validate_official_scenes.py 第 49 行](../../../tools/validate_official_scenes.py#L49)。类型：`FunctionDef`。

```python
_trigger_actor_ids(trigger: Any) -> set[str]
```

【_trigger_actor_ids】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_trigger_route_progress_m`

源码位置：[tools/validate_official_scenes.py 第 64 行](../../../tools/validate_official_scenes.py#L64)。类型：`FunctionDef`。

```python
_trigger_route_progress_m(trigger: Any) -> float | None
```

【_trigger_route_progress_m】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_validate_common`

源码位置：[tools/validate_official_scenes.py 第 79 行](../../../tools/validate_official_scenes.py#L79)。类型：`FunctionDef`。

```python
_validate_common(label: str, path: Path, data: dict[str, Any]) -> ScenarioSpec
```

【_validate_common】检查维护工具的数据检查、生成、评测或证据处理的局部合同并返回/累计函数体定义的结果；静态校验通过不等于外部服务、CARLA、音频模型或最终交付已经通过。

### `validate_all`

源码位置：[tools/validate_official_scenes.py 第 123 行](../../../tools/validate_official_scenes.py#L123)。类型：`FunctionDef`。

```python
validate_all() -> dict[str, Any]
```

【validate_all】检查维护工具的数据检查、生成、评测或证据处理的局部合同并返回/累计函数体定义的结果；静态校验通过不等于外部服务、CARLA、音频模型或最终交付已经通过。

### `main`

源码位置：[tools/validate_official_scenes.py 第 370 行](../../../tools/validate_official_scenes.py#L370)。类型：`FunctionDef`。

```python
main() -> None
```

【main】是维护工具的数据检查、生成、评测或证据处理的执行/命令入口；参数来自紧邻签名或本页CLI表，可能读取外部资源、写产物或启动服务，应以退出码、原始日志和固定输入身份判定结果。

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
