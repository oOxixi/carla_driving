# qwen_scenario_monitor：功能记录

上级模块：[模块说明](../modules/vehicle-planner.md) · 实现：[integration/qwen_scenario_monitor.py](../../../integration/qwen_scenario_monitor.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [异步等待、旧结果拒绝与多层命令ID](async-plan-dispatch.md)
- [计划可行性校验与内部步骤展开](plan-validation-compilation.md)

## 功能职责与范围

CARLA-independent acceptance monitor for ``qwen_expected`` contracts.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `QwenScenarioReport.passed: bool`；默认：`未在声明处设置`。
- `QwenScenarioReport.checks: Mapping[str, bool]`；默认：`未在声明处设置`。
- `QwenScenarioReport.failures: tuple[str, ...]`；默认：`未在声明处设置`。
- `QwenScenarioReport.observed: Mapping[str, Any]`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

<a id="fn-qwenscenarioreport"></a>

### `QwenScenarioReport`

源码位置：[integration/qwen_scenario_monitor.py 第 20 行](../../../integration/qwen_scenario_monitor.py#L20)。类型：`ClassDef`。

冻结验收报告，passed 为所有 checks 同时为真，failures 保存失败检查名，observed 保存路由、调用数、行为、终态和禁止字段路径等证据；不是原始逐帧轨迹。

<a id="fn-qwenscenarioreport-to-dict"></a>

### `QwenScenarioReport.to_dict`

源码位置：[integration/qwen_scenario_monitor.py 第 26 行](../../../integration/qwen_scenario_monitor.py#L26)。类型：`FunctionDef`。

```python
QwenScenarioReport.to_dict(self) -> dict[str, Any]
```

将 checks/observed 转顶层 dict、failures 转 list 返回；observed 嵌套列表不深复制，调用方不应据冻结 dataclass 推断整个报告不可变。

<a id="fn-qwenscenariomonitor"></a>

### `QwenScenarioMonitor`

源码位置：[integration/qwen_scenario_monitor.py 第 35 行](../../../integration/qwen_scenario_monitor.py#L35)。类型：`ClassDef`。

汇总 qwen_expected 的路由/调用/行为/终态契约，不调用模型、不驱动车辆，也不代替基础 scenario acceptance。通过此监控不等于场景任务完成。

<a id="fn-qwenscenariomonitor---init--"></a>

### `QwenScenarioMonitor.__init__`

源码位置：[integration/qwen_scenario_monitor.py 第 36 行](../../../integration/qwen_scenario_monitor.py#L36)。类型：`FunctionDef`。

```python
QwenScenarioMonitor.__init__(self, expected: Mapping[str, Any]) -> None
```

expected 要求映射，route 精确为 QWEN_PLAN 或 CONFIRM_SAFE，min_calls/max_calls 为整数且 0<=min<=max；其余 expected_behaviors/expected_terminal/expected_terminal_reason_prefix/allowed_replans 在 finalize 消费，allowed_replans 默认 0。初始化空证据集合，expected 仅顶层复制。

<a id="fn-qwenscenariomonitor-record-routing"></a>

### `QwenScenarioMonitor.record_routing`

源码位置：[integration/qwen_scenario_monitor.py 第 60 行](../../../integration/qwen_scenario_monitor.py#L60)。类型：`FunctionDef`。

```python
QwenScenarioMonitor.record_routing(self, route: str, *, qwen_submitted: bool=False, command_id: str | None=None) -> None
```

route 转大写并校验；可选 command_id 去空白后非空并加入用户命令集合，qwen_submitted=True 才增加模型调用数。记录 route 后才校验 command_id，非法 ID 异常前可能已修改 routes。

<a id="fn-qwenscenariomonitor-record-plan"></a>

### `QwenScenarioMonitor.record_plan`

源码位置：[integration/qwen_scenario_monitor.py 第 79 行](../../../integration/qwen_scenario_monitor.py#L79)。类型：`FunctionDef`。

```python
QwenScenarioMonitor.record_plan(self, plan: Mapping[str, Any]) -> None
```

要求映射，递归记录禁止低层字段路径；schema_version=2.0 时收集每步 behavior，否则收集顶层 behavior。不做 Schema/时效/身份校验，调用方应传已校验计划。

<a id="fn-qwenscenariomonitor-record-behavior"></a>

### `QwenScenarioMonitor.record_behavior`

源码位置：[integration/qwen_scenario_monitor.py 第 93 行](../../../integration/qwen_scenario_monitor.py#L93)。类型：`FunctionDef`。

```python
QwenScenarioMonitor.record_behavior(self, behavior: Any) -> None
```

Record a behavior from a validated Qwen plan or safety hold.

<a id="fn-qwenscenariomonitor-record-replan"></a>

### `QwenScenarioMonitor.record_replan`

源码位置：[integration/qwen_scenario_monitor.py 第 100 行](../../../integration/qwen_scenario_monitor.py#L100)。类型：`FunctionDef`。

```python
QwenScenarioMonitor.record_replan(self) -> None
```

每次调用将 replans 加 1，不推断具体原因、不自动发起重规划，也不按 command_id 去重。

<a id="fn-qwenscenariomonitor-record-terminal"></a>

### `QwenScenarioMonitor.record_terminal`

源码位置：[integration/qwen_scenario_monitor.py 第 103 行](../../../integration/qwen_scenario_monitor.py#L103)。类型：`FunctionDef`。

```python
QwenScenarioMonitor.record_terminal(self, status: Any, *, command_id: str | None=None, reason_code: Any | None=None) -> None
```

支持枚举或字符串状态，只记录已知终态（包含 CONFIRMING）。已有路由命令集合时过滤不属于该集合的等待命令；未指定 ID 且未登记集合时用 <unspecified>。同一 ID 重复上报累加而不去重，用于 single_terminal 检查。

<a id="fn-qwenscenariomonitor-finalize"></a>

### `QwenScenarioMonitor.finalize`

源码位置：[integration/qwen_scenario_monitor.py 第 125 行](../../../integration/qwen_scenario_monitor.py#L125)。类型：`FunctionDef`。

```python
QwenScenarioMonitor.finalize(self) -> QwenScenarioReport
```

要求所有已观测 route 符合期望、调用数在闭区间、行为集合包含期望、期望终态至少出现一次、原因前缀至少匹配一次、已记录终态的每个 ID 恰好一次、重规划不超限且无低层字段。行为不检查顺序；终态与原因分别匹配；single_terminal 不检查每个路由命令均有终态，不能作为全命令生命周期完整性证明。

<a id="fn--forbidden-paths"></a>

### `_forbidden_paths`

源码位置：[integration/qwen_scenario_monitor.py 第 177 行](../../../integration/qwen_scenario_monitor.py#L177)。类型：`FunctionDef`。

```python
_forbidden_paths(value: Any, path: str='<root>') -> list[str]
```

递归 Mapping 与非字符串 Sequence，以大小写不敏感键匹配 FORBIDDEN_LOW_LEVEL_FIELDS，返回含字典键/列表索引的完整路径；不修改载荷，且不是完整 JSON Schema 校验。

## 内部调用与异常路径

- `_forbidden_paths` 调用：`_forbidden_paths`, `enumerate`, `found.append`, `found.extend`, `isinstance`, `str`, `str(key).lower`, `value.items`.
- `to_dict` 调用：`dict`, `list`.
- `__init__` 调用：`TypeError`, `ValueError`, `dict`, `expected.get`, `isinstance`, `set`, `str`, `type`.
- `record_routing` 调用：`ValueError`, `self.command_ids.add`, `self.routes.append`, `str`, `str(command_id).strip`, `str(route).upper`.
- `record_plan` 调用：`TypeError`, `_forbidden_paths`, `isinstance`, `plan.get`, `self.behaviors.append`, `self.behaviors.extend`, `self.forbidden_paths.extend`, `step.get`, `str`, `str(plan['behavior']).upper`, `str(step.get('behavior', '')).upper`.
- `record_behavior` 调用：`ValueError`, `self.behaviors.append`, `str`, `str(behavior).strip`, `str(behavior).strip().upper`.
- `record_terminal` 调用：`getattr`, `self.terminal_counts.get`, `self.terminal_reasons.append`, `self.terminals.append`, `str`, `str(command_id).strip`, `str(reason_code).strip`, `str(reason_code).strip().upper`, `str(value).upper`.
- `finalize` 调用：`QwenScenarioReport`, `all`, `any`, `bool`, `checks.items`, `dict`, `expected_behaviors.issubset`, `int`, `list`, `reason.startswith`, `self.expected.get`, `self.terminal_counts.values`, `set`, `str`, `str(item).upper`, `str(self.expected.get('expected_terminal', '')).upper`, `str(self.expected.get('expected_terminal_reason_prefix', '')).upper`, `tuple`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 38 行：`TypeError('qwen_expected must be a mapping')`。
- `__init__`，第 41 行：`ValueError('qwen_expected.route is invalid')`。
- `__init__`，第 48 行：`ValueError('qwen_expected calls must satisfy 0 <= min <= max')`。
- `record_behavior`，第 97 行：`ValueError('behavior must be non-empty')`。
- `record_plan`，第 81 行：`TypeError('plan must be a mapping')`。
- `record_routing`，第 69 行：`ValueError(f'invalid observed route: {route!r}')`。
- `record_routing`，第 74 行：`ValueError('command_id must be non-empty when provided')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [runtime/plan_validator.py](../../../runtime/plan_validator.py)

静态 import 消费者（含测试）：

- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/tests/test_qwen_scenario_monitor.py](../../../integration/tests/test_qwen_scenario_monitor.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-planner.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-integration-qwen-scenario-monitor-py"></a>

### `integration/qwen_scenario_monitor.py`

来源 SHA256：`36d681ed43f25e871ab29adec01a86dbbcac2a26ebf9f1cede827c20ca925d23`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `QwenScenarioReport.passed` | `bool` | `无声明默认；构造/赋值方提供` |
| `QwenScenarioReport.checks` | `Mapping[str, bool]` | `无声明默认；构造/赋值方提供` |
| `QwenScenarioReport.failures` | `tuple[str, ...]` | `无声明默认；构造/赋值方提供` |
| `QwenScenarioReport.observed` | `Mapping[str, Any]` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `QwenScenarioMonitor.__init__` / 38 | `not isinstance(expected, Mapping)` | `raise TypeError('qwen_expected must be a mapping')` |
| `QwenScenarioMonitor.__init__` / 41 | `route not in _ROUTES` | `raise ValueError('qwen_expected.route is invalid')` |
| `QwenScenarioMonitor.__init__` / 48 | `type(minimum) is not int or isinstance(minimum, bool) or type(maximum) is not int or isinstance(maximum, bool) or (not 0 <= minimum <= maximum)` | `raise ValueError('qwen_expected calls must satisfy 0 <= min <= max')` |
| `QwenScenarioMonitor.record_routing` / 69 | `normalized not in _ROUTES` | `raise ValueError(f'invalid observed route: {route!r}')` |
| `QwenScenarioMonitor.record_routing` / 74 | `command_id is not None AND not normalized_id` | `raise ValueError('command_id must be non-empty when provided')` |
| `QwenScenarioMonitor.record_plan` / 81 | `not isinstance(plan, Mapping)` | `raise TypeError('plan must be a mapping')` |
| `QwenScenarioMonitor.record_behavior` / 97 | `not normalized` | `raise ValueError('behavior must be non-empty')` |
