# scenario_extensions：功能记录

上级模块：[模块说明](../modules/vehicle-scenarios.md) · 实现：[integration/scenario_extensions.py](../../../integration/scenario_extensions.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [场景触发、车辆行为与验收分离](scenario-evidence-contract.md)

## 功能职责与范围

Executable acceptance-suite v2 extensions.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `ExtensionFrameState.trigger_context: dict[str, object]`；默认：`未在声明处设置`。
- `ExtensionFrameState.active_faults: tuple[dict[str, Any], ...]`；默认：`未在声明处设置`。
- `ExtensionFrameState.newly_active_fault_ids: tuple[str, ...]`；默认：`未在声明处设置`。
- `ExtensionFrameState.newly_recovered_fault_ids: tuple[str, ...]`；默认：`未在声明处设置`。
- `ExtensionFrameState.speed_limit_mps: float | None`；默认：`未在声明处设置`。
- `ExtensionFrameState.speed_limit_overrides_map: bool`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

### `missing_runtime_requirements`

源码位置：[integration/scenario_extensions.py 第 46 行](../../../integration/scenario_extensions.py#L46)。类型：`FunctionDef`。

```python
missing_runtime_requirements(extensions: Mapping[str, Any]) -> tuple[str, ...]
```

读取 `extensions.runtime_support.requirements`，要求为非字符串 sequence，返回去重排序后不在 `IMPLEMENTED_RUNTIME_REQUIREMENTS` 中的名称。缺少 support/requirements 视为空；这里只核对声明名称，不证明每项场景运行已通过。

### `ExtensionFrameState`

源码位置：[integration/scenario_extensions.py 第 55 行](../../../integration/scenario_extensions.py#L55)。类型：`ClassDef`。

冻结的单帧扩展输出：trigger context、当前 faults、刚激活/恢复的 fault ID、可选场景限速 m/s 以及是否替换地图限速。嵌套 dict 可变，状态由同一 `ScenarioExtensionRuntime` 累积。

### `ScenarioExtensionRuntime`

源码位置：[integration/scenario_extensions.py 第 64 行](../../../integration/scenario_extensions.py#L64)。类型：`ClassDef`。

State machine for scenario-only runtime extensions and their evidence.

### `ScenarioExtensionRuntime.__init__`

源码位置：[integration/scenario_extensions.py 第 67 行](../../../integration/scenario_extensions.py#L67)。类型：`FunctionDef`。

```python
ScenarioExtensionRuntime.__init__(self, extensions: Mapping[str, Any]) -> None
```

验证 extensions 为 mapping 且声明 requirement 全部已实现，复制顶层配置，解析 faults sequence，并初始化命令/phase、Qwen、actor、fault、速度/灯态、紧急响应、路线与 RSS 等跨帧聚合状态。非 mapping fault 项会被静默忽略；实例只服务一个场景且无 reset/线程同步。

### `ScenarioExtensionRuntime._rss_mb`

源码位置：[integration/scenario_extensions.py 第 170 行](../../../integration/scenario_extensions.py#L170)。类型：`FunctionDef`。

```python
ScenarioExtensionRuntime._rss_mb() -> float
```

尝试用 `resource.getrusage(RUSAGE_SELF).ru_maxrss` 换算 MB，Windows 与非 Windows 使用不同分母；模块/OS/值异常返回0。ru_maxrss 通常是进程历史峰值，不是当前占用，跨场景同进程的 growth 证据有平台与基线限制。

### `ScenarioExtensionRuntime.qwen_faults`

源码位置：[integration/scenario_extensions.py 第 179 行](../../../integration/scenario_extensions.py#L179)。类型：`FunctionDef`。

```python
ScenarioExtensionRuntime.qwen_faults(self) -> tuple[dict[str, Any], ...]
```

筛选 fault.type 小写以 `qwen_` 开头的配置并返回 tuple；元素仍是初始化时的浅复制 dict，可被外部修改。

### `ScenarioExtensionRuntime.weather_parameters`

源码位置：[integration/scenario_extensions.py 第 186 行](../../../integration/scenario_extensions.py#L186)。类型：`FunctionDef`。

```python
ScenarioExtensionRuntime.weather_parameters(self) -> dict[str, float]
```

读取 `extensions.weather_parameters`，要求 mapping，并把键转字符串、值转 float 返回新字典。未检查有限性或 CARLA WeatherParameters 是否支持该键。

### `ScenarioExtensionRuntime.route_loop`

源码位置：[integration/scenario_extensions.py 第 193 行](../../../integration/scenario_extensions.py#L193)。类型：`FunctionDef`。

```python
ScenarioExtensionRuntime.route_loop(self) -> bool
```

当 `extensions.route_policy` 是 mapping 时返回其 `loop` 的 Python bool，否则 false。字符串 `"false"` 会成为真，场景 schema 应传真实布尔值。

### `ScenarioExtensionRuntime.note_command_submitted`

源码位置：[integration/scenario_extensions.py 第 197 行](../../../integration/scenario_extensions.py#L197)。类型：`FunctionDef`。

```python
ScenarioExtensionRuntime.note_command_submitted(self, command: Mapping[str, object], *, qwen: bool) -> None
```

登记 command ID/intent/当前 elapsed、phase 的提交里程与近10秒接近速度、活动 phase 和目标速度；累计确认、Qwen请求、停止/重启/减速状态。速度按 unit 转成 km/h，但未校验有限性；重复 ID 会再次进入提交顺序列表。

### `ScenarioExtensionRuntime.note_terminal`

源码位置：[integration/scenario_extensions.py 第 242 行](../../../integration/scenario_extensions.py#L242)。类型：`FunctionDef`。

```python
ScenarioExtensionRuntime.note_terminal(self, command_id: str, status: object) -> None
```

把 command ID 加入 terminal set，若已绑定 phase 则标记 terminal/completed 并结束活动 phase；按规范化 status 累计计数，SUCCEEDED 记录当前 elapsed。方法名虽用于 Qwen 统计，但不验证该 ID 曾以 qwen=true 提交，也不限制 status 为终态。

### `ScenarioExtensionRuntime.note_qwen_plan`

源码位置：[integration/scenario_extensions.py 第 255 行](../../../integration/scenario_extensions.py#L255)。类型：`FunctionDef`。

```python
ScenarioExtensionRuntime.note_qwen_plan(self, plan: Mapping[str, Any], *, elapsed_s: float | None=None, target_aliases: Mapping[str, str] | None=None) -> None
```

Collect actions and auditable sensor-to-scenario target bindings.

### `ScenarioExtensionRuntime.note_qwen_plan.walk`

源码位置：[integration/scenario_extensions.py 第 271 行](../../../integration/scenario_extensions.py#L271)。类型：`FunctionDef`。

```python
ScenarioExtensionRuntime.note_qwen_plan.walk(value: Any, key: str='') -> None
```

递归遍历 plan mapping/sequence，收集 behavior/action/intent，大写保存；收集三种目标 ID 并按 sensor→scenario alias 同时加入映射值；目标速度 m/s 转 km/h、kph 原值保存。它是宽松证据提取，不验证 ManeuverPlan schema，也可能从非执行元数据中采到同名键。

### `ScenarioExtensionRuntime.note_qwen_resolution`

源码位置：[integration/scenario_extensions.py 第 291 行](../../../integration/scenario_extensions.py#L291)。类型：`FunctionDef`。

```python
ScenarioExtensionRuntime.note_qwen_resolution(self, *, disposition: str, reason_code: str | None, applied: bool, command_id: str | None=None) -> None
```

记录 disposition/reason，并通过字符串 token 统计 stale/late/invalid/timeout；applied 时增加 vehicle-advance、当前 elapsed、按 command 的 applied 时间和最新提交索引。invalid 还会因场景配置存在 qwen_invalid_token fault 而计数，因此这是验收事件分类，不是纯模型响应解析。

### `ScenarioExtensionRuntime.note_maneuver_terminal_reason`

源码位置：[integration/scenario_extensions.py 第 329 行](../../../integration/scenario_extensions.py#L329)。类型：`FunctionDef`。

```python
ScenarioExtensionRuntime.note_maneuver_terminal_reason(self, reason_code: str | None) -> None
```

Preserve downstream FSM rejection/failure reasons for acceptance.

Qwen resolution records why a plan was accepted or rejected at the
model boundary.  A safe-gap decision can only be resolved later by the
execution FSM, so its terminal reason is separate evidence and must not
be counted as another Qwen request or outcome.

### `ScenarioExtensionRuntime.note_phase_completed`

源码位置：[integration/scenario_extensions.py 第 341 行](../../../integration/scenario_extensions.py#L341)。类型：`FunctionDef`。

```python
ScenarioExtensionRuntime.note_phase_completed(self, phase_id: str) -> None
```

strip phase ID，非空时加入 completed set；不要求 phase 在计划或命令映射中存在，也不自动加入 terminal trigger set。

### `ScenarioExtensionRuntime.restore_terminal_phase`

源码位置：[integration/scenario_extensions.py 第 346 行](../../../integration/scenario_extensions.py#L346)。类型：`FunctionDef`。

```python
ScenarioExtensionRuntime.restore_terminal_phase(self, phase_id: str) -> None
```

Restore trigger state from a verified earlier run segment only.

### `ScenarioExtensionRuntime.note_actor_trigger`

源码位置：[integration/scenario_extensions.py 第 354 行](../../../integration/scenario_extensions.py#L354)。类型：`FunctionDef`。

```python
ScenarioExtensionRuntime.note_actor_trigger(self, actor_id: str, *, elapsed_s: float | None=None) -> None
```

strip actor ID，非空时加入触发集合，并用显式 elapsed 或当前 last elapsed 记录首次危险时间；后续同 ID 不覆盖首次时间。未校验时间有限/非负。

### `ScenarioExtensionRuntime.note_perception_observation`

源码位置：[integration/scenario_extensions.py 第 363 行](../../../integration/scenario_extensions.py#L363)。类型：`FunctionDef`。

```python
ScenarioExtensionRuntime.note_perception_observation(self, *, elapsed_s: float, detected_actor_ids: Sequence[str]) -> None
```

Record the first sensor-derived observation after an actor hazard starts.

### `ScenarioExtensionRuntime.note_front_path_observation`

源码位置：[integration/scenario_extensions.py 第 375 行](../../../integration/scenario_extensions.py#L375)。类型：`FunctionDef`。

```python
ScenarioExtensionRuntime.note_front_path_observation(self, *, elapsed_s: float, path_clear: bool) -> None
```

Track continuous sensor confirmation that the ego path is clear.

### `ScenarioExtensionRuntime.ready_emergency_recovery`

源码位置：[integration/scenario_extensions.py 第 387 行](../../../integration/scenario_extensions.py#L387)。类型：`FunctionDef`。

```python
ScenarioExtensionRuntime.ready_emergency_recovery(self, *, elapsed_s: float) -> tuple[str, float] | None
```

Return one configured hazard whose minimum stop hold has elapsed.

### `ScenarioExtensionRuntime.note_emergency_recovered`

源码位置：[integration/scenario_extensions.py 第 443 行](../../../integration/scenario_extensions.py#L443)。类型：`FunctionDef`。

```python
ScenarioExtensionRuntime.note_emergency_recovered(self, actor_id: str, *, elapsed_s: float) -> None
```

要求该 actor 已有 control-effect 时间，再以 `setdefault` 记录首次恢复 elapsed。它不自行核对 hold/clearance；调用方应先通过 `ready_emergency_recovery`。

### `ScenarioExtensionRuntime.note_actor_activated`

源码位置：[integration/scenario_extensions.py 第 449 行](../../../integration/scenario_extensions.py#L449)。类型：`FunctionDef`。

```python
ScenarioExtensionRuntime.note_actor_activated(self, actor_id: str, *, route_progress_m: float) -> None
```

要求非空 actor ID 和有限非负任务路线里程，以 `setdefault` 保存首次激活进度。重复激活不覆盖，单位为米。

### `ScenarioExtensionRuntime.note_target_lane_occupancy`

源码位置：[integration/scenario_extensions.py 第 458 行](../../../integration/scenario_extensions.py#L458)。类型：`FunctionDef`。

```python
ScenarioExtensionRuntime.note_target_lane_occupancy(self, count: int) -> None
```

要求精确非负 int 并覆盖保存当前/最近一次目标车道占用数量；不是最大值、最小值或时间序列，验收消费者读取最后一次观测。

### `ScenarioExtensionRuntime.note_mission_route_restored`

源码位置：[integration/scenario_extensions.py 第 463 行](../../../integration/scenario_extensions.py#L463)。类型：`FunctionDef`。

```python
ScenarioExtensionRuntime.note_mission_route_restored(self) -> None
```

Record a successful manoeuvre return to the saved mission route.

### `ScenarioExtensionRuntime.update_frame`

源码位置：[integration/scenario_extensions.py 第 467 行](../../../integration/scenario_extensions.py#L467)。类型：`FunctionDef`。

```python
ScenarioExtensionRuntime.update_frame(self, *, elapsed_s: float, route_progress_m: float, ego_speed_mps: float, ego_standstill_duration_s: float, actor_distances_m: Mapping[str, float], traffic_light_state: str, distance_to_stop_line_m: float | None, lane_id: str, lateral_offset_m: float | None=None, route_deviation_m: float | None=None) -> ExtensionFrameState
```

更新每帧 trigger context、actor距离最小值、车道切换、速度/phase目标接近、路线偏差、重启位移、RSS和灯态/停止线；逐 fault 评估触发及 duration 窗口，返回活动/新启停 fault 和场景限速。多个数值直接 float 转换，actor距离单独要求有限非负；elapsed/速度/里程等未统一有限性检查，调用方必须提供已验证帧状态。

### `ScenarioExtensionRuntime.note_control_observation`

源码位置：[integration/scenario_extensions.py 第 615 行](../../../integration/scenario_extensions.py#L615)。类型：`FunctionDef`。

```python
ScenarioExtensionRuntime.note_control_observation(self, *, elapsed_s: float, speed_mps: float, route_progress_m: float, brake: float, throttle: float=0.0, safety_override: bool, safety_reason: str, route_deviation_m: float | None, collision: bool=False, lateral_offset_m: float | None=None) -> None
```

Record the actually applied control outcome for acceptance timing.

### `ScenarioExtensionRuntime.actor_state`

源码位置：[integration/scenario_extensions.py 第 700 行](../../../integration/scenario_extensions.py#L700)。类型：`FunctionDef`。

```python
ScenarioExtensionRuntime.actor_state(self, actor_spec: Mapping[str, object], *, elapsed_s: float, trigger_context: Mapping[str, object]) -> dict[str, object]
```

Advance one actor event at a time and return its effective state.

### `ScenarioExtensionRuntime.evidence`

源码位置：[integration/scenario_extensions.py 第 760 行](../../../integration/scenario_extensions.py#L760)。类型：`FunctionDef`。

```python
ScenarioExtensionRuntime.evidence(self) -> dict[str, object]
```

把累计状态复制为评价字典，包括 Qwen请求/终态/行为/目标/故障、速度/灯态/phase/路线、actor距离和紧急事件六阶段时间。紧急 response 使用 perception→control 毫秒并计算插值 P95/最大值；缺失阶段保留 None，不会伪造完成。

### `ScenarioExtensionRuntime._percentile`

源码位置：[integration/scenario_extensions.py 第 881 行](../../../integration/scenario_extensions.py#L881)。类型：`FunctionDef`。

```python
ScenarioExtensionRuntime._percentile(values: Sequence[float], quantile: float) -> float | None
```

空 sequence 返回 None，单值原样返回，多值排序后按 `(n-1)*quantile` 线性插值。quantile 未限制范围，当前用于0.95。

### `ScenarioExtensionRuntime.evaluate`

源码位置：[integration/scenario_extensions.py 第 894 行](../../../integration/scenario_extensions.py#L894)。类型：`FunctionDef`。

```python
ScenarioExtensionRuntime.evaluate(self, proposed: Mapping[str, Any], *, expected_command_count: int, safety_reasons: Sequence[str]=(), oracle: Mapping[str, Any] | None=None) -> dict[str, object]
```

Evaluate every v2 proposed-acceptance field with auditable evidence.

### `ScenarioExtensionRuntime.evaluate.add`

源码位置：[integration/scenario_extensions.py 第 926 行](../../../integration/scenario_extensions.py#L926)。类型：`FunctionDef`。

```python
ScenarioExtensionRuntime.evaluate.add(key: str, passed: bool, actual: object, required: object) -> None
```

向 checks 追加 key、PASS/FAIL、actual、required 的统一条目；外层 `evaluate` 对 proposed 每个已知字段逐项调用，未知字段走失败分支。闭包不做类型转换或去重。

## 内部调用与异常路径

- `missing_runtime_requirements` 调用：`TypeError`, `extensions.get`, `isinstance`, `map`, `set`, `sorted`, `support.get`, `tuple`.
- `__init__` 调用：`', '.join`, `RuntimeError`, `TypeError`, `deque`, `dict`, `isinstance`, `missing_runtime_requirements`, `self._rss_mb`, `self.extensions.get`, `set`, `tuple`.
- `_rss_mb` 调用：`float`, `resource.getrusage`.
- `qwen_faults` 调用：`item.get`, `str`, `str(item.get('type', '')).lower`, `str(item.get('type', '')).lower().startswith`, `tuple`.
- `weather_parameters` 调用：`TypeError`, `float`, `isinstance`, `self.extensions.get`, `str`, `values.items`.
- `route_loop` 调用：`bool`, `isinstance`, `policy.get`, `self.extensions.get`.
- `note_command_submitted` 调用：`command.get`, `float`, `isinstance`, `max`, `parameters.get`, `self._active_command_phases.add`, `self._submitted_command_ids.append`, `str`, `str(command.get('intent', '')).upper`, `str(parameters.get('unit', 'km/h')).lower`, `str(parameters.get('unit', 'km/h')).lower().replace`, `type`.
- `note_terminal` 调用：`getattr`, `self._active_command_phases.discard`, `self._command_phase_by_id.get`, `self._completed_phase_ids.add`, `self._qwen_status_counts.get`, `self._qwen_terminals.add`, `self._terminal_phase_ids.add`, `str`, `str(getattr(status, 'value', status)).upper`.
- `note_qwen_plan` 调用：`child.upper`, `float`, `isinstance`, `self._qwen_behaviors.append`, `self._qwen_target_ids.add`, `self._qwen_target_speeds_kph.append`, `str`, `str(child_key).lower`, `target_aliases.items`, `type`, `value.items`, `walk`.
- `note_qwen_resolution` 调用：`any`, `item.get`, `self._qwen_applied_s.append`, `self._qwen_outcomes.append`, `self._qwen_resolution_reasons.append`, `self._submitted_command_ids.index`, `str`, `str(disposition).upper`, `str(item.get('type', '')).lower`, `str(reason_code or '').upper`.
- `note_maneuver_terminal_reason` 调用：`self._qwen_resolution_reasons.append`, `str`, `str(reason_code or '').strip`, `str(reason_code or '').strip().upper`.
- `note_phase_completed` 调用：`self._completed_phase_ids.add`, `str`, `str(phase_id).strip`.
- `restore_terminal_phase` 调用：`ValueError`, `self._completed_phase_ids.add`, `self._terminal_phase_ids.add`, `str`, `str(phase_id).strip`.
- `note_actor_trigger` 调用：`float`, `self._actor_trigger_ids.add`, `self._actor_trigger_time_s.setdefault`, `str`, `str(actor_id).strip`.
- `note_perception_observation` 调用：`float`, `self._actor_perception_time_s.setdefault`, `str`, `str(actor_id).strip`.
- `note_front_path_observation` 调用：`TypeError`, `float`, `type`.
- `ready_emergency_recovery` 调用：`TypeError`, `ValueError`, `float`, `isinstance`, `raw_policy.get`, `recovery.items`, `self._actor_control_effect_time_s.get`, `self._actor_distances_m.get`, `self.extensions.get`, `str`, `str(raw_policy.get('clearance_mode', 'actor_distance')).strip`, `str(raw_policy.get('clearance_mode', 'actor_distance')).strip().lower`.
- `note_emergency_recovered` 调用：`ValueError`, `float`, `self._actor_recovery_time_s.setdefault`, `str`, `str(actor_id).strip`.
- `note_actor_activated` 调用：`ValueError`, `float`, `math.isfinite`, `self._actor_activation_progress_m.setdefault`, `str`, `str(actor_id).strip`.
- `note_target_lane_occupancy` 调用：`ValueError`, `type`.
- `update_frame` 调用：`ExtensionFrameState`, `ValueError`, `abs`, `active.append`, `actor_distances_m.items`, `dict`, `fault.get`, `float`, `isinstance`, `math.isfinite`, `max`, `min`, `newly_active.append`, `newly_recovered.append`, `scenario_trigger_satisfied`, `self._closest_speed_to_target_kph_by_phase.get`, `self._fault_active.add`, `self._fault_recovered.add`, `self._fault_started_s.get`, `self._max_speed_after_phase_kph.get`, `self._minimum_actor_distances_m.get`, `self._minimum_speed_during_phase_kph.get`, `self._recent_speed_samples.append`, `self._recent_speed_samples.popleft`, `self._rss_mb`, `self._target_speed_kph_by_phase.get`, `self._traffic_light_states.append`, `self.extensions.get`, `sorted`, `speed_policy.get`, `str`, `str(speed_policy.get('map_limit_handling', default_mode)).strip`, `str(speed_policy.get('map_limit_handling', default_mode)).strip().lower`, `str(traffic_light_state).upper`, `tuple`.
- `note_control_observation` 调用：`abs`, `bool`, `float`, `item.get`, `max`, `self._actor_control_effect_time_s.setdefault`, `self._actor_decision_time_s.setdefault`, `self._actor_safety_override_time_s.setdefault`, `self._command_submitted_s.get`, `self._fault_recovered_s.items`, `self._fault_started_s.items`, `self._safety_reasons.add`, `str`, `str(item.get('type', '')).lower`, `str(safety_reason).strip`, `str(safety_reason).strip().upper`, `{'front_rgb', 'lidar'}.issubset`.
- `actor_state` 调用：`action.get`, `actor_spec.get`, `behavior.get`, `context.get`, `context.setdefault`, `dict`, `event.get`, `float`, `isinstance`, `len`, `max`, `scenario_trigger_satisfied`, `self._actor_event_index.get`, `self._actor_event_time_s.get`, `self._actor_speed_mps.get`, `self.note_actor_trigger`, `self.note_phase_completed`, `str`, `str(action.get('type', '')).lower`, `str(actor_spec.get('state', 'UNKNOWN')).upper`, `str(event['state']).upper`, `type`.
- `evidence` 调用：`dict`, `emergency_events.values`, `float`, `len`, `list`, `max`, `self._actor_activation_progress_m.items`, `self._actor_control_effect_time_s.get`, `self._actor_decision_time_s.get`, `self._actor_perception_time_s.get`, `self._actor_recovery_time_s.get`, `self._actor_safety_override_time_s.get`, `self._actor_trigger_time_s.items`, `self._closest_speed_to_target_kph_by_phase.items`, `self._command_approach_speed_kph_by_phase.items`, `self._command_progress_m_by_phase.items`, `self._command_submitted_s.get`, `self._max_speed_after_phase_kph.items`, `self._minimum_actor_distances_m.items`, `self._minimum_speed_during_phase_kph.items`, `self._percentile`, `self._qwen_applied_by_command_s.get`, `self._target_speed_kph_by_phase.items`, `sorted`.
- `_percentile` 调用：`float`, `len`, `math.ceil`, `math.floor`, `sorted`.
- `evaluate` 调用：`TypeError`, `abs`, `actual.items`, `actual_distances.get`, `actual_events.items`, `actual_set.add`, `actual_set.discard`, `actual_set.issubset`, `actual_speeds.get`, `actual_values.get`, `add`, `all`, `allowed.issubset`, `any`, `behaviors.intersection`, `behaviors.isdisjoint`, `behaviors.issubset`, `bool`, `checks.append`, `checks_by_actor.values`, `dict`, `enumerate`, `event.get`, `evidence['fault_recovery_response_s'].values`, `evidence['fault_response_s'].values`, `evidence['successful_terminal_s'].values`, `faults_started.issubset`, `float`, `int`, `isinstance`, `len`, `list`, `max`, `oracle_contract.get`, `proposed.get`, `proposed.items`, `required.items`, `required_ids.issubset`, `required_phases.issubset`, `results.values`, `self._command_intent_by_id.get`, `self._fault_recovered_s.values`, `self.evidence`, `self.extensions.get`, `set`, `sorted`, `speed_policy.get`, `str`, `str(item).strip`, `str(item).strip().upper`, `str(item).upper`, `target_speeds.get`, `type`, `zip`.
- `walk` 调用：`child.upper`, `float`, `isinstance`, `self._qwen_behaviors.append`, `self._qwen_target_ids.add`, `self._qwen_target_speeds_kph.append`, `str`, `str(child_key).lower`, `type`, `value.items`, `walk`.
- `add` 调用：`checks.append`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 69 行：`TypeError('extensions must be a mapping')`。
- `__init__`，第 72 行：`RuntimeError('unimplemented scenario runtime requirements: ' + ', '.join(missing))`。
- `__init__`，第 76 行：`TypeError('extensions.faults must be a list')`。
- `evaluate`，第 923 行：`TypeError('extensions.oracle must be an object')`。
- `evaluate`，第 1000 行：`TypeError('minimum_actor_distances_m must be an object')`。
- `evaluate`，第 1023 行：`TypeError(f'{key} must be an object')`。
- `evaluate`，第 1037 行：`TypeError(f'{key}.{item_id} must be [minimum, maximum]')`。
- `evaluate`，第 1050 行：`TypeError(f'{key} must be an object')`。
- `evaluate`，第 1067 行：`TypeError('phase_min_speed_ranges_kph must be an object')`。
- `evaluate`，第 1077 行：`TypeError(f'phase_min_speed_ranges_kph.{phase_id} must be [minimum, maximum]')`。
- `evaluate`，第 1088 行：`TypeError('phase_target_speed_tolerance_kph must be an object')`。
- `evaluate`，第 1454 行：`TypeError('extensions.oracle.expected_behaviors must be a list')`。
- `missing_runtime_requirements`，第 50 行：`TypeError('extensions.runtime_support.requirements must be a list')`。
- `note_actor_activated`，第 453 行：`ValueError('activated actor_id must be non-empty')`。
- `note_actor_activated`，第 455 行：`ValueError('actor activation route progress must be finite and non-negative')`。
- `note_emergency_recovered`，第 446 行：`ValueError('emergency recovery requires prior control-effect evidence')`。
- `note_front_path_observation`，第 380 行：`TypeError('path_clear must be bool')`。
- `note_target_lane_occupancy`，第 460 行：`ValueError('target lane occupancy must be a non-negative integer')`。
- `ready_emergency_recovery`，第 391 行：`TypeError('extensions.emergency_recovery must be an object')`。
- `ready_emergency_recovery`，第 400 行：`TypeError('emergency recovery policies must be objects')`。
- `ready_emergency_recovery`，第 405 行：`ValueError('emergency recovery hold/resume speed must be positive and clearance non-negative')`。
- `ready_emergency_recovery`，第 425 行：`ValueError('minimum_path_clear_s must be positive')`。
- `ready_emergency_recovery`，第 432 行：`ValueError('emergency recovery clearance_mode must be actor_distance or sensor_path_clear')`。
- `restore_terminal_phase`，第 350 行：`ValueError('restored phase_id must be non-empty')`。
- `update_frame`，第 497 行：`ValueError('actor distances must be finite and non-negative')`。
- `update_frame`，第 604 行：`ValueError("speed_policy.map_limit_handling must be 'minimum' or 'replace'")`。
- `weather_parameters`，第 189 行：`TypeError('extensions.weather_parameters must be an object')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [integration/scenario_execution.py](../../../integration/scenario_execution.py)

静态 import 消费者（含测试）：

- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/tests/test_scenario_extensions.py](../../../integration/tests/test_scenario_extensions.py)
- [tools/build_acceptance_suite.py](../../../tools/build_acceptance_suite.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-scenarios.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `integration/scenario_extensions.py`

来源 SHA256：`f6fa9be04c2111e33063d2346889b3aa2202a00641d494863ddba4b2da6f6dd9`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `ExtensionFrameState.trigger_context` | `dict[str, object]` | `无声明默认；构造/赋值方提供` |
| `ExtensionFrameState.active_faults` | `tuple[dict[str, Any], ...]` | `无声明默认；构造/赋值方提供` |
| `ExtensionFrameState.newly_active_fault_ids` | `tuple[str, ...]` | `无声明默认；构造/赋值方提供` |
| `ExtensionFrameState.newly_recovered_fault_ids` | `tuple[str, ...]` | `无声明默认；构造/赋值方提供` |
| `ExtensionFrameState.speed_limit_mps` | `float &#124; None` | `无声明默认；构造/赋值方提供` |
| `ExtensionFrameState.speed_limit_overrides_map` | `bool` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `missing_runtime_requirements` / 50 | `not isinstance(requirements, Sequence) or isinstance(requirements, (str, bytes))` | `raise TypeError('extensions.runtime_support.requirements must be a list')` |
| `ScenarioExtensionRuntime.__init__` / 69 | `not isinstance(extensions, Mapping)` | `raise TypeError('extensions must be a mapping')` |
| `ScenarioExtensionRuntime.__init__` / 72 | `missing` | `raise RuntimeError('unimplemented scenario runtime requirements: ' + ', '.join(missing))` |
| `ScenarioExtensionRuntime.__init__` / 76 | `not isinstance(raw_faults, Sequence) or isinstance(raw_faults, (str, bytes))` | `raise TypeError('extensions.faults must be a list')` |
| `ScenarioExtensionRuntime.weather_parameters` / 189 | `not isinstance(values, Mapping)` | `raise TypeError('extensions.weather_parameters must be an object')` |
| `ScenarioExtensionRuntime.restore_terminal_phase` / 350 | `not normalized` | `raise ValueError('restored phase_id must be non-empty')` |
| `ScenarioExtensionRuntime.note_front_path_observation` / 380 | `type(path_clear) is not bool` | `raise TypeError('path_clear must be bool')` |
| `ScenarioExtensionRuntime.ready_emergency_recovery` / 391 | `not isinstance(recovery, Mapping)` | `raise TypeError('extensions.emergency_recovery must be an object')` |
| `ScenarioExtensionRuntime.ready_emergency_recovery` / 400 | `not isinstance(raw_policy, Mapping)` | `raise TypeError('emergency recovery policies must be objects')` |
| `ScenarioExtensionRuntime.ready_emergency_recovery` / 405 | `hold_s <= 0.0 or minimum_clearance_m < 0.0 or resume_speed_kph <= 0.0` | `raise ValueError('emergency recovery hold/resume speed must be positive and clearance non-negative')` |
| `ScenarioExtensionRuntime.ready_emergency_recovery` / 425 | `NOT (clearance_mode == 'actor_distance') AND clearance_mode == 'sensor_path_clear' AND minimum_path_clear_s <= 0.0` | `raise ValueError('minimum_path_clear_s must be positive')` |
| `ScenarioExtensionRuntime.ready_emergency_recovery` / 432 | `NOT (clearance_mode == 'actor_distance') AND NOT (clearance_mode == 'sensor_path_clear')` | `raise ValueError('emergency recovery clearance_mode must be actor_distance or sensor_path_clear')` |
| `ScenarioExtensionRuntime.note_emergency_recovered` / 446 | `normalized not in self._actor_control_effect_time_s` | `raise ValueError('emergency recovery requires prior control-effect evidence')` |
| `ScenarioExtensionRuntime.note_actor_activated` / 453 | `not normalized` | `raise ValueError('activated actor_id must be non-empty')` |
| `ScenarioExtensionRuntime.note_actor_activated` / 455 | `not math.isfinite(progress) or progress < 0.0` | `raise ValueError('actor activation route progress must be finite and non-negative')` |
| `ScenarioExtensionRuntime.note_target_lane_occupancy` / 460 | `type(count) is not int or count < 0` | `raise ValueError('target lane occupancy must be a non-negative integer')` |
| `ScenarioExtensionRuntime.update_frame` / 497 | `not math.isfinite(distance) or distance < 0.0` | `raise ValueError('actor distances must be finite and non-negative')` |
| `ScenarioExtensionRuntime.update_frame` / 604 | `isinstance(speed_policy, Mapping) and 'scenario_limit_kph' in speed_policy AND mode not in {'minimum', 'replace'}` | `raise ValueError("speed_policy.map_limit_handling must be 'minimum' or 'replace'")` |
| `ScenarioExtensionRuntime.evaluate` / 923 | `not isinstance(oracle_contract, Mapping)` | `raise TypeError('extensions.oracle must be an object')` |
| `ScenarioExtensionRuntime.evaluate` / 1000 | `NOT (key in {'qwen_request_count', 'qwen_command_count'}) AND NOT (key == 'must_call_qwen') AND NOT (key == 'qwen_missing_request_count') AND NOT (key in {'qwen_stale_result_applied_count', 'late_result_applied_count'}) AND NOT (key == 'all_commands_must_have_terminal_status') AND NOT (key == 'must_recover_after_fault') AND NOT (key == 'post_recovery_command_succeeds') AND NOT (key == 'max_fault_response_s') AND NOT (key == 'recovery_deadline_s') AND NOT (key == 'speed_drop_deadline_s') AND NOT (key == 'max_resource_growth_mb') AND NOT (key == 'must_return_to_original_lane') AND key == 'minimum_actor_distances_m' AND not isinstance(required, Mapping)` | `raise TypeError('minimum_actor_distances_m must be an object')` |
| `ScenarioExtensionRuntime.evaluate` / 1023 | `NOT (key in {'qwen_request_count', 'qwen_command_count'}) AND NOT (key == 'must_call_qwen') AND NOT (key == 'qwen_missing_request_count') AND NOT (key in {'qwen_stale_result_applied_count', 'late_result_applied_count'}) AND NOT (key == 'all_commands_must_have_terminal_status') AND NOT (key == 'must_recover_after_fault') AND NOT (key == 'post_recovery_command_succeeds') AND NOT (key == 'max_fault_response_s') AND NOT (key == 'recovery_deadline_s') AND NOT (key == 'speed_drop_deadline_s') AND NOT (key == 'max_resource_growth_mb') AND NOT (key == 'must_return_to_original_lane') AND NOT (key == 'minimum_actor_distances_m') AND key in {'actor_activation_progress_windows_m', 'command_progress_windows_m'} AND not isinstance(required, Mapping)` | `raise TypeError(f'{key} must be an object')` |
| `ScenarioExtensionRuntime.evaluate` / 1037 | `NOT (key in {'qwen_request_count', 'qwen_command_count'}) AND NOT (key == 'must_call_qwen') AND NOT (key == 'qwen_missing_request_count') AND NOT (key in {'qwen_stale_result_applied_count', 'late_result_applied_count'}) AND NOT (key == 'all_commands_must_have_terminal_status') AND NOT (key == 'must_recover_after_fault') AND NOT (key == 'post_recovery_command_succeeds') AND NOT (key == 'max_fault_response_s') AND NOT (key == 'recovery_deadline_s') AND NOT (key == 'speed_drop_deadline_s') AND NOT (key == 'max_resource_growth_mb') AND NOT (key == 'must_return_to_original_lane') AND NOT (key == 'minimum_actor_distances_m') AND key in {'actor_activation_progress_windows_m', 'command_progress_windows_m'} AND not isinstance(window, Sequence) or isinstance(window, (str, bytes)) or len(window) != 2` | `raise TypeError(f'{key}.{item_id} must be [minimum, maximum]')` |
| `ScenarioExtensionRuntime.evaluate` / 1050 | `NOT (key in {'qwen_request_count', 'qwen_command_count'}) AND NOT (key == 'must_call_qwen') AND NOT (key == 'qwen_missing_request_count') AND NOT (key in {'qwen_stale_result_applied_count', 'late_result_applied_count'}) AND NOT (key == 'all_commands_must_have_terminal_status') AND NOT (key == 'must_recover_after_fault') AND NOT (key == 'post_recovery_command_succeeds') AND NOT (key == 'max_fault_response_s') AND NOT (key == 'recovery_deadline_s') AND NOT (key == 'speed_drop_deadline_s') AND NOT (key == 'max_resource_growth_mb') AND NOT (key == 'must_return_to_original_lane') AND NOT (key == 'minimum_actor_distances_m') AND NOT (key in {'actor_activation_progress_windows_m', 'command_progress_windows_m'}) AND key in {'minimum_approach_speed_kph_by_phase', 'minimum_resumed_speed_kph_by_phase'} AND not isinstance(required, Mapping)` | `raise TypeError(f'{key} must be an object')` |
| `ScenarioExtensionRuntime.evaluate` / 1067 | `NOT (key in {'qwen_request_count', 'qwen_command_count'}) AND NOT (key == 'must_call_qwen') AND NOT (key == 'qwen_missing_request_count') AND NOT (key in {'qwen_stale_result_applied_count', 'late_result_applied_count'}) AND NOT (key == 'all_commands_must_have_terminal_status') AND NOT (key == 'must_recover_after_fault') AND NOT (key == 'post_recovery_command_succeeds') AND NOT (key == 'max_fault_response_s') AND NOT (key == 'recovery_deadline_s') AND NOT (key == 'speed_drop_deadline_s') AND NOT (key == 'max_resource_growth_mb') AND NOT (key == 'must_return_to_original_lane') AND NOT (key == 'minimum_actor_distances_m') AND NOT (key in {'actor_activation_progress_windows_m', 'command_progress_windows_m'}) AND NOT (key in {'minimum_approach_speed_kph_by_phase', 'minimum_resumed_speed_kph_by_phase'}) AND key == 'phase_min_speed_ranges_kph' AND not isinstance(required, Mapping)` | `raise TypeError('phase_min_speed_ranges_kph must be an object')` |
| `ScenarioExtensionRuntime.evaluate` / 1077 | `NOT (key in {'qwen_request_count', 'qwen_command_count'}) AND NOT (key == 'must_call_qwen') AND NOT (key == 'qwen_missing_request_count') AND NOT (key in {'qwen_stale_result_applied_count', 'late_result_applied_count'}) AND NOT (key == 'all_commands_must_have_terminal_status') AND NOT (key == 'must_recover_after_fault') AND NOT (key == 'post_recovery_command_succeeds') AND NOT (key == 'max_fault_response_s') AND NOT (key == 'recovery_deadline_s') AND NOT (key == 'speed_drop_deadline_s') AND NOT (key == 'max_resource_growth_mb') AND NOT (key == 'must_return_to_original_lane') AND NOT (key == 'minimum_actor_distances_m') AND NOT (key in {'actor_activation_progress_windows_m', 'command_progress_windows_m'}) AND NOT (key in {'minimum_approach_speed_kph_by_phase', 'minimum_resumed_speed_kph_by_phase'}) AND key == 'phase_min_speed_ranges_kph' AND not isinstance(speed_range, Sequence) or isinstance(speed_range, (str, bytes)) or len(speed_range) != 2` | `raise TypeError(f'phase_min_speed_ranges_kph.{phase_id} must be [minimum, maximum]')` |
| `ScenarioExtensionRuntime.evaluate` / 1088 | `NOT (key in {'qwen_request_count', 'qwen_command_count'}) AND NOT (key == 'must_call_qwen') AND NOT (key == 'qwen_missing_request_count') AND NOT (key in {'qwen_stale_result_applied_count', 'late_result_applied_count'}) AND NOT (key == 'all_commands_must_have_terminal_status') AND NOT (key == 'must_recover_after_fault') AND NOT (key == 'post_recovery_command_succeeds') AND NOT (key == 'max_fault_response_s') AND NOT (key == 'recovery_deadline_s') AND NOT (key == 'speed_drop_deadline_s') AND NOT (key == 'max_resource_growth_mb') AND NOT (key == 'must_return_to_original_lane') AND NOT (key == 'minimum_actor_distances_m') AND NOT (key in {'actor_activation_progress_windows_m', 'command_progress_windows_m'}) AND NOT (key in {'minimum_approach_speed_kph_by_phase', 'minimum_resumed_speed_kph_by_phase'}) AND NOT (key == 'phase_min_speed_ranges_kph') AND key == 'phase_target_speed_tolerance_kph' AND not isinstance(required, Mapping)` | `raise TypeError('phase_target_speed_tolerance_kph must be an object')` |
| `ScenarioExtensionRuntime.evaluate` / 1454 | `expected_behaviors is not None and valid_model_output_expected AND not isinstance(expected_behaviors, Sequence) or isinstance(expected_behaviors, (str, bytes))` | `raise TypeError('extensions.oracle.expected_behaviors must be a list')` |
