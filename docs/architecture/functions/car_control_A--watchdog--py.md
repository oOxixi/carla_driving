# watchdog：功能记录

上级模块：[模块说明](../modules/vehicle-behavior.md) · 实现：[car_control_A/watchdog.py](../../../car_control_A/watchdog.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [授权、确认、过期与停车保持](command-lifecycle.md)
- [前置条件锁存、步骤完成与重规划](maneuver-progress.md)

## 功能职责与范围

Narrow runtime health fail-safe, deliberately not D's safety arbiter.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

<a id="fn-runtimewatchdog"></a>

### `RuntimeWatchdog`

源码位置：[car_control_A/watchdog.py 第 10 行](../../../car_control_A/watchdog.py#L10)。类型：`ClassDef`。

A运行健康超时检测器，返回全刹或None，不是D SafetySupervisor，不负责感知碰撞规则。内部不锁存故障；外层ControlRuntime可将告警锁存，不能把两层恢复语义混用。

<a id="fn-runtimewatchdog---init--"></a>

### `RuntimeWatchdog.__init__`

源码位置：[car_control_A/watchdog.py 第 11 行](../../../car_control_A/watchdog.py#L11)。类型：`FunctionDef`。

```python
RuntimeWatchdog.__init__(self, *, timeout_s: float=1.0, required_modules: tuple[str, ...]=(), startup_grace_s: float=0.0, started_at_s: float=0.0) -> None
```

timeout_s默认1秒，required_modules默认空tuple，startup_grace_s/started_at_s默认0；检查timeout>0、其余>=0但未独立isfinite/type约束。required名字非空str并frozenset去重；启动截止=start+grace+timeout，无后台线程或预填心跳。

<a id="fn-runtimewatchdog--time"></a>

### `RuntimeWatchdog._time`

源码位置：[car_control_A/watchdog.py 第 24 行](../../../car_control_A/watchdog.py#L24)。类型：`FunctionDef`。

```python
RuntimeWatchdog._time(value: float, name: str) -> float
```

先float转换，再要求有限非负秒；与其他exact数值契约不同，会接受可转换数字字符串/bool。仅校验单次值，不拒绝跨调用时钟回退。

<a id="fn-runtimewatchdog-heartbeat"></a>

### `RuntimeWatchdog.heartbeat`

源码位置：[car_control_A/watchdog.py 第 30 行](../../../car_control_A/watchdog.py#L30)。类型：`FunctionDef`。

```python
RuntimeWatchdog.heartbeat(self, module: str, *, now_s: float) -> None
```

module非空str；暂停中抛RuntimeError；否则保存经_time校验的now并覆盖旧值。非required模块也记录并参加后续超时检测，未来时间戳未额外拒绝。

<a id="fn-runtimewatchdog-pause"></a>

### `RuntimeWatchdog.pause`

源码位置：[car_control_A/watchdog.py 第 37 行](../../../car_control_A/watchdog.py#L37)。类型：`FunctionDef`。

```python
RuntimeWatchdog.pause(self, *, now_s: float) -> None
```

Exclude an external wait during which the controlled system is frozen.

CARLA synchronous ``world.tick()`` can block in the renderer while
simulation time does not advance.  Counting that wait as a B/C/D
module outage creates a false permanent stop.  The caller must bracket
only the simulator/pacing wait; control, perception and logging remain
inside the active watchdog interval.

要求此前未暂停，保存经_time校验的now；暂停中heartbeat/check都会抛错，不是静默忽略。resume以暂停时长平移心跳/启动截止，只适合系统被外部tick/pacing冻结的等待。

<a id="fn-runtimewatchdog-resume"></a>

### `RuntimeWatchdog.resume`

源码位置：[car_control_A/watchdog.py 第 50 行](../../../car_control_A/watchdog.py#L50)。类型：`FunctionDef`。

```python
RuntimeWatchdog.resume(self, *, now_s: float) -> None
```

必须已暂停，now有限非负且>=暂停点；将暂停时长加到启动截止和所有已记录心跳，清暂停标志。只应排除外部冻结等待，不应覆盖仍在工作的感知/控制/日志时间。

<a id="fn-runtimewatchdog-check"></a>

### `RuntimeWatchdog.check`

源码位置：[car_control_A/watchdog.py 第 62 行](../../../car_control_A/watchdog.py#L62)。类型：`FunctionDef`。

```python
RuntimeWatchdog.check(self, *, now_s: float) -> ControlOutput | None
```

暂停中拒绝；达到启动截止（>=）且任一required从未心跳则全刹；任一已记录模块心跳年龄严格>timeout也全刹，包括非required模块。否则None；补回心跳后可恢复，函数自身不保持故障锁存。

<a id="fn-runtimewatchdog-module-failed"></a>

### `RuntimeWatchdog.module_failed`

源码位置：[car_control_A/watchdog.py 第 72 行](../../../car_control_A/watchdog.py#L72)。类型：`FunctionDef`。

```python
RuntimeWatchdog.module_failed(self, module: str, error: BaseException) -> ControlOutput
```

仅校验module名后返回全刹，error参数当前不读取/记录，也不修改心跳或故障状态；调用方必须保存异常证据并决定锁存。

<a id="fn-runtimewatchdog--full-brake"></a>

### `RuntimeWatchdog._full_brake`

源码位置：[car_control_A/watchdog.py 第 78 行](../../../car_control_A/watchdog.py#L78)。类型：`FunctionDef`。

```python
RuntimeWatchdog._full_brake() -> ControlOutput
```

返回严格ControlOutput(throttle=0,brake=1,steer=0)；不直接调用CARLA apply_control，也不代表D已仲裁或车已停稳。

## 内部调用与异常路径

- `__init__` 调用：`ValueError`, `any`, `float`, `frozenset`, `type`.
- `_time` 调用：`ValueError`, `float`, `math.isfinite`.
- `heartbeat` 调用：`RuntimeError`, `ValueError`, `self._time`, `type`.
- `pause` 调用：`RuntimeError`, `self._time`.
- `resume` 调用：`RuntimeError`, `ValueError`, `self._time`, `tuple`.
- `check` 调用：`RuntimeError`, `any`, `self._full_brake`, `self._heartbeats.values`, `self._time`.
- `module_failed` 调用：`ValueError`, `self._full_brake`, `type`.
- `_full_brake` 调用：`ControlOutput`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 14 行：`ValueError('timeout_s must be positive; grace and start must be non-negative')`。
- `__init__`，第 16 行：`ValueError('required_modules must contain non-empty strings')`。
- `_time`，第 27 行：`ValueError(f'{name} must be finite and non-negative')`。
- `check`，第 64 行：`RuntimeError('cannot check watchdog while it is paused')`。
- `heartbeat`，第 32 行：`ValueError('module must be a non-empty string')`。
- `heartbeat`，第 34 行：`RuntimeError('cannot record a heartbeat while watchdog is paused')`。
- `module_failed`，第 74 行：`ValueError('module must be a non-empty string')`。
- `pause`，第 47 行：`RuntimeError('watchdog is already paused')`。
- `resume`，第 52 行：`RuntimeError('watchdog is not paused')`。
- `resume`，第 55 行：`ValueError('resume time must not precede pause time')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_A/contracts.py](../../../car_control_A/contracts.py)

静态 import 消费者（含测试）：

- [car_control_A/tests/test_ac_integration.py](../../../car_control_A/tests/test_ac_integration.py)
- [car_control_A/tests/test_watchdog.py](../../../car_control_A/tests/test_watchdog.py)
- [integration/carla_runner.py](../../../integration/carla_runner.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-behavior.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-car-control-a-watchdog-py"></a>

### `car_control_A/watchdog.py`

来源 SHA256：`a3bf6559d19b0d587411d9cd18559355a8a45080a3c2a331daf56d07f5ff8630`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `RuntimeWatchdog.__init__` / 14 | `timeout_s <= 0.0 or startup_grace_s < 0.0 or started_at_s < 0.0` | `raise ValueError('timeout_s must be positive; grace and start must be non-negative')` |
| `RuntimeWatchdog.__init__` / 16 | `any((type(module) is not str or not module for module in required_modules))` | `raise ValueError('required_modules must contain non-empty strings')` |
| `RuntimeWatchdog._time` / 27 | `not math.isfinite(converted) or converted < 0.0` | `raise ValueError(f'{name} must be finite and non-negative')` |
| `RuntimeWatchdog.heartbeat` / 32 | `type(module) is not str or not module` | `raise ValueError('module must be a non-empty string')` |
| `RuntimeWatchdog.heartbeat` / 34 | `self._paused_at_s is not None` | `raise RuntimeError('cannot record a heartbeat while watchdog is paused')` |
| `RuntimeWatchdog.pause` / 47 | `self._paused_at_s is not None` | `raise RuntimeError('watchdog is already paused')` |
| `RuntimeWatchdog.resume` / 52 | `self._paused_at_s is None` | `raise RuntimeError('watchdog is not paused')` |
| `RuntimeWatchdog.resume` / 55 | `resumed_at_s < self._paused_at_s` | `raise ValueError('resume time must not precede pause time')` |
| `RuntimeWatchdog.check` / 64 | `self._paused_at_s is not None` | `raise RuntimeError('cannot check watchdog while it is paused')` |
| `RuntimeWatchdog.module_failed` / 74 | `type(module) is not str or not module` | `raise ValueError('module must be a non-empty string')` |
