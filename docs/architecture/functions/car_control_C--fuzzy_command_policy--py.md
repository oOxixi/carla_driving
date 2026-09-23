# fuzzy_command_policy：功能记录

上级模块：[模块说明](../modules/vehicle-longitudinal.md) · 实现：[car_control_C/fuzzy_command_policy.py](../../../car_control_C/fuzzy_command_policy.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [目标速度、跟车风险与D交接](longitudinal-safety-contract.md)

## 功能职责与范围

Deterministic safe fallback for ambiguous or untrusted voice commands.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `FuzzyCommandDecision.request: LongitudinalRequest`；默认：`未在声明处设置`。
- `FuzzyCommandDecision.intervened: bool`；默认：`未在声明处设置`。
- `FuzzyCommandDecision.requires_confirmation: bool`；默认：`未在声明处设置`。
- `FuzzyCommandDecision.output: LongitudinalOutput | None`；默认：`未在声明处设置`。
- `FuzzyCommandDecision.feedback: ExecutionFeedback | None`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

### `FuzzyCommandDecision`

源码位置：[car_control_C/fuzzy_command_policy.py 第 26 行](../../../car_control_C/fuzzy_command_policy.py#L26)。类型：`ClassDef`。

Result passed to C's controller or A's command/FSM layer.

A clear command has ``intervened=False`` and preserves the caller's request.
A policy intervention always replaces its requested speed with zero.

### `FuzzyCommandPolicy`

源码位置：[car_control_C/fuzzy_command_policy.py 第 40 行](../../../car_control_C/fuzzy_command_policy.py#L40)。类型：`ClassDef`。

Reject expiry and stop safely before requesting a voice confirmation.

### `FuzzyCommandPolicy.__init__`

源码位置：[car_control_C/fuzzy_command_policy.py 第 43 行](../../../car_control_C/fuzzy_command_policy.py#L43)。类型：`FunctionDef`。

```python
FuzzyCommandPolicy.__init__(self, config: FuzzyCommandPolicyConfig | None=None) -> None
```

保存严格策略配置并创建独立 `FollowingController` 用于当前帧 TTC；不共享主纵向控制器的历史，也不拥有命令状态机。

### `FuzzyCommandPolicy.evaluate`

源码位置：[car_control_C/fuzzy_command_policy.py 第 47 行](../../../car_control_C/fuzzy_command_policy.py#L47)。类型：`FunctionDef`。

```python
FuzzyCommandPolicy.evaluate(self, command: DrivingCommand, request: LongitudinalRequest) -> FuzzyCommandDecision
```

先校验 A 层命令/请求类型并保留前车测量计算风险。命令到期时返回零速安全请求、`REJECTED` 输出和 `EXPIRED` 反馈；低置信、歧义或显式确认时返回零速请求及 `CONFIRMING`，若低 TTC 则升级本地 `EMERGENCY_BRAKE`。可信命令原样放行且 `output=None`。

### `FuzzyCommandPolicy._safe_output`

源码位置：[car_control_C/fuzzy_command_policy.py 第 76 行](../../../car_control_C/fuzzy_command_policy.py#L76)。类型：`FunctionDef`。

```python
FuzzyCommandPolicy._safe_output(self, request: LongitudinalRequest, state: str, reason: str, risk: RiskMetrics) -> LongitudinalOutput
```

生成互斥的 `throttle=0` 与制动：静止用 hold brake，运动中用舒适/最大减速度比例，紧急风险至少提高到 emergency brake。目标速度固定零；目标加速度记录舒适减速度请求，最终控制仍可被 D 覆盖。

## 内部调用与异常路径

- `__init__` 调用：`FollowingController`, `FuzzyCommandPolicyConfig`.
- `evaluate` 调用：`ExecutionFeedback`, `FuzzyCommandDecision`, `TypeError`, `command.is_expired_at`, `isinstance`, `replace`, `self._following.risk`, `self._safe_output`.
- `_safe_output` 调用：`ControlOutput`, `LongitudinalOutput`, `max`, `min`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `evaluate`，第 49 行：`TypeError('command must be DrivingCommand')`。
- `evaluate`，第 51 行：`TypeError('request must be LongitudinalRequest')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_A/__init__.py](../../../car_control_A/__init__.py)
- [car_control_C/config.py](../../../car_control_C/config.py)
- [car_control_C/following_controller.py](../../../car_control_C/following_controller.py)

静态 import 消费者（含测试）：

- [car_control_C/__init__.py](../../../car_control_C/__init__.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-longitudinal.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_C/fuzzy_command_policy.py`

来源 SHA256：`c277076536d1dbad2cff109ab7add99f1ae9bc13c1868614b359b1d1131e7c66`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `FuzzyCommandDecision.request` | `LongitudinalRequest` | `无声明默认；构造/赋值方提供` |
| `FuzzyCommandDecision.intervened` | `bool` | `无声明默认；构造/赋值方提供` |
| `FuzzyCommandDecision.requires_confirmation` | `bool` | `无声明默认；构造/赋值方提供` |
| `FuzzyCommandDecision.output` | `LongitudinalOutput &#124; None` | `无声明默认；构造/赋值方提供` |
| `FuzzyCommandDecision.feedback` | `ExecutionFeedback &#124; None` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `FuzzyCommandPolicy.evaluate` / 49 | `not isinstance(command, DrivingCommand)` | `raise TypeError('command must be DrivingCommand')` |
| `FuzzyCommandPolicy.evaluate` / 51 | `not isinstance(request, LongitudinalRequest)` | `raise TypeError('request must be LongitudinalRequest')` |
