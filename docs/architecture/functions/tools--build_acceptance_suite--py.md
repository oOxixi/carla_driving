# build_acceptance_suite：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/build_acceptance_suite.py](../../../tools/build_acceptance_suite.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Build the 83-scenario Dongfeng-track acceptance suite.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `command`

源码位置：[tools/build_acceptance_suite.py 第 56 行](../../../tools/build_acceptance_suite.py#L56)。类型：`FunctionDef`。

```python
command(time_s: float, text: str, intent: str, *, speed_kph: float | None=None, parameters: dict[str, Any] | None=None, status: str='valid', confirm_required: bool=False, phase_id: str | None=None, trigger: dict[str, Any] | None=None) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `vehicle`

源码位置：[tools/build_acceptance_suite.py 第 87 行](../../../tools/build_acceptance_suite.py#L87)。类型：`FunctionDef`。

```python
vehicle(actor_id: str, x: float, y: float=0.0, *, speed_mps: float=0.0, brake_at_s: float | None=None, target_speed_mps: float | None=None, blueprint_id: str='vehicle.audi.tt', behavior_mode: str='lead_vehicle', behavior_events: list[dict[str, Any]] | None=None) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `walker`

源码位置：[tools/build_acceptance_suite.py 第 117 行](../../../tools/build_acceptance_suite.py#L117)。类型：`FunctionDef`。

```python
walker(actor_id: str, x: float, start_y: float=-3.0, end_y: float=3.0, *, start_time_s: float=4.0, speed_mps: float=1.4, trigger: dict[str, Any] | None=None, phase_id: str | None=None) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `prop`

源码位置：[tools/build_acceptance_suite.py 第 146 行](../../../tools/build_acceptance_suite.py#L146)。类型：`FunctionDef`。

```python
prop(actor_id: str, x: float, y: float, yaw_deg: float=0.0) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `red_light`

源码位置：[tools/build_acceptance_suite.py 第 155 行](../../../tools/build_acceptance_suite.py#L155)。类型：`FunctionDef`。

```python
red_light(distance_m: float=18.0) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `fault`

源码位置：[tools/build_acceptance_suite.py 第 164 行](../../../tools/build_acceptance_suite.py#L164)。类型：`FunctionDef`。

```python
fault(fault_id: str, fault_type: str, time_s: float, duration_s: float, **values: Any) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `scenario`

源码位置：[tools/build_acceptance_suite.py 第 180 行](../../../tools/build_acceptance_suite.py#L180)。类型：`FunctionDef`。

```python
scenario(scenario_id: str, folder: str, *, priority: str, category: str, level: str, capability: str, description: str, commands: list[dict[str, Any]], route: list[list[float]] | None=None, route_values: dict[str, Any] | None=None, actors: list[dict[str, Any]] | None=None, expected: dict[str, Any] | None=None, weather: str='ClearNoon', seed: int=0, duration_s: float=35.0, ego_y: float=0.0, oracle_behaviors: list[str] | None=None, expected_target_actor_id: str | None=None, faults: list[dict[str, Any]] | None=None, proposed_acceptance: dict[str, Any] | None=None, extension_requirements: list[str] | None=None, extension_values: dict[str, Any] | None=None, notes: list[str] | None=None, suite_group: str | None=None, extra_tags: list[str] | None=None) -> tuple[str, dict[str, Any], dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `build_scenarios`

源码位置：[tools/build_acceptance_suite.py 第 326 行](../../../tools/build_acceptance_suite.py#L326)。类型：`FunctionDef`。

```python
build_scenarios() -> list[tuple[str, dict[str, Any], dict[str, Any]]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `matrix`

源码位置：[tools/build_acceptance_suite.py 第 1533 行](../../../tools/build_acceptance_suite.py#L1533)。类型：`FunctionDef`。

```python
matrix(entries: list[dict[str, Any]]) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `render_json`

源码位置：[tools/build_acceptance_suite.py 第 1566 行](../../../tools/build_acceptance_suite.py#L1566)。类型：`FunctionDef`。

```python
render_json(data: dict[str, Any]) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `render_build_summary`

源码位置：[tools/build_acceptance_suite.py 第 1570 行](../../../tools/build_acceptance_suite.py#L1570)。类型：`FunctionDef`。

```python
render_build_summary(entries: list[dict[str, Any]]) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[tools/build_acceptance_suite.py 第 1645 行](../../../tools/build_acceptance_suite.py#L1645)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `command` 调用：`dict`.
- `scenario` 调用：`extensions.update`, `list`, `missing_runtime_requirements`, `priority.lower`.
- `build_scenarios` 调用：`add`, `command`, `fault`, `prop`, `red_light`, `scenario`, `vehicle`, `walker`.
- `matrix` 调用：`item['priority'].startswith`, `len`, `sum`.
- `render_json` 调用：`json.dumps`.
- `render_build_summary` 调用：`'\n'.join`, `enumerate`, `group_labels.items`, `item['path'].startswith`, `len`, `lines.append`, `lines.extend`, `next`, `sum`.
- `main` 调用：`RuntimeError`, `argparse.ArgumentParser`, `build_scenarios`, `json.loads`, `len`, `matrix`, `outputs.items`, `parser.add_argument`, `parser.parse_args`, `path.exists`, `path.parent.mkdir`, `path.read_text`, `path.relative_to`, `path.write_text`, `preserved.append`, `print`, `removed_path.exists`, `removed_path.unlink`, `render_build_summary`, `render_json`, `scenario_path.exists`, `scenario_path.read_text`, `set`, `stale.append`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `main`，第 1660 行：`RuntimeError(f"suite must contain {EXPECTED_COUNTS['total']} scenarios, got {len(scenarios)}")`。
- `main`，第 1665 行：`RuntimeError('scenario_id values must be unique')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 1647 行：`parser.add_argument('--check', action='store_true', help='verify generated files are current without writing them')`。
- 第 1652 行：`parser.add_argument('--refresh-scenarios', action='store_true', help='overwrite checked-in scenario contracts from generator defaults')`。

## 上下游与关联验证

静态导入的项目内实现：

- [integration/scenario_extensions.py](../../../integration/scenario_extensions.py)

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/build_acceptance_suite.py`

来源 SHA256：`1777d37563e78ecadec58f76b122271782c9199fc8ed3a4ae20c0eb9fe89eeb0`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 1647 | `'--check'` | `action='store_true'; help='verify generated files are current without writing them'` |
| 1652 | `'--refresh-scenarios'` | `action='store_true'; help='overwrite checked-in scenario contracts from generator defaults'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `main` / 1660 | `len(scenarios) != EXPECTED_COUNTS['total']` | `raise RuntimeError(f"suite must contain {EXPECTED_COUNTS['total']} scenarios, got {len(scenarios)}")` |
| `main` / 1665 | `len(ids) != len(set(ids))` | `raise RuntimeError('scenario_id values must be unique')` |
