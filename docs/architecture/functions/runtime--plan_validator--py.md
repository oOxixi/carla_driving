# plan_validator：功能记录

上级模块：[模块说明](../modules/vehicle-planner.md) · 实现：[runtime/plan_validator.py](../../../runtime/plan_validator.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [异步等待、旧结果拒绝与多层命令ID](async-plan-dispatch.md)
- [计划可行性校验与内部步骤展开](plan-validation-compilation.md)

## 功能职责与范围

Strict schema and scene-feasibility validation for ManeuverPlan V2.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

<a id="fn-planvalidationerror"></a>

### `PlanValidationError`

源码位置：[runtime/plan_validator.py 第 39 行](../../../runtime/plan_validator.py#L39)。类型：`ClassDef`。

A plan failed a stable, machine-readable safety boundary.

<a id="fn-planvalidationerror---init--"></a>

### `PlanValidationError.__init__`

源码位置：[runtime/plan_validator.py 第 42 行](../../../runtime/plan_validator.py#L42)。类型：`FunctionDef`。

```python
PlanValidationError.__init__(self, reason_code: str, detail: str) -> None
```

保存reason_code/detail并构造ValueError文本reason: detail；调用者可按稳定reason统计，不能只匹配整句。

<a id="fn-planvalidator"></a>

### `PlanValidator`

源码位置：[runtime/plan_validator.py 第 48 行](../../../runtime/plan_validator.py#L48)。类型：`ClassDef`。

ManeuverPlan V2的Schema与提交场景可执行边界；不调用模型/车辆，不证明未来每帧前置条件满足。allow_confirmation仅保留待确认计划。

<a id="fn-planvalidator---init--"></a>

### `PlanValidator.__init__`

源码位置：[runtime/plan_validator.py 第 49 行](../../../runtime/plan_validator.py#L49)。类型：`FunctionDef`。

```python
PlanValidator.__init__(self, *, registry: InterfaceRegistry | None=None, maximum_speed_mps: float=13.8888888889, minimum_confidence: float=0.8, clock_ns: Any=time.monotonic_ns) -> None
```

默认速度13.8888888889m/s需有限正数；confidence默认0.8且[0,1]；registry/单调纳秒clock可注入。构造不预热Schema。

<a id="fn-planvalidator-validate"></a>

### `PlanValidator.validate`

源码位置：[runtime/plan_validator.py 第 66 行](../../../runtime/plan_validator.py#L66)。类型：`FunctionDef`。

```python
PlanValidator.validate(self, payload: Mapping[str, Any], *, scene: Mapping[str, Any], expected_request_id: str | None=None, expected_command_id: str | None=None, now_ns: int | None=None, allow_confirmation: bool=False) -> dict[str, Any]
```

拒绝递归低层控制字段，校验Schema、可选期望ID、created<valid_until、now>=valid_until过期；默认拒绝低置信/需确认。检查scene新鲜度、重复step ID、全部非空目标（包括STOP带目标）、FOLLOW/AVOID必需目标、速度/车道/完成条件，返回严格JSON副本。目标集合含objects.track_id与grounded_target_ids，不等于全为视觉测量。

<a id="fn-planvalidator--validate-preconditions"></a>

### `PlanValidator._validate_preconditions`

源码位置：[runtime/plan_validator.py 第 186 行](../../../runtime/plan_validator.py#L186)。类型：`FunctionDef`。

```python
PlanValidator._validate_preconditions(preconditions: Sequence[str], scene: Mapping[str, Any], prefix: str) -> None
```

主要检查可观测字段是否存在：TARGET_VISIBLE需objects键，车道/gap/route等需映射键。值为False仍可通过，执行FSM负责等待；PERCEPTION_FRESH与NO_EMERGENCY_RISK在此循环跳过，不能称全部条件当前已成立。

<a id="fn-planvalidator--validate-completion"></a>

### `PlanValidator._validate_completion`

源码位置：[runtime/plan_validator.py 第 208 行](../../../runtime/plan_validator.py#L208)。类型：`FunctionDef`。

```python
PlanValidator._validate_completion(behavior: str, completion: Mapping[str, Any], prefix: str) -> None
```

SPEED_BELOW/SPEED_REACHED/TARGET_GAP_REACHED需value，LANE_CENTERED需lane；按行为限定completion，例如TURN→JUNCTION_EXITED、FOLLOW→TARGET_GAP_REACHED/HOLD_FRAMES、YIELD→HOLD_FRAMES。其余行为不在该表时仅受Schema及通用检查。

<a id="fn--find-forbidden-fields"></a>

### `_find_forbidden_fields`

源码位置：[runtime/plan_validator.py 第 238 行](../../../runtime/plan_validator.py#L238)。类型：`FunctionDef`。

```python
_find_forbidden_fields(value: Any, path: str='<root>') -> Sequence[str]
```

递归Mapping和非字符串Sequence，按key小写匹配低层字段，返回所有点/数组路径；不会分析字符串内嵌代码。

<a id="fn--nested"></a>

### `_nested`

源码位置：[runtime/plan_validator.py 第 252 行](../../../runtime/plan_validator.py#L252)。类型：`FunctionDef`。

```python
_nested(payload: Mapping[str, Any], outer: str, inner: str, default: Any) -> Any
```

outer为Mapping才读取inner，否则回default；不修改输入。

<a id="fn--speed-limit"></a>

### `_speed_limit`

源码位置：[runtime/plan_validator.py 第 257 行](../../../runtime/plan_validator.py#L257)。类型：`FunctionDef`。

```python
_speed_limit(scene: Mapping[str, Any], configured: float) -> float
```

scene限速非数或bool回configured；有效数值取min(configured,max(0,value))。本helper没有独立isfinite检查，scene来源应受上游约束。

<a id="fn--must-stop"></a>

### `_must_stop`

源码位置：[runtime/plan_validator.py 第 264 行](../../../runtime/plan_validator.py#L264)。类型：`FunctionDef`。

```python
_must_stop(scene: Mapping[str, Any]) -> bool
```

EMERGENCY风险优先True；若有显式must_stop使用其bool，避免远红灯误阻止接近；否则红/黄灯且停止线距离非None即True，不在此比较距离阈值。

<a id="fn--available-lanes"></a>

### `_available_lanes`

源码位置：[runtime/plan_validator.py 第 279 行](../../../runtime/plan_validator.py#L279)。类型：`FunctionDef`。

```python
_available_lanes(scene: Mapping[str, Any]) -> set[str] | None
```

显式available_lanes为非字符串Sequence时转大写set；否则由left/right/shoulder_exists推导，至少有一个观测键则含CURRENT的set，全部缺失返回None。None与仅CURRENT表示不同可观测性。

## 内部调用与异常路径

- `_find_forbidden_fields` 调用：`_find_forbidden_fields`, `enumerate`, `found.append`, `found.extend`, `isinstance`, `str`, `str(key).lower`, `value.items`.
- `_nested` 调用：`isinstance`, `nested.get`, `payload.get`.
- `_speed_limit` 调用：`float`, `isinstance`, `max`, `min`, `scene.get`, `type`.
- `_must_stop` 调用：`bool`, `scene.get`, `str`, `str(scene.get('risk_level', 'UNKNOWN')).upper`, `str(scene.get('traffic_light', 'UNKNOWN')).upper`.
- `_available_lanes` 调用：`bool`, `derived.add`, `isinstance`, `scene.get`, `str`, `str(item).upper`.
- `__init__` 调用：`InterfaceRegistry`, `ValueError`, `float`, `math.isfinite`, `super`, `super().__init__`.
- `validate` 调用：`', '.join`, `PlanValidationError`, `TypeError`, `ValueError`, `_LANE_REQUIREMENTS.get`, `_available_lanes`, `_find_forbidden_fields`, `_must_stop`, `_nested`, `_speed_limit`, `available_targets.update`, `bool`, `enumerate`, `float`, `isinstance`, `item.get`, `len`, `scene.get`, `self._clock_ns`, `self._validate_completion`, `self._validate_preconditions`, `self.registry.validate`, `set`, `str`, `target.get`, `tuple`, `type`.
- `_validate_preconditions` 调用：`PlanValidationError`, `_OBSERVABILITY_KEYS.get`.
- `_validate_completion` 调用：`PlanValidationError`, `completion.get`, `str`, `{'TURN_LEFT': {'JUNCTION_EXITED'}, 'TURN_RIGHT': {'JUNCTION_EXITED'}, 'CHANGE_LANE_LEFT': {'LANE_CENTERED'}, 'CHANGE_LANE_RIGHT': {'LANE_CENTERED'}, 'STOP': {'STOPPED', 'SPEED_BELOW'}, 'FOLLOW': {'TARGET_GAP_REACHED', 'HOLD_FRAMES'}, 'YIELD': {'HOLD_FRAMES'}, 'PULL_OVER': {'STOPPED', 'LANE_CENTERED'}}.get`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 58 行：`ValueError('maximum_speed_mps must be finite and positive')`。
- `__init__`，第 60 行：`ValueError('minimum_confidence must be in [0, 1]')`。
- `_validate_completion`，第 214 行：`PlanValidationError('COMPLETION_VALUE_REQUIRED', f'{prefix} {completion_type} requires value')`。
- `_validate_completion`，第 218 行：`PlanValidationError('COMPLETION_LANE_REQUIRED', f'{prefix} LANE_CENTERED requires lane')`。
- `_validate_completion`，第 232 行：`PlanValidationError('COMPLETION_BEHAVIOR_MISMATCH', f'{prefix} {behavior} cannot use completion {completion_type}')`。
- `_validate_preconditions`，第 196 行：`PlanValidationError('PRECONDITION_UNOBSERVABLE', f'{prefix} cannot observe TARGET_VISIBLE')`。
- `_validate_preconditions`，第 202 行：`PlanValidationError('PRECONDITION_UNOBSERVABLE', f'{prefix} cannot observe {condition}; missing scene.{key}')`。
- `validate`，第 77 行：`PlanValidationError('INVALID_PLAN_SCHEMA', 'plan must be a JSON object')`。
- `validate`，第 79 行：`TypeError('scene must be a mapping')`。
- `validate`，第 82 行：`PlanValidationError('LOW_LEVEL_OUTPUT_FORBIDDEN', 'forbidden control field(s): ' + ', '.join(forbidden_paths))`。
- `validate`，第 89 行：`PlanValidationError('INVALID_PLAN_SCHEMA', str(error))`。
- `validate`，第 93 行：`ValueError('now_ns must be a non-negative integer')`。
- `validate`，第 95 行：`PlanValidationError('REQUEST_ID_MISMATCH', 'plan request_id does not match request')`。
- `validate`，第 97 行：`PlanValidationError('COMMAND_ID_MISMATCH', 'plan command_id does not match request')`。
- `validate`，第 99 行：`PlanValidationError('INVALID_PLAN_VALIDITY', 'valid_until_ns must follow created_at_ns')`。
- `validate`，第 101 行：`PlanValidationError('PLAN_EXPIRED', 'plan validity boundary elapsed')`。
- `validate`，第 103 行：`TypeError('allow_confirmation must be bool')`。
- `validate`，第 108 行：`PlanValidationError('PLAN_CONFIRMATION_REQUIRED', 'plan confidence is too low or model requested confirmation')`。
- `validate`，第 113 行：`PlanValidationError('PERCEPTION_STALE', 'plan cannot execute on stale perception')`。
- `validate`，第 117 行：`PlanValidationError('DUPLICATE_STEP_ID', 'every step_id must be unique')`。
- `validate`，第 144 行：`PlanValidationError('MUST_STOP_PROPULSION_FORBIDDEN', f'{prefix} {behavior} conflicts with red-light or emergency constraint')`。
- `validate`，第 149 行：`PlanValidationError('TARGET_NOT_FOUND', f'{prefix} target_id {target_id!r} is not visible')`。
- `validate`，第 153 行：`PlanValidationError('TARGET_REQUIRED', f'{prefix} {behavior} requires a visible target_id')`。
- `validate`，第 157 行：`PlanValidationError('SPEED_LIMIT_EXCEEDED', f'{prefix} target_speed_mps {target_speed} exceeds {speed_limit}')`。
- `validate`，第 162 行：`PlanValidationError('TARGET_SPEED_REQUIRED', f'{prefix} {behavior} requires target_speed_mps')`。
- `validate`，第 167 行：`PlanValidationError('TARGET_LANE_MISMATCH', f'{prefix} {behavior} requires target_lane={required_lane}')`。
- `validate`，第 173 行：`PlanValidationError('LANE_CONTEXT_MISSING', f'{prefix} cannot verify target lane {target_lane}')`。
- `validate`，第 178 行：`PlanValidationError('TARGET_LANE_UNAVAILABLE', f'{prefix} lane {target_lane} is unavailable')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [runtime/interface_registry.py](../../../runtime/interface_registry.py)

静态 import 消费者（含测试）：

- [challenge/planner/student_backend.py](../../../challenge/planner/student_backend.py)
- [challenge/planner/teacher_backend.py](../../../challenge/planner/teacher_backend.py)
- [integration/qwen_plan_adapter.py](../../../integration/qwen_plan_adapter.py)
- [integration/qwen_scenario_monitor.py](../../../integration/qwen_scenario_monitor.py)
- [integration/tests/test_maneuver_plan_schema.py](../../../integration/tests/test_maneuver_plan_schema.py)
- [qwen_service/service.py](../../../qwen_service/service.py)
- [runtime/__init__.py](../../../runtime/__init__.py)
- [runtime/orchestrator.py](../../../runtime/orchestrator.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-planner.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-runtime-plan-validator-py"></a>

### `runtime/plan_validator.py`

来源 SHA256：`e059390fd241b036a4fef16ccd63ce68c7b6b22a4d7157e6d9caba4f3c0a78da`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `PlanValidator.__init__` / 58 | `not math.isfinite(float(maximum_speed_mps)) or maximum_speed_mps <= 0` | `raise ValueError('maximum_speed_mps must be finite and positive')` |
| `PlanValidator.__init__` / 60 | `not 0.0 <= float(minimum_confidence) <= 1.0` | `raise ValueError('minimum_confidence must be in [0, 1]')` |
| `PlanValidator.validate` / 77 | `not isinstance(payload, Mapping)` | `raise PlanValidationError('INVALID_PLAN_SCHEMA', 'plan must be a JSON object')` |
| `PlanValidator.validate` / 79 | `not isinstance(scene, Mapping)` | `raise TypeError('scene must be a mapping')` |
| `PlanValidator.validate` / 82 | `forbidden_paths` | `raise PlanValidationError('LOW_LEVEL_OUTPUT_FORBIDDEN', 'forbidden control field(s): ' + ', '.join(forbidden_paths))` |
| `PlanValidator.validate` / 89 | `except InterfaceValidationError` | `raise PlanValidationError('INVALID_PLAN_SCHEMA', str(error)) from error` |
| `PlanValidator.validate` / 93 | `type(now) is not int or now < 0` | `raise ValueError('now_ns must be a non-negative integer')` |
| `PlanValidator.validate` / 95 | `expected_request_id is not None and plan['request_id'] != expected_request_id` | `raise PlanValidationError('REQUEST_ID_MISMATCH', 'plan request_id does not match request')` |
| `PlanValidator.validate` / 97 | `expected_command_id is not None and plan['command_id'] != expected_command_id` | `raise PlanValidationError('COMMAND_ID_MISMATCH', 'plan command_id does not match request')` |
| `PlanValidator.validate` / 99 | `plan['created_at_ns'] >= plan['valid_until_ns']` | `raise PlanValidationError('INVALID_PLAN_VALIDITY', 'valid_until_ns must follow created_at_ns')` |
| `PlanValidator.validate` / 101 | `now >= plan['valid_until_ns']` | `raise PlanValidationError('PLAN_EXPIRED', 'plan validity boundary elapsed')` |
| `PlanValidator.validate` / 103 | `type(allow_confirmation) is not bool` | `raise TypeError('allow_confirmation must be bool')` |
| `PlanValidator.validate` / 108 | `not allow_confirmation and (float(plan['confidence']) < self.minimum_confidence or plan['requires_confirmation'])` | `raise PlanValidationError('PLAN_CONFIRMATION_REQUIRED', 'plan confidence is too low or model requested confirmation')` |
| `PlanValidator.validate` / 113 | `bool(scene.get('stale', False)) or not bool(_nested(scene, 'sync', 'within_tolerance', True))` | `raise PlanValidationError('PERCEPTION_STALE', 'plan cannot execute on stale perception')` |
| `PlanValidator.validate` / 117 | `len(step_ids) != len(set(step_ids))` | `raise PlanValidationError('DUPLICATE_STEP_ID', 'every step_id must be unique')` |
| `PlanValidator.validate` / 144 | `must_stop and behavior in ADVANCING_BEHAVIORS` | `raise PlanValidationError('MUST_STOP_PROPULSION_FORBIDDEN', f'{prefix} {behavior} conflicts with red-light or emergency constraint')` |
| `PlanValidator.validate` / 149 | `target_id is not None and target_id not in available_targets` | `raise PlanValidationError('TARGET_NOT_FOUND', f'{prefix} target_id {target_id!r} is not visible')` |
| `PlanValidator.validate` / 153 | `behavior in _TARGET_BEHAVIORS and (not target_id)` | `raise PlanValidationError('TARGET_REQUIRED', f'{prefix} {behavior} requires a visible target_id')` |
| `PlanValidator.validate` / 157 | `target_speed is not None and float(target_speed) > speed_limit + 1e-09` | `raise PlanValidationError('SPEED_LIMIT_EXCEEDED', f'{prefix} target_speed_mps {target_speed} exceeds {speed_limit}')` |
| `PlanValidator.validate` / 162 | `behavior in _SPEED_BEHAVIORS and target_speed is None` | `raise PlanValidationError('TARGET_SPEED_REQUIRED', f'{prefix} {behavior} requires target_speed_mps')` |
| `PlanValidator.validate` / 167 | `required_lane is not None and target_lane != required_lane` | `raise PlanValidationError('TARGET_LANE_MISMATCH', f'{prefix} {behavior} requires target_lane={required_lane}')` |
| `PlanValidator.validate` / 173 | `target_lane in {'LEFT_ADJACENT', 'RIGHT_ADJACENT', 'SHOULDER'} AND available_lanes is None` | `raise PlanValidationError('LANE_CONTEXT_MISSING', f'{prefix} cannot verify target lane {target_lane}')` |
| `PlanValidator.validate` / 178 | `target_lane in {'LEFT_ADJACENT', 'RIGHT_ADJACENT', 'SHOULDER'} AND target_lane not in available_lanes` | `raise PlanValidationError('TARGET_LANE_UNAVAILABLE', f'{prefix} lane {target_lane} is unavailable')` |
| `PlanValidator._validate_preconditions` / 196 | `condition == 'TARGET_VISIBLE' AND 'objects' not in scene` | `raise PlanValidationError('PRECONDITION_UNOBSERVABLE', f'{prefix} cannot observe TARGET_VISIBLE')` |
| `PlanValidator._validate_preconditions` / 202 | `key is not None and key not in scene` | `raise PlanValidationError('PRECONDITION_UNOBSERVABLE', f'{prefix} cannot observe {condition}; missing scene.{key}')` |
| `PlanValidator._validate_completion` / 214 | `completion_type in {'SPEED_BELOW', 'SPEED_REACHED', 'TARGET_GAP_REACHED'} AND completion.get('value') is None` | `raise PlanValidationError('COMPLETION_VALUE_REQUIRED', f'{prefix} {completion_type} requires value')` |
| `PlanValidator._validate_completion` / 218 | `completion_type == 'LANE_CENTERED' and completion.get('lane') is None` | `raise PlanValidationError('COMPLETION_LANE_REQUIRED', f'{prefix} LANE_CENTERED requires lane')` |
| `PlanValidator._validate_completion` / 232 | `expected_types is not None and completion_type not in expected_types` | `raise PlanValidationError('COMPLETION_BEHAVIOR_MISMATCH', f'{prefix} {behavior} cannot use completion {completion_type}')` |
