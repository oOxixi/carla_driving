# second_group_runtime：功能记录

上级模块：[模块说明](../modules/vehicle-planner.md) · 实现：[integration/second_group_runtime.py](../../../integration/second_group_runtime.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [异步等待、旧结果拒绝与多层命令ID](async-plan-dispatch.md)
- [计划可行性校验与内部步骤展开](plan-validation-compilation.md)

## 功能职责与范围

Live adapter from frozen A/B/C interfaces to the existing D runtime.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `CanonicalSubmission.canonical_command: Mapping[str, Any]`；默认：`未在声明处设置`。
- `CanonicalSubmission.perception_state: Mapping[str, Any]`；默认：`未在声明处设置`。
- `CanonicalSubmission.orchestration: OrchestrationResult`；默认：`未在声明处设置`。
- `CanonicalSubmission.runtime_adapted: Any | None`；默认：`未在声明处设置`。
- `CanonicalSubmission.safety_envelope: Mapping[str, Any] | None`；默认：`未在声明处设置`。
- `CanonicalSubmission.safety_adapted: Any | None`；默认：`未在声明处设置`。
- `CanonicalSubmission.feedbacks: tuple[Mapping[str, Any], ...]`；默认：`未在声明处设置`。
- `CanonicalResolution.command_id: str`；默认：`未在声明处设置`。
- `CanonicalResolution.disposition: str`；默认：`未在声明处设置`。
- `CanonicalResolution.runtime_envelope: Mapping[str, Any] | None`；默认：`未在声明处设置`。
- `CanonicalResolution.runtime_adapted: Any | None`；默认：`未在声明处设置`。
- `CanonicalResolution.feedbacks: tuple[Mapping[str, Any], ...]`；默认：`未在声明处设置`。
- `CanonicalResolution.vehicle_feedback: Any | None`；默认：`None`。
- `CanonicalResolution.orchestration: OrchestrationResult | None`；默认：`None`。
- `_PendingSlow.command_id: str`；默认：`未在声明处设置`。
- `_PendingSlow.source_text: str`；默认：`未在声明处设置`。
- `_PendingSlow.wait_command_id: str`；默认：`未在声明处设置`。
- `_PendingSlow.grounded_target_ids: tuple[str, ...]`；默认：`()`。

## 功能入口：输入、输出与实现说明

<a id="fn-canonicalsubmission"></a>

### `CanonicalSubmission`

源码位置：[integration/second_group_runtime.py 第 34 行](../../../integration/second_group_runtime.py#L34)。类型：`ClassDef`。

提交阶段记录canonical命令、perception、编排结果和安全等待envelope/授权结果；runtime_adapted当前提交路径为None，因为模型结果尚未派发。

<a id="fn-canonicalresolution"></a>

### `CanonicalResolution`

源码位置：[integration/second_group_runtime.py 第 45 行](../../../integration/second_group_runtime.py#L45)。类型：`ClassDef`。

记录原command的处置、可空运行envelope/授权/车辆反馈、canonical反馈及原编排结果；必须区分模型拒绝、车辆拒绝与READY。

<a id="fn--pendingslow"></a>

### `_PendingSlow`

源码位置：[integration/second_group_runtime.py 第 56 行](../../../integration/second_group_runtime.py#L56)。类型：`ClassDef`。

保存原command/source_text、独立wait_command_id及提交时grounded_target_ids；不是每帧更新的live actor注册表。

<a id="fn-canonicalruntimebridge"></a>

### `CanonicalRuntimeBridge`

源码位置：[integration/second_group_runtime.py 第 63 行](../../../integration/second_group_runtime.py#L63)。类型：`ClassDef`。

Coordinate canonical routing without granting Qwen direct control.

<a id="fn-canonicalruntimebridge---init--"></a>

### `CanonicalRuntimeBridge.__init__`

源码位置：[integration/second_group_runtime.py 第 66 行](../../../integration/second_group_runtime.py#L66)。类型：`FunctionDef`。

```python
CanonicalRuntimeBridge.__init__(self, vehicle_runtime: Any, orchestrator: PipelineOrchestrator, *, registry: InterfaceRegistry | None=None, clock_ns: Any=time.monotonic_ns) -> None
```

保存vehicle_runtime/orchestrator/registry/clock，建立pending字典及latest ID；不创建CARLA对象、不启动额外worker。

<a id="fn-canonicalruntimebridge-has-pending"></a>

### `CanonicalRuntimeBridge.has_pending`

源码位置：[integration/second_group_runtime.py 第 82 行](../../../integration/second_group_runtime.py#L82)。类型：`FunctionDef`。

```python
CanonicalRuntimeBridge.has_pending(self) -> bool
```

Whether a canonical command is still waiting for its Qwen result.

仅返回pending字典是否非空；不表示worker是否空闲，也不表示已派发的FSM任务是否结束。超时清pending后，后台调用仍可能运行。

<a id="fn-canonicalruntimebridge-submit"></a>

### `CanonicalRuntimeBridge.submit`

源码位置：[integration/second_group_runtime.py 第 86 行](../../../integration/second_group_runtime.py#L86)。类型：`FunctionDef`。

```python
CanonicalRuntimeBridge.submit(self, envelope: Mapping[str, Any], scene: PerceptionFrame, vehicle: Any, *, sim_time_s: float, perception_mode: str, received_at_ns: int | None=None, captured_at_ns: int | None=None, rgb_ref: str | None=None, runtime_state: Mapping[str, Any] | None=None) -> CanonicalSubmission
```

先发布/取最新canonical感知，再转换语音并更新latest ID；status非valid/ambiguous产生拒绝，否则提交编排。无论结果是否PENDING都提交独立安全等待STOP（显式紧停则EMERGENCY_STOP）；仅PENDING写pending记录。转换异常向上传播。

<a id="fn-canonicalruntimebridge-poll"></a>

### `CanonicalRuntimeBridge.poll`

源码位置：[integration/second_group_runtime.py 第 142 行](../../../integration/second_group_runtime.py#L142)。类型：`FunctionDef`。

```python
CanonicalRuntimeBridge.poll(self, scene: PerceptionFrame, vehicle: Any, *, sim_time_s: float, perception_mode: str, captured_at_ns: int | None=None, wait_timeout_ms: float=0.0) -> tuple[CanonicalResolution, ...]
```

发布新帧、消费编排结果并pop对应pending；非READY终结仍匹配的等待命令。READY先拒绝旧command，再核对首control目标在最新objects或提交grounded集合中。V2用内部qwen-step ID派发，TTL至少sum(step.timeout)+1s；转换或运行授权失败明确拒绝。当前不对后续每步做最新帧全量复验。

<a id="fn-canonicalruntimebridge-fail-all-pending"></a>

### `CanonicalRuntimeBridge.fail_all_pending`

源码位置：[integration/second_group_runtime.py 第 273 行](../../../integration/second_group_runtime.py#L273)。类型：`FunctionDef`。

```python
CanonicalRuntimeBridge.fail_all_pending(self, *, sim_time_s: float, emitted_at_ns: int | None=None, reason_code: str='RUNTIME_ENDED') -> tuple[CanonicalResolution, ...]
```

Give every still-pending canonical command one explicit terminal.

清空pending并为每个用户命令生成FAILED/RUNTIME_ENDED（reason_code可覆盖）反馈；只在当前活动命令匹配wait ID时终结等待车辆命令。返回CanonicalResolution元组，不停止worker、不等后台推理，也不结算已交FSM执行的计划。sim_time_s为仿真秒，emitted_at_ns默认注入单调时钟。

<a id="fn-canonicalruntimebridge--publish-state"></a>

### `CanonicalRuntimeBridge._publish_state`

源码位置：[integration/second_group_runtime.py 第 299 行](../../../integration/second_group_runtime.py#L299)。类型：`FunctionDef`。

```python
CanonicalRuntimeBridge._publish_state(self, scene: PerceptionFrame, vehicle: Any, perception_mode: str, captured_at_ns: int) -> Mapping[str, Any]
```

转换PerceptionFrame并publish_perception，再latest_perception取尽队列；取不到抛RuntimeError。此方法消费队列，并非只发布。

<a id="fn-canonicalruntimebridge--runtime-envelope"></a>

### `CanonicalRuntimeBridge._runtime_envelope`

源码位置：[integration/second_group_runtime.py 第 319 行](../../../integration/second_group_runtime.py#L319)。类型：`FunctionDef`。

```python
CanonicalRuntimeBridge._runtime_envelope(self, control: Mapping[str, Any], original: Mapping[str, Any]) -> dict[str, Any]
```

将control转语音envelope，附原始音频/ASR/NLU时间戳；纯辅助转换，当前poll另有内联路径，不能因方法存在断言所有派发都保留这些时间戳。

<a id="fn-canonicalruntimebridge--pending-safety-envelope"></a>

### `CanonicalRuntimeBridge._pending_safety_envelope`

源码位置：[integration/second_group_runtime.py 第 333 行](../../../integration/second_group_runtime.py#L333)。类型：`FunctionDef`。

```python
CanonicalRuntimeBridge._pending_safety_envelope(command: Mapping[str, Any]) -> dict[str, Any]
```

生成独立UUID等待命令、3s有效期、confidence1且无需确认；紧停intent保持EMERGENCY_STOP，其他STOP，警告标记QWEN_PENDING_FAIL_CLOSED。此置信度属于确定性等待策略，不是模型置信度。

<a id="fn-canonicalruntimebridge--fail-wait-if-current"></a>

### `CanonicalRuntimeBridge._fail_wait_if_current`

源码位置：[integration/second_group_runtime.py 第 361 行](../../../integration/second_group_runtime.py#L361)。类型：`FunctionDef`。

```python
CanonicalRuntimeBridge._fail_wait_if_current(self, pending: _PendingSlow | None, command_id: str, sim_time_s: float, reason_code: str) -> Any | None
```

只有pending存在、原command仍最新且vehicle活动ID恰等wait ID时才fail_active，防止旧请求失败终结新命令；其他情况None。

<a id="fn-canonicalruntimebridge--rejection"></a>

### `CanonicalRuntimeBridge._rejection`

源码位置：[integration/second_group_runtime.py 第 379 行](../../../integration/second_group_runtime.py#L379)。类型：`FunctionDef`。

```python
CanonicalRuntimeBridge._rejection(self, command_id: str, now_ns: int, reason_code: str, detail: str) -> OrchestrationResult
```

构造REJECTED编排结果与canonical终态反馈，附队列快照，不提交推理。

<a id="fn-canonicalruntimebridge--feedback"></a>

### `CanonicalRuntimeBridge._feedback`

源码位置：[integration/second_group_runtime.py 第 394 行](../../../integration/second_group_runtime.py#L394)。类型：`FunctionDef`。

```python
CanonicalRuntimeBridge._feedback(self, command_id: str, now_ns: int, status: str, detail: str, reason_code: str) -> Mapping[str, Any]
```

Schema验证execution_feedback，仅终态填terminal_reason；action时间/latency/safety_event为空，不伪造已应用控制的证据。

## 内部调用与异常路径

- `__init__` 调用：`InterfaceRegistry`.
- `has_pending` 调用：`bool`.
- `submit` 调用：`CanonicalSubmission`, `_PendingSlow`, `envelope.get`, `isinstance`, `runtime_state.get`, `self._clock_ns`, `self._pending_safety_envelope`, `self._publish_state`, `self._rejection`, `self.orchestrator.submit_command`, `self.vehicle_runtime.submit_voice`, `str`, `str(envelope.get('status', 'valid')).lower`, `tuple`, `voice_envelope_to_driving_command`.
- `poll` 调用：`CanonicalResolution`, `compiled_steps[0].get`, `control_command_to_voice_envelope`, `current_targets.update`, `float`, `isinstance`, `max`, `resolutions.append`, `result.compiled_plan.get`, `result.control_command.get`, `result.control_command['target'].get`, `self._clock_ns`, `self._fail_wait_if_current`, `self._feedback`, `self._pending.pop`, `self._publish_state`, `self.orchestrator.poll_slow`, `self.vehicle_runtime.submit_voice`, `step.get`, `str`, `str(result.control_command.get('behavior', '')).upper`, `sum`, `tuple`.
- `fail_all_pending` 调用：`CanonicalResolution`, `resolutions.append`, `self._clock_ns`, `self._fail_wait_if_current`, `self._feedback`, `self._pending.items`, `tuple`.
- `_publish_state` 调用：`RuntimeError`, `perception_frame_to_state`, `self.orchestrator.latest_perception`, `self.orchestrator.publish_perception`.
- `_runtime_envelope` 调用：`control_command_to_voice_envelope`, `original.get`, `str`.
- `_pending_safety_envelope` 调用：`command.get`, `str`, `str(command.get('intent', '')).upper`, `uuid4`.
- `_fail_wait_if_current` 调用：`self.vehicle_runtime.fail_active`.
- `_rejection` 调用：`OrchestrationResult`, `self._feedback`, `self.orchestrator.queue_snapshot`.
- `_feedback` 调用：`self.registry.validate`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_publish_state`，第 316 行：`RuntimeError('canonical perception queue lost the published state')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [integration/canonical_bridge.py](../../../integration/canonical_bridge.py)
- [integration/contracts.py](../../../integration/contracts.py)
- [runtime/interface_registry.py](../../../runtime/interface_registry.py)
- [runtime/orchestrator.py](../../../runtime/orchestrator.py)

静态 import 消费者（含测试）：

- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/tests/test_second_group_runtime.py](../../../integration/tests/test_second_group_runtime.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-planner.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-integration-second-group-runtime-py"></a>

### `integration/second_group_runtime.py`

来源 SHA256：`1e66d4101d8c9ebfee02d475b3a84fef70e69674e3d2c93a06240325ce1814b2`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `CanonicalSubmission.canonical_command` | `Mapping[str, Any]` | `无声明默认；构造/赋值方提供` |
| `CanonicalSubmission.perception_state` | `Mapping[str, Any]` | `无声明默认；构造/赋值方提供` |
| `CanonicalSubmission.orchestration` | `OrchestrationResult` | `无声明默认；构造/赋值方提供` |
| `CanonicalSubmission.runtime_adapted` | `Any &#124; None` | `无声明默认；构造/赋值方提供` |
| `CanonicalSubmission.safety_envelope` | `Mapping[str, Any] &#124; None` | `无声明默认；构造/赋值方提供` |
| `CanonicalSubmission.safety_adapted` | `Any &#124; None` | `无声明默认；构造/赋值方提供` |
| `CanonicalSubmission.feedbacks` | `tuple[Mapping[str, Any], ...]` | `无声明默认；构造/赋值方提供` |
| `CanonicalResolution.command_id` | `str` | `无声明默认；构造/赋值方提供` |
| `CanonicalResolution.disposition` | `str` | `无声明默认；构造/赋值方提供` |
| `CanonicalResolution.runtime_envelope` | `Mapping[str, Any] &#124; None` | `无声明默认；构造/赋值方提供` |
| `CanonicalResolution.runtime_adapted` | `Any &#124; None` | `无声明默认；构造/赋值方提供` |
| `CanonicalResolution.feedbacks` | `tuple[Mapping[str, Any], ...]` | `无声明默认；构造/赋值方提供` |
| `CanonicalResolution.vehicle_feedback` | `Any &#124; None` | `None` |
| `CanonicalResolution.orchestration` | `OrchestrationResult &#124; None` | `None` |
| `_PendingSlow.command_id` | `str` | `无声明默认；构造/赋值方提供` |
| `_PendingSlow.source_text` | `str` | `无声明默认；构造/赋值方提供` |
| `_PendingSlow.wait_command_id` | `str` | `无声明默认；构造/赋值方提供` |
| `_PendingSlow.grounded_target_ids` | `tuple[str, ...]` | `()` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `CanonicalRuntimeBridge._publish_state` / 316 | `latest is None` | `raise RuntimeError('canonical perception queue lost the published state')` |
