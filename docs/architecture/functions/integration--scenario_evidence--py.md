# scenario_evidence：功能记录

上级模块：[模块说明](../modules/vehicle-scenarios.md) · 实现：[integration/scenario_evidence.py](../../../integration/scenario_evidence.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [场景触发、车辆行为与验收分离](scenario-evidence-contract.md)

## 功能职责与范围

Auditable evidence and score summaries for CARLA scenario runs.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `FrameTiming.decision_start_ns: int`；默认：`未在声明处设置`。
- `FrameTiming.decision_end_ns: int`；默认：`未在声明处设置`。
- `FrameTiming.control_applied_ns: int`；默认：`未在声明处设置`。
- `FrameTiming.sensor_ready_ns: int | None`；默认：`None`。
- `FrameTiming.simulator_tick_start_ns: int | None`；默认：`None`。
- `FrameTiming.simulator_tick_end_ns: int | None`；默认：`None`。
- `FrameTiming.perception_start_ns: int | None`；默认：`None`。

## 功能入口：输入、输出与实现说明

### `FrameTiming`

源码位置：[integration/scenario_evidence.py 第 33 行](../../../integration/scenario_evidence.py#L33)。类型：`ClassDef`。

Monotonic timestamps around one control decision.

All values use the same monotonic clock.  Optional sensor timing allows an
initial runner implementation to omit sensor instrumentation without
fabricating a latency value.

### `FrameTiming.__post_init__`

源码位置：[integration/scenario_evidence.py 第 49 行](../../../integration/scenario_evidence.py#L49)。类型：`FunctionDef`。

```python
FrameTiming.__post_init__(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `FrameTiming.to_dict`

源码位置：[integration/scenario_evidence.py 第 78 行](../../../integration/scenario_evidence.py#L78)。类型：`FunctionDef`。

```python
FrameTiming.to_dict(self) -> dict[str, float | int | None]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_jsonable`

源码位置：[integration/scenario_evidence.py 第 117 行](../../../integration/scenario_evidence.py#L117)。类型：`FunctionDef`。

```python
_jsonable(value: Any) -> Any
```

Convert controller contracts to strict JSON without lossy string reprs.

### `_field`

源码位置：[integration/scenario_evidence.py 第 139 行](../../../integration/scenario_evidence.py#L139)。类型：`FunctionDef`。

```python
_field(value: object, name: str, default: Any=None) -> Any
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioEvidenceRecorder`

源码位置：[integration/scenario_evidence.py 第 145 行](../../../integration/scenario_evidence.py#L145)。类型：`ClassDef`。

Write a unified JSONL audit trail and an adjacent score summary.

The class is deliberately stateful: invalid event order raises immediately,
preventing a successful-looking log that omitted ``run_start`` or emitted
frames after a terminal record.

### `ScenarioEvidenceRecorder.__init__`

源码位置：[integration/scenario_evidence.py 第 153 行](../../../integration/scenario_evidence.py#L153)。类型：`FunctionDef`。

```python
ScenarioEvidenceRecorder.__init__(self, path: str | Path, *, scorer: OfficialScorer | None=None, clock_ns: Any=time.monotonic_ns) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioEvidenceRecorder.run_id`

源码位置：[integration/scenario_evidence.py 第 217 行](../../../integration/scenario_evidence.py#L217)。类型：`FunctionDef`。

```python
ScenarioEvidenceRecorder.run_id(self) -> str | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioEvidenceRecorder.start_run`

源码位置：[integration/scenario_evidence.py 第 220 行](../../../integration/scenario_evidence.py#L220)。类型：`FunctionDef`。

```python
ScenarioEvidenceRecorder.start_run(self, *, scenario_id: str, difficulty: str='basic', config: Mapping[str, object] | None=None, expected_route_deviation: bool=False, run_id: str | None=None) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioEvidenceRecorder.record_command`

源码位置：[integration/scenario_evidence.py 第 238 行](../../../integration/scenario_evidence.py#L238)。类型：`FunctionDef`。

```python
ScenarioEvidenceRecorder.record_command(self, command: Mapping[str, object], *, disposition: str, adapted_command: object | None=None, received_ns: int | None=None, submitted_sim_time_s: float | None=None) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioEvidenceRecorder.record_qwen_event`

源码位置：[integration/scenario_evidence.py 第 267 行](../../../integration/scenario_evidence.py#L267)。类型：`FunctionDef`。

```python
ScenarioEvidenceRecorder.record_qwen_event(self, *, request_id: str, status: str, context: Mapping[str, object] | None=None, high_level_command: Mapping[str, object] | None=None, runtime_command: Mapping[str, object] | None=None, trace: object | None=None, error: str | None=None) -> None
```

Record a remote Qwen request/result without storing credentials.

### `ScenarioEvidenceRecorder.record_qwen_trajectory`

源码位置：[integration/scenario_evidence.py 第 304 行](../../../integration/scenario_evidence.py#L304)。类型：`FunctionDef`。

```python
ScenarioEvidenceRecorder.record_qwen_trajectory(self, *, command_id: str, request_id: str, sensor_ready_ns: int, model_completed_ns: int, trajectory_ready_ns: int, breakdown: Mapping[str, float] | None=None) -> None
```

Record the official sensor-ready to valid-trajectory boundary.

### `ScenarioEvidenceRecorder.record_frame`

源码位置：[integration/scenario_evidence.py 第 355 行](../../../integration/scenario_evidence.py#L355)。类型：`FunctionDef`。

```python
ScenarioEvidenceRecorder.record_frame(self, *, vehicle: object, scene: object, raw_control: object, final_control: object, safety_reason: str, safety_override: bool, timing: FrameTiming, safety_reason_category: str='NONE', command_id: str | None=None, fsm_state: str | None=None, longitudinal: object | None=None, lateral: object | None=None, perception_sources: Mapping[str, str] | None=None, c_safety_state: object | None=None, lane_marking_crossing_expected: bool=False) -> None
```

Record one applied control frame and update scenario aggregates.

### `ScenarioEvidenceRecorder.record_runtime_frame`

源码位置：[integration/scenario_evidence.py 第 511 行](../../../integration/scenario_evidence.py#L511)。类型：`FunctionDef`。

```python
ScenarioEvidenceRecorder.record_runtime_frame(self, result: object, scene: object, *, raw_control: object, timing: FrameTiming, command_id: str | None=None, fsm_state: str | None=None, perception_sources: Mapping[str, str] | None=None, c_safety_state: object | None=None, lane_marking_crossing_expected: bool=False) -> None
```

Convenience adapter for :class:`integration.contracts.FrameResult`.

``raw_control`` stays mandatory: silently reconstructing it from the
final steer value would make a safety takeover impossible to audit.
All terminal feedback carried by the frame is emitted exactly once.

### `ScenarioEvidenceRecorder.record_feedback`

源码位置：[integration/scenario_evidence.py 第 537 行](../../../integration/scenario_evidence.py#L537)。类型：`FunctionDef`。

```python
ScenarioEvidenceRecorder.record_feedback(self, feedback: object) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioEvidenceRecorder.record_canonical_routing`

源码位置：[integration/scenario_evidence.py 第 560 行](../../../integration/scenario_evidence.py#L560)。类型：`FunctionDef`。

```python
ScenarioEvidenceRecorder.record_canonical_routing(self, *, phase: str, command_id: str, payload: object) -> None
```

Persist A/B canonical objects without parsing their implementation.

### `ScenarioEvidenceRecorder.record_route_recovery_event`

源码位置：[integration/scenario_evidence.py 第 575 行](../../../integration/scenario_evidence.py#L575)。类型：`FunctionDef`。

```python
ScenarioEvidenceRecorder.record_route_recovery_event(self, *, event_type: str, payload: Mapping[str, object]) -> None
```

Persist route-recovery lifecycle evidence and update aggregates.

### `ScenarioEvidenceRecorder.complete`

源码位置：[integration/scenario_evidence.py 第 606 行](../../../integration/scenario_evidence.py#L606)。类型：`FunctionDef`。

```python
ScenarioEvidenceRecorder.complete(self, *, completion: bool | None=None, detail: str='', expected: Mapping[str, object] | None=None, acceptance_context: Mapping[str, object] | None=None) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioEvidenceRecorder.fail`

源码位置：[integration/scenario_evidence.py 第 634 行](../../../integration/scenario_evidence.py#L634)。类型：`FunctionDef`。

```python
ScenarioEvidenceRecorder.fail(self, error: BaseException | str, *, detail: str='') -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioEvidenceRecorder.close`

源码位置：[integration/scenario_evidence.py 第 645 行](../../../integration/scenario_evidence.py#L645)。类型：`FunctionDef`。

```python
ScenarioEvidenceRecorder.close(self) -> None
```

Close an unterminated recorder as a failed run, preserving evidence.

### `ScenarioEvidenceRecorder._summary`

源码位置：[integration/scenario_evidence.py 第 650 行](../../../integration/scenario_evidence.py#L650)。类型：`FunctionDef`。

```python
ScenarioEvidenceRecorder._summary(self, *, status: str, completion: bool, completion_basis: str, detail: str) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioEvidenceRecorder._acceptance_metrics`

源码位置：[integration/scenario_evidence.py 第 723 行](../../../integration/scenario_evidence.py#L723)。类型：`FunctionDef`。

```python
ScenarioEvidenceRecorder._acceptance_metrics(self, expected: Mapping[str, object], context: Mapping[str, object]) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioEvidenceRecorder._route_recovery_succeeded`

源码位置：[integration/scenario_evidence.py 第 893 行](../../../integration/scenario_evidence.py#L893)。类型：`FunctionDef`。

```python
ScenarioEvidenceRecorder._route_recovery_succeeded(self) -> bool
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioEvidenceRecorder._write`

源码位置：[integration/scenario_evidence.py 第 903 行](../../../integration/scenario_evidence.py#L903)。类型：`FunctionDef`。

```python
ScenarioEvidenceRecorder._write(self, record_type: str, **fields: Any) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioEvidenceRecorder._write_summary`

源码位置：[integration/scenario_evidence.py 第 919 行](../../../integration/scenario_evidence.py#L919)。类型：`FunctionDef`。

```python
ScenarioEvidenceRecorder._write_summary(self, summary: Mapping[str, Any]) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioEvidenceRecorder._ensure_active`

源码位置：[integration/scenario_evidence.py 第 925 行](../../../integration/scenario_evidence.py#L925)。类型：`FunctionDef`。

```python
ScenarioEvidenceRecorder._ensure_active(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioEvidenceRecorder._finish`

源码位置：[integration/scenario_evidence.py 第 931 行](../../../integration/scenario_evidence.py#L931)。类型：`FunctionDef`。

```python
ScenarioEvidenceRecorder._finish(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioEvidenceRecorder._minimum`

源码位置：[integration/scenario_evidence.py 第 938 行](../../../integration/scenario_evidence.py#L938)。类型：`FunctionDef`。

```python
ScenarioEvidenceRecorder._minimum(current: float | None, candidate: object) -> float | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioEvidenceRecorder._average`

源码位置：[integration/scenario_evidence.py 第 947 行](../../../integration/scenario_evidence.py#L947)。类型：`FunctionDef`。

```python
ScenarioEvidenceRecorder._average(values: list[float]) -> float | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioEvidenceRecorder._percentile`

源码位置：[integration/scenario_evidence.py 第 951 行](../../../integration/scenario_evidence.py#L951)。类型：`FunctionDef`。

```python
ScenarioEvidenceRecorder._percentile(values: list[float], quantile: float) -> float | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioEvidenceRecorder._command_latency`

源码位置：[integration/scenario_evidence.py 第 962 行](../../../integration/scenario_evidence.py#L962)。类型：`FunctionDef`。

```python
ScenarioEvidenceRecorder._command_latency(command: Mapping[str, Any], received_ns: int) -> dict[str, float | None]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioEvidenceRecorder._latency_origin_ns`

源码位置：[integration/scenario_evidence.py 第 974 行](../../../integration/scenario_evidence.py#L974)。类型：`FunctionDef`。

```python
ScenarioEvidenceRecorder._latency_origin_ns(command_record: Mapping[str, Any]) -> int | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_jsonable` 调用：`TypeError`, `ValueError`, `_jsonable`, `asdict`, `callable`, `getattr`, `is_dataclass`, `isinstance`, `math.isfinite`, `str`, `to_dict`, `type`, `value.items`.
- `_field` 调用：`getattr`, `isinstance`, `value.get`.
- `__post_init__` 调用：`ValueError`, `sorted`, `type`, `values.items`.
- `__init__` 调用：`OfficialScorer`, `Path`, `self.path.with_suffix`, `set`.
- `start_run` 调用：`RuntimeError`, `ValueError`, `bool`, `dict`, `self._write`, `self.path.open`, `self.path.parent.mkdir`, `uuid4`.
- `record_command` 调用：`ValueError`, `_jsonable`, `command.get`, `self._clock_ns`, `self._command_latency`, `self._ensure_active`, `self._write`, `type`.
- `record_qwen_event` 调用：`ValueError`, `_jsonable`, `high_level_command.get`, `isinstance`, `self._ensure_active`, `self._safety_reasons.add`, `self._write`, `str`, `str(high_level_command.get('action', '')).strip`, `str(high_level_command.get('action', '')).strip().upper`, `str(high_level_command.get('decision_source', '')).strip`, `str(high_level_command.get('decision_source', '')).strip().upper`, `str(status).strip`, `str(status).strip().upper`, `type`.
- `record_qwen_trajectory` 调用：`ValueError`, `any`, `breakdown.items`, `float`, `isinstance`, `math.isfinite`, `self._ensure_active`, `self._qwen_model_ms.append`, `self._qwen_sensor_to_trajectory_ms.append`, `self._write`, `type`.
- `record_frame` 调用：`TypeError`, `_field`, `_jsonable`, `abs`, `all`, `bool`, `command_record.get`, `command_record.get('command', {}).get`, `float`, `int`, `isinstance`, `math.isfinite`, `max`, `self._commands.values`, `self._cross_track_errors_m.append`, `self._ensure_active`, `self._frame_decision_ms.append`, `self._frame_perception_acquire_ms.append`, `self._frame_pipeline_active_ms.append`, `self._frame_sensor_to_control_ms.append`, `self._frame_simulator_tick_ms.append`, `self._frame_speeds_mps.append`, `self._frame_times_s.append`, `self._lane_offsets_m.append`, `self._latency_origin_ns`, `self._minimum`, `self._safety_reasons.add`, `self._steer_samples.append`, `self._write`, `str`, `str(command_record.get('command', {}).get('intent', '')).upper`, `timing.to_dict`, `tuple`, `type`.
- `record_runtime_frame` 调用：`_field`, `self.record_feedback`, `self.record_frame`.
- `record_feedback` 调用：`TypeError`, `_field`, `_jsonable`, `isinstance`, `safety_event.get`, `self._ensure_active`, `self._feedback_keys.add`, `self._safety_reasons.add`, `self._write`, `type`.
- `record_canonical_routing` 调用：`ValueError`, `_jsonable`, `self._ensure_active`, `self._write`, `type`.
- `record_route_recovery_event` 调用：`ValueError`, `dict`, `isinstance`, `max`, `normalized.get`, `self._ensure_active`, `self._route_recovery_states.append`, `self._write`, `str`, `str(normalized.get('status', '')).strip`, `str(normalized.get('status', '')).strip().upper`, `type`.
- `complete` 调用：`any`, `bool`, `evaluate_expected`, `self._acceptance_metrics`, `self._ensure_active`, `self._finish`, `self._summary`, `self._terminal_statuses.values`, `self._write`, `self._write_summary`.
- `fail` 调用：`isinstance`, `self._ensure_active`, `self._finish`, `self._summary`, `self._write`, `self._write_summary`, `str`, `type`.
- `close` 调用：`self.fail`.
- `_summary` 调用：`dict`, `len`, `list`, `max`, `self._average`, `self._commands.values`, `self._percentile`, `self._route_recovery_succeeded`, `self.scorer.score_scenario`, `self.scorer.score_scenario(result).to_dict`, `self.scorer.summarize`, `sorted`.
- `_acceptance_metrics` 调用：`_field`, `abs`, `all`, `any`, `bool`, `context.get`, `dict`, `float`, `int`, `len`, `list`, `math.cos`, `math.radians`, `math.sin`, `max`, `range`, `record.get`, `self._average`, `self._commands.values`, `self._route_recovery_succeeded`, `self._terminal_statuses.get`, `self.path.exists`, `sorted`, `str`, `str(record.get('disposition', '')).startswith`, `type`, `zip`.
- `_route_recovery_succeeded` 调用：`any`, `self._route_recovery_states.index`.
- `_write` 调用：`RuntimeError`, `_jsonable`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `json.dumps`, `self._handle.flush`, `self._handle.write`.
- `_write_summary` 调用：`_jsonable`, `json.dumps`, `self.summary_path.write_text`.
- `_ensure_active` 调用：`RuntimeError`.
- `_finish` 调用：`self._handle.close`.
- `_minimum` 调用：`ValueError`, `float`, `math.isfinite`, `min`.
- `_average` 调用：`len`, `sum`.
- `_percentile` 调用：`int`, `len`, `min`, `sorted`.
- `_command_latency` 调用：`command.get`, `type`.
- `_latency_origin_ns` 调用：`command.get`, `command_record.get`, `isinstance`, `type`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__post_init__`，第 61 行：`ValueError(f'{name} must be a non-negative integer or None')`。
- `__post_init__`，第 63 行：`ValueError('simulator tick timestamps must be provided together')`。
- `__post_init__`，第 65 行：`ValueError('perception_start_ns requires sensor_ready_ns')`。
- `__post_init__`，第 76 行：`ValueError('frame timestamps must be monotonic')`。
- `_ensure_active`，第 927 行：`RuntimeError('run has not started')`。
- `_ensure_active`，第 929 行：`RuntimeError('run is already terminal')`。
- `_jsonable`，第 123 行：`ValueError('evidence values must be finite')`。
- `_jsonable`，第 136 行：`TypeError(f'unsupported evidence value: {type(value).__name__}')`。
- `_minimum`，第 943 行：`ValueError('distance and TTC metrics must be finite and non-negative')`。
- `_write`，第 905 行：`RuntimeError('run has not started')`。
- `record_canonical_routing`，第 565 行：`ValueError('phase must be a non-empty string')`。
- `record_canonical_routing`，第 567 行：`ValueError('command_id must be a non-empty string')`。
- `record_command`，第 245 行：`ValueError('command.command_id must be a non-empty string')`。
- `record_command`，第 248 行：`ValueError('received_ns must be a non-negative integer')`。
- `record_feedback`，第 543 行：`TypeError('feedback must provide string command_id and status')`。
- `record_frame`，第 369 行：`TypeError('safety_override must be bool')`。
- `record_frame`，第 374 行：`TypeError('vehicle must provide frame, sim_time_s and speed_mps')`。
- `record_qwen_event`，第 281 行：`ValueError('request_id must be a non-empty string')`。
- `record_qwen_event`，第 284 行：`ValueError('unsupported Qwen evidence status')`。
- `record_qwen_trajectory`，第 317 行：`ValueError('command_id and request_id must be non-empty')`。
- `record_qwen_trajectory`，第 320 行：`ValueError('Qwen trajectory timestamps must be non-negative integers')`。
- `record_qwen_trajectory`，第 322 行：`ValueError('Qwen trajectory timestamps must be monotonic')`。
- `record_qwen_trajectory`，第 330 行：`ValueError('Qwen timing breakdown keys must be non-empty strings')`。
- `record_qwen_trajectory`，第 337 行：`ValueError('Qwen timing breakdown values must be finite and non-negative')`。
- `record_route_recovery_event`，第 588 行：`ValueError('unsupported route recovery event type')`。
- `record_route_recovery_event`，第 592 行：`ValueError('route recovery attempt must be a non-negative integer')`。
- `record_route_recovery_event`，第 597 行：`ValueError('route recovery state requires a status')`。
- `start_run`，第 225 行：`RuntimeError('recorder can only start one run')`。
- `start_run`，第 227 行：`ValueError('scenario_id and difficulty must be non-empty')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_D/official_score.py](../../../car_control_D/official_score.py)
- [config/strategy.py](../../../config/strategy.py)
- [integration/scenario_acceptance.py](../../../integration/scenario_acceptance.py)

静态 import 消费者（含测试）：

- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/tests/test_scenario_evidence.py](../../../integration/tests/test_scenario_evidence.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-scenarios.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `integration/scenario_evidence.py`

来源 SHA256：`b4920a45a1526990beaf5ce9c53ef2e2dad9595b4bbdcf6d64d5d51267c9ac03`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `FrameTiming.decision_start_ns` | `int` | `无声明默认；构造/赋值方提供` |
| `FrameTiming.decision_end_ns` | `int` | `无声明默认；构造/赋值方提供` |
| `FrameTiming.control_applied_ns` | `int` | `无声明默认；构造/赋值方提供` |
| `FrameTiming.sensor_ready_ns` | `int &#124; None` | `None` |
| `FrameTiming.simulator_tick_start_ns` | `int &#124; None` | `None` |
| `FrameTiming.simulator_tick_end_ns` | `int &#124; None` | `None` |
| `FrameTiming.perception_start_ns` | `int &#124; None` | `None` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `FrameTiming.__post_init__` / 61 | `value is not None and (type(value) is not int or value < 0)` | `raise ValueError(f'{name} must be a non-negative integer or None')` |
| `FrameTiming.__post_init__` / 63 | `(self.simulator_tick_start_ns is None) != (self.simulator_tick_end_ns is None)` | `raise ValueError('simulator tick timestamps must be provided together')` |
| `FrameTiming.__post_init__` / 65 | `self.perception_start_ns is not None and self.sensor_ready_ns is None` | `raise ValueError('perception_start_ns requires sensor_ready_ns')` |
| `FrameTiming.__post_init__` / 76 | `ordered != sorted(ordered)` | `raise ValueError('frame timestamps must be monotonic')` |
| `_jsonable` / 123 | `type(value) is float AND not math.isfinite(value)` | `raise ValueError('evidence values must be finite')` |
| `_jsonable` / 136 | `本地无直接if；检查上下文` | `raise TypeError(f'unsupported evidence value: {type(value).__name__}')` |
| `ScenarioEvidenceRecorder.start_run` / 225 | `self._handle is not None or self._terminal` | `raise RuntimeError('recorder can only start one run')` |
| `ScenarioEvidenceRecorder.start_run` / 227 | `not scenario_id or not difficulty` | `raise ValueError('scenario_id and difficulty must be non-empty')` |
| `ScenarioEvidenceRecorder.record_command` / 245 | `type(command_id) is not str or not command_id` | `raise ValueError('command.command_id must be a non-empty string')` |
| `ScenarioEvidenceRecorder.record_command` / 248 | `type(stamp) is not int or stamp < 0` | `raise ValueError('received_ns must be a non-negative integer')` |
| `ScenarioEvidenceRecorder.record_qwen_event` / 281 | `type(request_id) is not str or not request_id` | `raise ValueError('request_id must be a non-empty string')` |
| `ScenarioEvidenceRecorder.record_qwen_event` / 284 | `normalized_status not in {'PENDING', 'READY', 'TIMEOUT', 'STALE', 'ERROR'}` | `raise ValueError('unsupported Qwen evidence status')` |
| `ScenarioEvidenceRecorder.record_qwen_trajectory` / 317 | `not command_id or not request_id` | `raise ValueError('command_id and request_id must be non-empty')` |
| `ScenarioEvidenceRecorder.record_qwen_trajectory` / 320 | `any((type(value) is not int or value < 0 for value in stamps))` | `raise ValueError('Qwen trajectory timestamps must be non-negative integers')` |
| `ScenarioEvidenceRecorder.record_qwen_trajectory` / 322 | `not sensor_ready_ns <= model_completed_ns <= trajectory_ready_ns` | `raise ValueError('Qwen trajectory timestamps must be monotonic')` |
| `ScenarioEvidenceRecorder.record_qwen_trajectory` / 330 | `breakdown is not None AND type(key) is not str or not key` | `raise ValueError('Qwen timing breakdown keys must be non-empty strings')` |
| `ScenarioEvidenceRecorder.record_qwen_trajectory` / 337 | `breakdown is not None AND type(value) not in (int, float) or isinstance(value, bool) or (not math.isfinite(float(value))) or (float(value) < 0)` | `raise ValueError('Qwen timing breakdown values must be finite and non-negative')` |
| `ScenarioEvidenceRecorder.record_frame` / 369 | `type(safety_override) is not bool` | `raise TypeError('safety_override must be bool')` |
| `ScenarioEvidenceRecorder.record_frame` / 374 | `type(frame) is not int or type(sim_time_s) not in (int, float) or type(speed_mps) not in (int, float)` | `raise TypeError('vehicle must provide frame, sim_time_s and speed_mps')` |
| `ScenarioEvidenceRecorder.record_feedback` / 543 | `type(command_id) is not str or type(status) is not str` | `raise TypeError('feedback must provide string command_id and status')` |
| `ScenarioEvidenceRecorder.record_canonical_routing` / 565 | `type(phase) is not str or not phase` | `raise ValueError('phase must be a non-empty string')` |
| `ScenarioEvidenceRecorder.record_canonical_routing` / 567 | `type(command_id) is not str or not command_id` | `raise ValueError('command_id must be a non-empty string')` |
| `ScenarioEvidenceRecorder.record_route_recovery_event` / 588 | `event_type not in {'route_recovery_state', 'route_replanned', 'route_replan_failed'}` | `raise ValueError('unsupported route recovery event type')` |
| `ScenarioEvidenceRecorder.record_route_recovery_event` / 592 | `type(attempt) is not int or isinstance(attempt, bool) or attempt < 0` | `raise ValueError('route recovery attempt must be a non-negative integer')` |
| `ScenarioEvidenceRecorder.record_route_recovery_event` / 597 | `event_type == 'route_recovery_state' AND not status` | `raise ValueError('route recovery state requires a status')` |
| `ScenarioEvidenceRecorder._write` / 905 | `self._handle is None` | `raise RuntimeError('run has not started')` |
| `ScenarioEvidenceRecorder._ensure_active` / 927 | `self._handle is None` | `raise RuntimeError('run has not started')` |
| `ScenarioEvidenceRecorder._ensure_active` / 929 | `self._terminal` | `raise RuntimeError('run is already terminal')` |
| `ScenarioEvidenceRecorder._minimum` / 943 | `not math.isfinite(value) or value < 0.0` | `raise ValueError('distance and TTC metrics must be finite and non-negative')` |
