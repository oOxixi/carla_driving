# qwen_fault_injection：功能记录

上级模块：[模块说明](../modules/vehicle-planner.md) · 实现：[integration/qwen_fault_injection.py](../../../integration/qwen_fault_injection.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [异步等待、旧结果拒绝与多层命令ID](async-plan-dispatch.md)
- [计划可行性校验与内部步骤展开](plan-validation-compilation.md)

## 功能职责与范围

Scenario-only fault injection at the Qwen client trust boundary.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

<a id="fn-scenarioqwenfaultinjector"></a>

### `ScenarioQwenFaultInjector`

源码位置：[integration/qwen_fault_injection.py 第 16 行](../../../integration/qwen_fault_injection.py#L16)。类型：`ClassDef`。

Wrap a real client while preserving production code paths after inference.

Faults are loaded only from an explicit scenario file.  A timeout delays the
worker response; a low-level fault corrupts an otherwise valid response so
the runtime validator must reject it before vehicle dispatch.

<a id="fn-scenarioqwenfaultinjector---init--"></a>

### `ScenarioQwenFaultInjector.__init__`

源码位置：[integration/qwen_fault_injection.py 第 24 行](../../../integration/qwen_fault_injection.py#L24)。类型：`FunctionDef`。

```python
ScenarioQwenFaultInjector.__init__(self, infer: Callable[[Mapping[str, Any]], Mapping[str, Any]], fault: Mapping[str, Any] | Sequence[Mapping[str, Any]], *, command_times_s: Sequence[float] | None=None, sleeper: Callable[[float], None]=time.sleep) -> None
```

包装可调用 infer，保存 scenario 中的 fault_injection 映射或列表及 command_times_s；校验支持的故障名、正 delay_ms（毫秒）、允许注入的低层字段/数值。内部调用序号从 0 开始；这是回归故障包装器，不会自动重试或修复模型响应。

<a id="fn-scenarioqwenfaultinjector--active-for-call"></a>

### `ScenarioQwenFaultInjector._active_for_call`

源码位置：[integration/qwen_fault_injection.py 第 66 行](../../../integration/qwen_fault_injection.py#L66)。类型：`FunctionDef`。

```python
ScenarioQwenFaultInjector._active_for_call(self, fault: Mapping[str, Any], call_index: int) -> bool
```

有 command_index 时按本次调用索引匹配；否则按 start_s <= command_time < start_s+duration_s 判定时间窗。没有对应 command_times_s 项时取 0 秒，不读取真实时钟。

<a id="fn-scenarioqwenfaultinjector---call--"></a>

### `ScenarioQwenFaultInjector.__call__`

源码位置：[integration/qwen_fault_injection.py 第 80 行](../../../integration/qwen_fault_injection.py#L80)。类型：`FunctionDef`。

```python
ScenarioQwenFaultInjector.__call__(self, request: Mapping[str, Any]) -> Mapping[str, Any]
```

先递增调用计数，再按活动故障延迟、抛断连异常、直接返回非法 token 或调用原 infer。响应延迟可强制超过 request 截止时间 0.05 秒；低层字段注入先深复制返回值，V2 注入第一步。sleep 阻塞工作线程，超时不会取消该调用；无锁，不保证多线程计数一致。

## 内部调用与异常路径

- `__init__` 调用：`TypeError`, `ValueError`, `any`, `callable`, `dict`, `float`, `isinstance`, `item.get`, `list`, `str`, `str(item.get('field', '')).lower`, `str(item.get('type', '')).upper`, `tuple`, `type`.
- `_active_for_call` 调用：`fault.get`, `float`, `int`, `isinstance`, `len`, `trigger.get`.
- `__call__` 调用：`ConnectionError`, `ValueError`, `copy.deepcopy`, `dict`, `float`, `isinstance`, `item.get`, `max`, `request.get`, `response.get`, `self._active_for_call`, `self._infer`, `self._sleeper`, `str`, `str(item['field']).lower`, `str(item['type']).upper`, `tuple`, `type`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__call__`，第 107 行：`ConnectionError('scenario-injected Qwen service disconnect')`。
- `__call__`，第 117 行：`ValueError('LOW_LEVEL_FIELD fault requires a ManeuverPlan V2 response')`。
- `__init__`，第 33 行：`TypeError('infer must be callable')`。
- `__init__`，第 36 行：`TypeError('fault must be a mapping or a non-empty sequence of mappings')`。
- `__init__`，第 44 行：`ValueError(f"unsupported qwen fault type: {fault_type or '<missing>'}")`。
- `__init__`，第 52 行：`ValueError(f'{fault_type} fault requires positive delay_ms')`。
- `__init__`，第 56 行：`ValueError('LOW_LEVEL_FIELD fault requires a forbidden control field')`。
- `__init__`，第 59 行：`TypeError('LOW_LEVEL_FIELD fault value must be numeric')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/tests/test_qwen_fault_injection.py](../../../integration/tests/test_qwen_fault_injection.py)
- [integration/tests/test_qwen_planner_orchestrator.py](../../../integration/tests/test_qwen_planner_orchestrator.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-planner.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-integration-qwen-fault-injection-py"></a>

### `integration/qwen_fault_injection.py`

来源 SHA256：`e71a274834fabff5705e624fc3b4b9ff739687232cc3cbd6d0f14bb6dbf92315`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `ScenarioQwenFaultInjector.__init__` / 33 | `not callable(infer)` | `raise TypeError('infer must be callable')` |
| `ScenarioQwenFaultInjector.__init__` / 36 | `not raw_faults or any((not isinstance(item, Mapping) for item in raw_faults))` | `raise TypeError('fault must be a mapping or a non-empty sequence of mappings')` |
| `ScenarioQwenFaultInjector.__init__` / 44 | `fault_type not in supported` | `raise ValueError(f"unsupported qwen fault type: {fault_type or '<missing>'}")` |
| `ScenarioQwenFaultInjector.__init__` / 52 | `fault_type in {'TIMEOUT', 'QWEN_RESPONSE_DELAY', 'QWEN_COMMAND_DELAY'} AND type(delay_ms) not in (int, float) or isinstance(delay_ms, bool) or float(delay_ms) <= 0.0` | `raise ValueError(f'{fault_type} fault requires positive delay_ms')` |
| `ScenarioQwenFaultInjector.__init__` / 56 | `NOT (fault_type in {'TIMEOUT', 'QWEN_RESPONSE_DELAY', 'QWEN_COMMAND_DELAY'}) AND fault_type == 'LOW_LEVEL_FIELD' AND field not in _LOW_LEVEL_FIELDS` | `raise ValueError('LOW_LEVEL_FIELD fault requires a forbidden control field')` |
| `ScenarioQwenFaultInjector.__init__` / 59 | `NOT (fault_type in {'TIMEOUT', 'QWEN_RESPONSE_DELAY', 'QWEN_COMMAND_DELAY'}) AND fault_type == 'LOW_LEVEL_FIELD' AND type(value) not in (int, float) or isinstance(value, bool)` | `raise TypeError('LOW_LEVEL_FIELD fault value must be numeric')` |
| `ScenarioQwenFaultInjector.__call__` / 107 | `NOT (fault_type in {'TIMEOUT', 'QWEN_RESPONSE_DELAY', 'QWEN_COMMAND_DELAY'}) AND fault_type == 'QWEN_SERVICE_DISCONNECT'` | `raise ConnectionError('scenario-injected Qwen service disconnect')` |
| `ScenarioQwenFaultInjector.__call__` / 117 | `not isinstance(steps, list) or not steps or (not isinstance(steps[0], dict))` | `raise ValueError('LOW_LEVEL_FIELD fault requires a ManeuverPlan V2 response')` |
