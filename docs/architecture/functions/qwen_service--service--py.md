# service：功能记录

上级模块：[模块说明](../modules/support-qwen.md) · 实现：[qwen_service/service.py](../../../qwen_service/service.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [服务模式、动作组装与health](qwen-service-semantics.md)

## 功能职责与范围

Core B service with strict contracts, bounded concurrency and metrics.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `DecisionBackend.model_id: str`；默认：`未在声明处设置`。
- `DecisionBackend.production_ready: bool`；默认：`未在声明处设置`。
- `QwenServiceConfig.timeout_ms: float`；默认：`300.0`。
- `QwenServiceConfig.max_concurrency: int`；默认：`1`。
- `QwenServiceConfig.max_request_bytes: int`；默认：`262144`。

## 功能入口：输入、输出与实现说明

### `_percentile`

源码位置：[qwen_service/service.py 第 29 行](../../../qwen_service/service.py#L29)。类型：`FunctionDef`。

```python
_percentile(values: list[float], quantile: float) -> float | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `DecisionBackend`

源码位置：[qwen_service/service.py 第 42 行](../../../qwen_service/service.py#L42)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `DecisionBackend.infer`

源码位置：[qwen_service/service.py 第 46 行](../../../qwen_service/service.py#L46)。类型：`FunctionDef`。

```python
DecisionBackend.infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `DecisionBackend.health`

源码位置：[qwen_service/service.py 第 48 行](../../../qwen_service/service.py#L48)。类型：`FunctionDef`。

```python
DecisionBackend.health(self) -> tuple[bool, str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ServiceFailure`

源码位置：[qwen_service/service.py 第 51 行](../../../qwen_service/service.py#L51)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ServiceFailure.__init__`

源码位置：[qwen_service/service.py 第 52 行](../../../qwen_service/service.py#L52)。类型：`FunctionDef`。

```python
ServiceFailure.__init__(self, status_code: int, error_code: str, message: str, *, request_id: str | None=None) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ServiceFailure.to_dict`

源码位置：[qwen_service/service.py 第 58 行](../../../qwen_service/service.py#L58)。类型：`FunctionDef`。

```python
ServiceFailure.to_dict(self) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `QwenServiceConfig`

源码位置：[qwen_service/service.py 第 69 行](../../../qwen_service/service.py#L69)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `QwenServiceConfig.__post_init__`

源码位置：[qwen_service/service.py 第 74 行](../../../qwen_service/service.py#L74)。类型：`FunctionDef`。

```python
QwenServiceConfig.__post_init__(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `UnavailableBackend`

源码位置：[qwen_service/service.py 第 82 行](../../../qwen_service/service.py#L82)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `UnavailableBackend.__init__`

源码位置：[qwen_service/service.py 第 86 行](../../../qwen_service/service.py#L86)。类型：`FunctionDef`。

```python
UnavailableBackend.__init__(self, reason: str='no local Qwen checkpoint configured') -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `UnavailableBackend.infer`

源码位置：[qwen_service/service.py 第 89 行](../../../qwen_service/service.py#L89)。类型：`FunctionDef`。

```python
UnavailableBackend.infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `UnavailableBackend.health`

源码位置：[qwen_service/service.py 第 92 行](../../../qwen_service/service.py#L92)。类型：`FunctionDef`。

```python
UnavailableBackend.health(self) -> tuple[bool, str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `DeterministicTestBackend`

源码位置：[qwen_service/service.py 第 96 行](../../../qwen_service/service.py#L96)。类型：`ClassDef`。

Contract-test backend; never valid evidence for Qwen correctness/latency.

### `DeterministicTestBackend.health`

源码位置：[qwen_service/service.py 第 102 行](../../../qwen_service/service.py#L102)。类型：`FunctionDef`。

```python
DeterministicTestBackend.health(self) -> tuple[bool, str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `DeterministicTestBackend.infer`

源码位置：[qwen_service/service.py 第 105 行](../../../qwen_service/service.py#L105)。类型：`FunctionDef`。

```python
DeterministicTestBackend.infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `DeterministicPlannerV2Backend`

源码位置：[qwen_service/service.py 第 142 行](../../../qwen_service/service.py#L142)。类型：`ClassDef`。

Planner V2 contract stub; explicitly excluded from model evidence.

### `DeterministicPlannerV2Backend.health`

源码位置：[qwen_service/service.py 第 148 行](../../../qwen_service/service.py#L148)。类型：`FunctionDef`。

```python
DeterministicPlannerV2Backend.health(self) -> tuple[bool, str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `DeterministicPlannerV2Backend.infer`

源码位置：[qwen_service/service.py 第 151 行](../../../qwen_service/service.py#L151)。类型：`FunctionDef`。

```python
DeterministicPlannerV2Backend.infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `LocalQwenPlannerBackend`

源码位置：[qwen_service/service.py 第 377 行](../../../qwen_service/service.py#L377)。类型：`ClassDef`。

Real local Qwen2.5-VL generation backend for ManeuverPlan V2 JSON.

### `LocalQwenPlannerBackend.__init__`

源码位置：[qwen_service/service.py 第 382 行](../../../qwen_service/service.py#L382)。类型：`FunctionDef`。

```python
LocalQwenPlannerBackend.__init__(self, model_path: str | Path, *, image_root: str | Path | None=None, max_new_tokens: int=256, min_pixels: int=64 * 28 * 28, max_pixels: int=256 * 28 * 28) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `LocalQwenPlannerBackend.health`

源码位置：[qwen_service/service.py 第 404 行](../../../qwen_service/service.py#L404)。类型：`FunctionDef`。

```python
LocalQwenPlannerBackend.health(self) -> tuple[bool, str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `LocalQwenPlannerBackend.infer`

源码位置：[qwen_service/service.py 第 407 行](../../../qwen_service/service.py#L407)。类型：`FunctionDef`。

```python
LocalQwenPlannerBackend.infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `LocalQwenPlannerBackend._resolve_image`

源码位置：[qwen_service/service.py 第 420 行](../../../qwen_service/service.py#L420)。类型：`FunctionDef`。

```python
LocalQwenPlannerBackend._resolve_image(self, value: Any) -> Path | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `VllmQwenPlannerBackend`

源码位置：[qwen_service/service.py 第 439 行](../../../qwen_service/service.py#L439)。类型：`ClassDef`。

Production Planner V2 adapter over an existing OpenAI-compatible vLLM.

### `VllmQwenPlannerBackend.__init__`

源码位置：[qwen_service/service.py 第 451 行](../../../qwen_service/service.py#L451)。类型：`FunctionDef`。

```python
VllmQwenPlannerBackend.__init__(self, *, base_url: str, model: str, image_root: str | Path | None=None, api_key: str='unused', timeout_s: float=15.0, max_new_tokens: int=256, image_max_side: int=224, jpeg_quality: int=75) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `VllmQwenPlannerBackend.health`

源码位置：[qwen_service/service.py 第 483 行](../../../qwen_service/service.py#L483)。类型：`FunctionDef`。

```python
VllmQwenPlannerBackend.health(self) -> tuple[bool, str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `VllmQwenPlannerBackend.infer`

源码位置：[qwen_service/service.py 第 486 行](../../../qwen_service/service.py#L486)。类型：`FunctionDef`。

```python
VllmQwenPlannerBackend.infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `VllmQwenPlannerBackend._expanded_steps`

源码位置：[qwen_service/service.py 第 545 行](../../../qwen_service/service.py#L545)。类型：`FunctionDef`。

```python
VllmQwenPlannerBackend._expanded_steps(self, request: Mapping[str, Any], behavior: str) -> list[dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `VllmQwenPlannerBackend._pedestrian_then_overtake_requested`

源码位置：[qwen_service/service.py 第 624 行](../../../qwen_service/service.py#L624)。类型：`FunctionDef`。

```python
VllmQwenPlannerBackend._pedestrian_then_overtake_requested(request: Mapping[str, Any]) -> bool
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `VllmQwenPlannerBackend._persistent_post_maneuver_speed_requested`

源码位置：[qwen_service/service.py 第 638 行](../../../qwen_service/service.py#L638)。类型：`FunctionDef`。

```python
VllmQwenPlannerBackend._persistent_post_maneuver_speed_requested(request: Mapping[str, Any]) -> bool
```

Return whether a finite maneuver requests a persistent speed.

### `VllmQwenPlannerBackend._resume_requested`

源码位置：[qwen_service/service.py 第 697 行](../../../qwen_service/service.py#L697)。类型：`FunctionDef`。

```python
VllmQwenPlannerBackend._resume_requested(request: Mapping[str, Any]) -> bool
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `VllmQwenPlannerBackend._clearance_observation_requested`

源码位置：[qwen_service/service.py 第 704 行](../../../qwen_service/service.py#L704)。类型：`FunctionDef`。

```python
VllmQwenPlannerBackend._clearance_observation_requested(request: Mapping[str, Any]) -> bool
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `VllmQwenPlannerBackend._transient_merge_hazard`

源码位置：[qwen_service/service.py 第 712 行](../../../qwen_service/service.py#L712)。类型：`FunctionDef`。

```python
VllmQwenPlannerBackend._transient_merge_hazard(request: Mapping[str, Any]) -> bool
```

Identify hazards that clear by stabilising, not by being passed.

### `VllmQwenPlannerBackend._choice_codes`

源码位置：[qwen_service/service.py 第 719 行](../../../qwen_service/service.py#L719)。类型：`FunctionDef`。

```python
VllmQwenPlannerBackend._choice_codes(self, request: Mapping[str, Any]) -> list[str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `VllmQwenPlannerBackend._traffic_stop_required`

源码位置：[qwen_service/service.py 第 777 行](../../../qwen_service/service.py#L777)。类型：`FunctionDef`。

```python
VllmQwenPlannerBackend._traffic_stop_required(request: Mapping[str, Any]) -> bool
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `VllmQwenPlannerBackend._choice_prompt`

源码位置：[qwen_service/service.py 第 784 行](../../../qwen_service/service.py#L784)。类型：`FunctionDef`。

```python
VllmQwenPlannerBackend._choice_prompt(self, request: Mapping[str, Any], *, choice_codes: list[str] | None=None) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `VllmQwenPlannerBackend._step`

源码位置：[qwen_service/service.py 第 837 行](../../../qwen_service/service.py#L837)。类型：`FunctionDef`。

```python
VllmQwenPlannerBackend._step(self, request: Mapping[str, Any], behavior: str, *, index: int) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `VllmQwenPlannerBackend._resolve_image`

源码位置：[qwen_service/service.py 第 1052 行](../../../qwen_service/service.py#L1052)。类型：`FunctionDef`。

```python
VllmQwenPlannerBackend._resolve_image(self, value: Any) -> Path | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `VllmQwenPlannerBackend._image_data_url`

源码位置：[qwen_service/service.py 第 1067 行](../../../qwen_service/service.py#L1067)。类型：`FunctionDef`。

```python
VllmQwenPlannerBackend._image_data_url(self, path: Path) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `VllmQwenPlannerBackend.close`

源码位置：[qwen_service/service.py 第 1086 行](../../../qwen_service/service.py#L1086)。类型：`FunctionDef`。

```python
VllmQwenPlannerBackend.close(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `LocalQwenBackend`

源码位置：[qwen_service/service.py 第 1092 行](../../../qwen_service/service.py#L1092)。类型：`ClassDef`。

Adapter from the repository's real local Qwen2.5-VL implementation.

### `LocalQwenBackend.__init__`

源码位置：[qwen_service/service.py 第 1097 行](../../../qwen_service/service.py#L1097)。类型：`FunctionDef`。

```python
LocalQwenBackend.__init__(self, model_path: str | Path, *, image_root: str | Path | None=None, max_new_tokens: int=48, min_pixels: int=64 * 28 * 28, max_pixels: int=256 * 28 * 28) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `LocalQwenBackend.health`

源码位置：[qwen_service/service.py 第 1119 行](../../../qwen_service/service.py#L1119)。类型：`FunctionDef`。

```python
LocalQwenBackend.health(self) -> tuple[bool, str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `LocalQwenBackend.infer`

源码位置：[qwen_service/service.py 第 1122 行](../../../qwen_service/service.py#L1122)。类型：`FunctionDef`。

```python
LocalQwenBackend.infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `LocalQwenBackend._to_plan`

源码位置：[qwen_service/service.py 第 1150 行](../../../qwen_service/service.py#L1150)。类型：`FunctionDef`。

```python
LocalQwenBackend._to_plan(self, request: Mapping[str, Any], decision: Mapping[str, Any]) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_planner_step`

源码位置：[qwen_service/service.py 第 1190 行](../../../qwen_service/service.py#L1190)。类型：`FunctionDef`。

```python
_planner_step(step_id: str, behavior: str, *, speed: float | None, target_id: str | None=None, lane: str | None='CURRENT', time_gap_s: float | None=None, route_direction: str | None=None, preconditions: tuple[str, ...]=('PERCEPTION_FRESH', 'NO_EMERGENCY_RISK'), completion: str='SPEED_BELOW', completion_value: float | None=3.3, timeout_s: float=5.0, failure: str='SAFE_STOP') -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `QwenDecisionService`

源码位置：[qwen_service/service.py 第 1227 行](../../../qwen_service/service.py#L1227)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `QwenDecisionService.__init__`

源码位置：[qwen_service/service.py 第 1228 行](../../../qwen_service/service.py#L1228)。类型：`FunctionDef`。

```python
QwenDecisionService.__init__(self, backend: DecisionBackend, *, config: QwenServiceConfig | None=None, registry: InterfaceRegistry | None=None, qwen_mode: str='atomic_v1', clock_ns: Any=time.monotonic_ns) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `QwenDecisionService.infer`

源码位置：[qwen_service/service.py 第 1268 行](../../../qwen_service/service.py#L1268)。类型：`FunctionDef`。

```python
QwenDecisionService.infer(self, payload: Mapping[str, Any]) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `QwenDecisionService.health`

源码位置：[qwen_service/service.py 第 1344 行](../../../qwen_service/service.py#L1344)。类型：`FunctionDef`。

```python
QwenDecisionService.health(self) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `QwenDecisionService.metrics`

源码位置：[qwen_service/service.py 第 1361 行](../../../qwen_service/service.py#L1361)。类型：`FunctionDef`。

```python
QwenDecisionService.metrics(self) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `QwenDecisionService.close`

源码位置：[qwen_service/service.py 第 1384 行](../../../qwen_service/service.py#L1384)。类型：`FunctionDef`。

```python
QwenDecisionService.close(self, *, wait: bool=False) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `QwenDecisionService._release_slot`

源码位置：[qwen_service/service.py 第 1387 行](../../../qwen_service/service.py#L1387)。类型：`FunctionDef`。

```python
QwenDecisionService._release_slot(self, _future: Future[Any]) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `QwenDecisionService._increment`

源码位置：[qwen_service/service.py 第 1392 行](../../../qwen_service/service.py#L1392)。类型：`FunctionDef`。

```python
QwenDecisionService._increment(self, name: str) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_gpu_metrics`

源码位置：[qwen_service/service.py 第 1397 行](../../../qwen_service/service.py#L1397)。类型：`FunctionDef`。

```python
_gpu_metrics() -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_planner_scene`

源码位置：[qwen_service/service.py 第 1417 行](../../../qwen_service/service.py#L1417)。类型：`FunctionDef`。

```python
_planner_scene(request: Mapping[str, Any]) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_percentile` 调用：`int`, `len`, `math.ceil`, `math.floor`, `sorted`.
- `_planner_step` 调用：`list`.
- `_gpu_metrics` 调用：`int`, `torch.cuda.current_device`, `torch.cuda.get_device_name`, `torch.cuda.is_available`, `torch.cuda.mem_get_info`, `torch.cuda.memory_allocated`, `torch.cuda.memory_reserved`, `type`.
- `_planner_scene` 调用：`dict`, `isinstance`, `request.get`, `request['constraints'].get`.
- `__init__` 调用：`BoundedSemaphore`, `FileNotFoundError`, `InterfaceRegistry`, `Lock`, `OpenAI`, `Path`, `Path(image_root).expanduser`, `Path(image_root).expanduser().resolve`, `Path(model_path).expanduser`, `Path(model_path).expanduser().resolve`, `PlanValidator`, `QwenServiceConfig`, `RuntimeError`, `StrictQwenVLAdapter.from_local_checkpoint`, `ThreadPoolExecutor`, `TransformersQwen25VLBackend`, `TypeError`, `ValueError`, `base_url.rstrip`, `base_url.strip`, `callable`, `getattr`, `int`, `model.strip`, `path.is_dir`, `super`, `super().__init__`.
- `to_dict` 调用：`str`.
- `__post_init__` 调用：`ValueError`, `float`, `getattr`, `isinstance`, `math.isfinite`, `type`.
- `infer` 调用：`QwenInputContext`, `RuntimeError`, `ServiceFailure`, `ValueError`, `_planner_scene`, `_planner_step`, `any`, `behavior.removesuffix`, `behavior.removesuffix('_LEFT').removesuffix`, `build_planner_v2_prompt`, `capabilities.get`, `constraints.get`, `content.append`, `dict`, `direction.lower`, `float`, `future.add_done_callback`, `future.result`, `getattr`, `hint.get`, `hinted_intent.removeprefix`, `int`, `isinstance`, `item.get`, `len`, `min`, `parse_maneuver_plan`, `payload.get`, `request.get`, `routing.get`, `self._choice_codes`, `self._choice_prompt`, `self._client.chat.completions.create`, `self._clock_ns`, `self._executor.submit`, `self._expanded_steps`, `self._image_data_url`, `self._increment`, `self._latencies_ms.append`, `self._resolve_image`, `self._slots.acquire`, `self._to_plan`, `self._traffic_stop_required`, `self.adapter`, `self.backend.generate`, `self.backend.health`, `self.plan_validator.validate`, `self.registry.validate`, `set`, `steps.append`, `steps.extend`, `str`, `str(getattr(getattr(choices[0], 'message', None), 'content', '')).strip`, `str(getattr(getattr(choices[0], 'message', None), 'content', '')).strip().upper`, `str(hint.get('direction', '')).upper`, `str(hint.get('intent', '')).upper`, `text.lower`, `time.monotonic_ns`, `time.perf_counter_ns`, `type`.
- `_resolve_image` 调用：`(self.image_root / candidate).resolve`, `FileNotFoundError`, `Path`, `Path(str(value)).expanduser`, `ValueError`, `candidate.is_absolute`, `candidate.is_file`, `candidate.relative_to`, `candidate.resolve`, `str`.
- `_expanded_steps` 调用：`dict`, `float`, `isinstance`, `item.get`, `len`, `next`, `request.get`, `request['constraints'].get`, `self._pedestrian_then_overtake_requested`, `self._persistent_post_maneuver_speed_requested`, `self._resume_requested`, `self._step`, `steps.append`, `str`, `str(item.get('class', '')).casefold`.
- `_pedestrian_then_overtake_requested` 调用：`any`, `request.get`, `str`, `str(request.get('source_text', '')).casefold`.
- `_persistent_post_maneuver_speed_requested` 调用：`any`, `float`, `hint.get`, `isinstance`, `math.isfinite`, `request.get`, `str`, `str(hint.get('intent', '')).upper`, `str(request.get('source_text', '')).casefold`, `type`.
- `_resume_requested` 调用：`any`, `request.get`, `str`, `str(request.get('source_text', '')).casefold`.
- `_clearance_observation_requested` 调用：`any`, `request.get`, `str`, `str(request.get('source_text', '')).casefold`.
- `_transient_merge_hazard` 调用：`any`, `request.get`, `str`, `str(request.get('source_text', '')).casefold`.
- `_choice_codes` 调用：`behavior.removesuffix`, `behavior.removesuffix('_LEFT').removesuffix`, `bool`, `hint.get`, `isinstance`, `request.get`, `request.get('scene_summary', {}).get`, `request['constraints'].get`, `self._CHOICES.items`, `self._CHOICES[code].endswith`, `self._traffic_stop_required`, `set`, `str`, `str(hint.get('direction', '')).upper`, `str(hint.get('intent', '')).upper`, `str(request.get('scene_summary', {}).get('risk_level', '')).upper`, `{'KEEP_LANE': {'A'}, 'SET_SPEED': {'B'}, 'SLOW_DOWN': {'C'}, 'STOP': {'D'}, 'YIELD': {'E'}, 'FOLLOW': {'F'}, 'CHANGE_LANE': {'G', 'H'}, 'TURN': {'I', 'J'}, 'AVOID_OBSTACLE': {'K'}, 'RETURN_TO_LANE': {'L'}, 'PULL_OVER': {'M'}}.get`.
- `_traffic_stop_required` 调用：`isinstance`, `request.get`, `str`, `str(summary.get('traffic_light', '')).upper`, `summary.get`.
- `_choice_prompt` 调用：`' '.join`, `isinstance`, `json.dumps`, `list`, `request.get`, `str`, `str(request.get('rgb_ref', '')).lower`.
- `_step` 调用：`behavior.endswith`, `behavior.rsplit`, `behavior.startswith`, `capabilities.get`, `float`, `hint.get`, `isinstance`, `item.get`, `min`, `raw_requested_target.strip`, `request.get`, `request['constraints'].get`, `self._clearance_observation_requested`, `self._transient_merge_hazard`, `str`, `str(hint.get('direction', '')).upper`, `str(hint.get('intent', '')).upper`, `str(item.get('class', '')).lower`, `str(item.get('class', '')).strip`, `str(item.get('class', '')).strip().lower`, `str(item.get('relation', '')).lower`, `type`, `{'STOP': 'STOPPED', 'HOLD': 'HOLD_FRAMES', 'PULL_OVER': 'STOPPED', 'FOLLOW': 'TARGET_GAP_REACHED', 'AVOID_OBSTACLE': 'TARGET_PASSED', 'RETURN_TO_LANE': 'LANE_CENTERED', 'CHANGE_LANE_LEFT': 'LANE_CENTERED', 'CHANGE_LANE_RIGHT': 'LANE_CENTERED', 'TURN_LEFT': 'JUNCTION_EXITED', 'TURN_RIGHT': 'JUNCTION_EXITED', 'KEEP_LANE': 'HOLD_FRAMES', 'SLOW_DOWN': 'SPEED_BELOW', 'YIELD': 'HOLD_FRAMES'}.get`.
- `_image_data_url` 调用：`Image.open`, `ImageOps.pad`, `RuntimeError`, `base64.b64encode`, `base64.b64encode(buffer.getvalue()).decode`, `base64.b64encode(encoded).decode`, `buffer.getvalue`, `image.convert`, `image.save`, `io.BytesIO`, `path.read_bytes`.
- `close` 调用：`callable`, `close`, `getattr`, `self._executor.shutdown`.
- `_to_plan` 调用：`decision.get`, `float`, `min`, `request['constraints'].get`, `str`, `str(decision['action']).upper`, `time.monotonic_ns`, `{'START': ('KEEP_LANE', 'KEEP_LANE'), 'KEEP_LANE': ('KEEP_LANE', 'KEEP_LANE'), 'SET_SPEED': ('SET_SPEED', 'SET_SPEED'), 'SLOW_DOWN': ('SLOW_DOWN', 'SLOW_DOWN'), 'STOP': ('STOP', 'STOP'), 'EMERGENCY_STOP': ('STOP', 'STOP')}.get`.
- `health` 调用：`_gpu_metrics`, `bool`, `self.backend.health`.
- `metrics` 调用：`_gpu_metrics`, `_percentile`, `bool`, `dict`, `len`, `list`, `max`, `statistics.fmean`.
- `_release_slot` 调用：`self._slots.release`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 393 行：`FileNotFoundError(f'local Qwen checkpoint not found: {path}')`。
- `__init__`，第 464 行：`ValueError('vLLM base URL and model must be non-empty')`。
- `__init__`，第 468 行：`RuntimeError('vLLM service backend requires the openai package')`。
- `__init__`，第 479 行：`ValueError('planner_v2 fixes images at 224x224 (64 visual tokens)')`。
- `__init__`，第 1108 行：`FileNotFoundError(f'local Qwen checkpoint not found: {path}')`。
- `__init__`，第 1238 行：`TypeError('backend must provide infer() and health()')`。
- `__init__`，第 1241 行：`ValueError("qwen_mode must be 'atomic_v1' or 'planner_v2'")`。
- `__post_init__`，第 76 行：`ValueError('timeout_ms must be finite and positive')`。
- `__post_init__`，第 79 行：`ValueError(f'{name} must be a positive integer')`。
- `_image_data_url`，第 1071 行：`RuntimeError('vLLM image encoding requires Pillow')`。
- `_resolve_image`，第 428 行：`ValueError('rgb_ref must be relative when image_root is configured')`。
- `_resolve_image`，第 433 行：`ValueError('rgb_ref escapes image_root')`。
- `_resolve_image`，第 435 行：`FileNotFoundError(f'Qwen RGB input not found: {candidate}')`。
- `_resolve_image`，第 1060 行：`ValueError('rgb_ref must be relative when image_root is configured')`。
- `_resolve_image`，第 1064 行：`FileNotFoundError(f'Qwen RGB input not found: {candidate}')`。
- `infer`，第 90 行：`RuntimeError(self.reason)`。
- `infer`，第 410 行：`ValueError('planner_v2 request is missing routing metadata')`。
- `infer`，第 509 行：`RuntimeError('vLLM returned no planner choices')`。
- `infer`，第 512 行：`ValueError(f'vLLM returned invalid constrained planner choice: {raw!r}')`。
- `infer`，第 527 行：`ValueError(f'Qwen behavior {behavior} violates allowed_behaviors')`。
- `infer`，第 1276 行：`ServiceFailure(400, 'INVALID_REQUEST', str(error), request_id=request_id)`。
- `infer`，第 1281 行：`ServiceFailure(400, 'INVALID_DEADLINE', 'deadline must follow creation', request_id=request_id)`。
- `infer`，第 1284 行：`ServiceFailure(408, 'REQUEST_EXPIRED', 'request deadline elapsed', request_id=request_id)`。
- `infer`，第 1288 行：`ServiceFailure(503, 'MODEL_UNAVAILABLE', reason, request_id=request_id)`。
- `infer`，第 1291 行：`ServiceFailure(429, 'CONCURRENCY_LIMIT', 'Qwen service is busy', request_id=request_id)`。
- `infer`，第 1304 行：`ServiceFailure(504, 'MODEL_TIMEOUT', 'Qwen inference exceeded deadline', request_id=request_id)`。
- `infer`，第 1308 行：`ServiceFailure(502, code, str(error), request_id=request_id)`。
- `infer`，第 1311 行：`ServiceFailure(500, 'MODEL_ERROR', f'{type(error).__name__}: {error}', request_id=request_id)`。
- `infer`，第 1329 行：`ServiceFailure(502, code, str(error), request_id=request_id)`。
- `infer`，第 1332 行：`ServiceFailure(502, 'MODEL_ID_MISMATCH', 'model output IDs do not match request', request_id=request_id)`。
- `infer`，第 1335 行：`ServiceFailure(502, 'INVALID_MODEL_VALIDITY', 'model output validity exceeds request', request_id=request_id)`。
- `infer`，第 1338 行：`ServiceFailure(502, 'LOW_LEVEL_OUTPUT_FORBIDDEN', 'model output contains vehicle control', request_id=request_id)`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [integration/qwen_boundary.py](../../../integration/qwen_boundary.py)
- [integration/qwen_plan_adapter.py](../../../integration/qwen_plan_adapter.py)
- [integration/qwen_vl_adapter.py](../../../integration/qwen_vl_adapter.py)
- [runtime/interface_registry.py](../../../runtime/interface_registry.py)
- [runtime/plan_validator.py](../../../runtime/plan_validator.py)

静态 import 消费者（含测试）：

- [qwen_service/__init__.py](../../../qwen_service/__init__.py)
- [qwen_service/server.py](../../../qwen_service/server.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-qwen.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `qwen_service/service.py`

来源 SHA256：`da46a5617c89b3ca149666b0dbdda3fc9a02a0afa3d06e2701fa3da74bbfd72a`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `DecisionBackend.model_id` | `str` | `无声明默认；构造/赋值方提供` |
| `DecisionBackend.production_ready` | `bool` | `无声明默认；构造/赋值方提供` |
| `QwenServiceConfig.timeout_ms` | `float` | `300.0` |
| `QwenServiceConfig.max_concurrency` | `int` | `1` |
| `QwenServiceConfig.max_request_bytes` | `int` | `262144` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `QwenServiceConfig.__post_init__` / 76 | `type(self.timeout_ms) not in (int, float) or isinstance(self.timeout_ms, bool) or (not math.isfinite(float(self.timeout_ms))) or (self.timeout_ms <= 0)` | `raise ValueError('timeout_ms must be finite and positive')` |
| `QwenServiceConfig.__post_init__` / 79 | `type(getattr(self, name)) is not int or getattr(self, name) < 1` | `raise ValueError(f'{name} must be a positive integer')` |
| `UnavailableBackend.infer` / 90 | `本地无直接if；检查上下文` | `raise RuntimeError(self.reason)` |
| `LocalQwenPlannerBackend.__init__` / 393 | `not path.is_dir()` | `raise FileNotFoundError(f'local Qwen checkpoint not found: {path}')` |
| `LocalQwenPlannerBackend.infer` / 410 | `not isinstance(routing, Mapping)` | `raise ValueError('planner_v2 request is missing routing metadata')` |
| `LocalQwenPlannerBackend._resolve_image` / 428 | `NOT (self.image_root is None) AND candidate.is_absolute()` | `raise ValueError('rgb_ref must be relative when image_root is configured')` |
| `LocalQwenPlannerBackend._resolve_image` / 433 | `NOT (self.image_root is None) AND except ValueError` | `raise ValueError('rgb_ref escapes image_root') from error` |
| `LocalQwenPlannerBackend._resolve_image` / 435 | `not candidate.is_file()` | `raise FileNotFoundError(f'Qwen RGB input not found: {candidate}')` |
| `VllmQwenPlannerBackend.__init__` / 464 | `not base_url.strip() or not model.strip()` | `raise ValueError('vLLM base URL and model must be non-empty')` |
| `VllmQwenPlannerBackend.__init__` / 468 | `except ImportError` | `raise RuntimeError('vLLM service backend requires the openai package') from error` |
| `VllmQwenPlannerBackend.__init__` / 479 | `int(image_max_side) != 224` | `raise ValueError('planner_v2 fixes images at 224x224 (64 visual tokens)')` |
| `VllmQwenPlannerBackend.infer` / 509 | `not choices` | `raise RuntimeError('vLLM returned no planner choices')` |
| `VllmQwenPlannerBackend.infer` / 512 | `raw not in self._CHOICES` | `raise ValueError(f'vLLM returned invalid constrained planner choice: {raw!r}')` |
| `VllmQwenPlannerBackend.infer` / 527 | `behavior not in {'HOLD'} and behavior not in allowed and (normalized not in allowed)` | `raise ValueError(f'Qwen behavior {behavior} violates allowed_behaviors')` |
| `VllmQwenPlannerBackend._resolve_image` / 1060 | `NOT (self.image_root is None) AND candidate.is_absolute()` | `raise ValueError('rgb_ref must be relative when image_root is configured')` |
| `VllmQwenPlannerBackend._resolve_image` / 1064 | `not candidate.is_file()` | `raise FileNotFoundError(f'Qwen RGB input not found: {candidate}')` |
| `VllmQwenPlannerBackend._image_data_url` / 1071 | `except ImportError` | `raise RuntimeError('vLLM image encoding requires Pillow') from error` |
| `LocalQwenBackend.__init__` / 1108 | `not path.is_dir()` | `raise FileNotFoundError(f'local Qwen checkpoint not found: {path}')` |
| `QwenDecisionService.__init__` / 1238 | `not callable(getattr(backend, 'infer', None)) or not callable(getattr(backend, 'health', None))` | `raise TypeError('backend must provide infer() and health()')` |
| `QwenDecisionService.__init__` / 1241 | `qwen_mode not in {'atomic_v1', 'planner_v2'}` | `raise ValueError("qwen_mode must be 'atomic_v1' or 'planner_v2'")` |
| `QwenDecisionService.infer` / 1276 | `except InterfaceValidationError` | `raise ServiceFailure(400, 'INVALID_REQUEST', str(error), request_id=request_id) from error` |
| `QwenDecisionService.infer` / 1281 | `request['deadline_ns'] <= request['created_at_ns']` | `raise ServiceFailure(400, 'INVALID_DEADLINE', 'deadline must follow creation', request_id=request_id)` |
| `QwenDecisionService.infer` / 1284 | `now >= request['deadline_ns']` | `raise ServiceFailure(408, 'REQUEST_EXPIRED', 'request deadline elapsed', request_id=request_id)` |
| `QwenDecisionService.infer` / 1288 | `not healthy` | `raise ServiceFailure(503, 'MODEL_UNAVAILABLE', reason, request_id=request_id)` |
| `QwenDecisionService.infer` / 1291 | `not self._slots.acquire(blocking=False)` | `raise ServiceFailure(429, 'CONCURRENCY_LIMIT', 'Qwen service is busy', request_id=request_id)` |
| `QwenDecisionService.infer` / 1304 | `except FutureTimeout` | `raise ServiceFailure(504, 'MODEL_TIMEOUT', 'Qwen inference exceeded deadline', request_id=request_id) from error` |
| `QwenDecisionService.infer` / 1308 | `except (QwenPlanParseError, PlanValidationError)` | `raise ServiceFailure(502, code, str(error), request_id=request_id) from error` |
| `QwenDecisionService.infer` / 1311 | `except Exception` | `raise ServiceFailure(500, 'MODEL_ERROR', f'{type(error).__name__}: {error}', request_id=request_id) from error` |
| `QwenDecisionService.infer` / 1329 | `except (InterfaceValidationError, PlanValidationError)` | `raise ServiceFailure(502, code, str(error), request_id=request_id) from error` |
| `QwenDecisionService.infer` / 1332 | `plan['request_id'] != request_id or plan['command_id'] != request['command_id']` | `raise ServiceFailure(502, 'MODEL_ID_MISMATCH', 'model output IDs do not match request', request_id=request_id)` |
| `QwenDecisionService.infer` / 1335 | `plan['valid_until_ns'] > request['deadline_ns'] or plan['created_at_ns'] >= plan['valid_until_ns']` | `raise ServiceFailure(502, 'INVALID_MODEL_VALIDITY', 'model output validity exceeds request', request_id=request_id)` |
| `QwenDecisionService.infer` / 1338 | `any((name in plan for name in ('throttle', 'brake', 'steer')))` | `raise ServiceFailure(502, 'LOW_LEVEL_OUTPUT_FORBIDDEN', 'model output contains vehicle control', request_id=request_id)` |
