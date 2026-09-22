# Qwen HTTP service and historical protocol

## 开发维护先读：实际语义

以下功能页说明实现理由、分支、接口含义、改动联动与验证。先读这些内容，再按逐文件索引定位方法；不要用函数名推断业务语义。

- [服务模式、动作组装与health](../functions/qwen-service-semantics.md)

Parent: [Support module](../modules/support.md).

## Functions and sources

[server.py](../../../qwen_service/server.py), invoked with python -m qwen_service, exposes /health, /infer and /metrics through QwenHTTPServer and QwenDecisionService. [client.py](../../../qwen_service/client.py) accepts Mapping requests, supports request_transform and per-request timing; HTTP errors and connection failures become RuntimeError.

[service.py](../../../qwen_service/service.py) owns concurrency admission, timeouts, output validation, health and metrics. Backends: UnavailableBackend, deterministic decision/Planner V2 test backends, LocalQwenBackend, LocalQwenPlannerBackend and VllmQwenPlannerBackend. Deterministic implementations are test-only; local Transformers implementations are compatibility paths. Production vLLM chooses one constrained semantic token, then _choice_codes/_expanded_steps/_step assemble allowed behaviors, compound maneuvers and target/speed fields deterministically. Do not describe this as unconstrained model-generated complete plans.

[runtime.py](../../../qwen_service/runtime.py) contains the separate historical QwenServiceRuntime using integration.qwen_boundary.QwenInputContext and decision responses. It is not interchangeable with QwenDecisionService.

## Contract and parameters

ModelRequest/ManeuverPlan contracts live under interfaces; [prompt_and_schema.md](../../../qwen_service/prompt_and_schema.md) describes prompts. Service timeout_ms/max_concurrency differ from backend HTTP timeout. vLLM accepts model/base_url/image_root; image size is fixed at 224 and max_new_tokens is forced to 1 despite the constructor parameter. Model output may not include throttle/brake/steer. Timeout, saturation, confidence and schema failures must remain visible to upstream safety handling.

## Confirmed inconsistencies

- service.py:442 sets production_ready=True; health at 483-484 returns true without contacting vLLM; 1344-1352 consequently reports READY/production_ready for configured but unreachable backends. A readiness probe and model identity/disconnection regression are needed; this audit has not changed behavior.
- tests/test_server.py:10 imports removed create_server; lines 29/83 instantiate historical QwenServiceRuntime. Actual python -m pytest -q qwen_service/tests/test_server.py --collect-only fails with ImportError. pytest.ini does not include this directory by default.
- Historical runtime and current service must be explicitly migrated or isolated, not silently mixed through new compatibility patches.

## Dependencies, validation and coordinated edits

Production service tests also live under integration/tests (qwen_service/planner/vllm names). tools/qwen_remote_smoke.py probes the remote boundary; docs/runbooks/QWEN_REMOTE.md owns deployment procedure. Contract edits affect client/server/backend, interfaces, runtime orchestration, Student TeacherBackend, prompts and fault tests. Semantic rule edits also affect scenes, labels and evaluation; retain raw model output so rule contributions remain distinguishable.


## 模块接口与参数核对（2026-09-20）

QwenDecisionService包装backend、Schema、并发/超时和响应错误。atomic_v1与planner_v2有不同构造路径；health与模型实际可达不能混同，当前health问题见AUDIT A04。

### 参数语义与生效边界

QwenServiceConfig默认timeout_ms300、max_concurrency1、max_request_bytes262144；VllmQwenPlannerBackend默认timeout_s15、max_new_tokens256、image_max_side224、jpeg_quality75。注意max_new_tokens=256只是签名默认：该vLLM Planner构造函数实际强制self.max_new_tokens=1；image_max_side非224直接拒绝。服务超时、HTTP超时与编排超时分别核对。

### 上下游与修改影响

STOP目标构造不绑定target，FOLLOW等绑定可见目标；改动作字段应查Schema/validator/collector/验收。模型profile、运行Teacher manifest与历史cohort身份不同，不全局替换旧manifest。

### [qwen_service/service.py](../../../qwen_service/service.py) 的入口与声明

```python
DecisionBackend.infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]
DecisionBackend.health(self) -> tuple[bool, str]
ServiceFailure.__init__(self, status_code: int, error_code: str, message: str, *, request_id: str | None=None) -> None
ServiceFailure.to_dict(self) -> dict[str, Any]
UnavailableBackend.__init__(self, reason: str='no local Qwen checkpoint configured') -> None
UnavailableBackend.infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]
UnavailableBackend.health(self) -> tuple[bool, str]
DeterministicTestBackend.health(self) -> tuple[bool, str]
DeterministicTestBackend.infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]
DeterministicPlannerV2Backend.health(self) -> tuple[bool, str]
DeterministicPlannerV2Backend.infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]
LocalQwenPlannerBackend.__init__(self, model_path: str | Path, *, image_root: str | Path | None=None, max_new_tokens: int=256, min_pixels: int=64 * 28 * 28, max_pixels: int=256 * 28 * 28) -> None
LocalQwenPlannerBackend.health(self) -> tuple[bool, str]
LocalQwenPlannerBackend.infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]
VllmQwenPlannerBackend.__init__(self, *, base_url: str, model: str, image_root: str | Path | None=None, api_key: str='unused', timeout_s: float=15.0, max_new_tokens: int=256, image_max_side: int=224, jpeg_quality: int=75) -> None
VllmQwenPlannerBackend.health(self) -> tuple[bool, str]
VllmQwenPlannerBackend.infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]
VllmQwenPlannerBackend.close(self) -> None
LocalQwenBackend.__init__(self, model_path: str | Path, *, image_root: str | Path | None=None, max_new_tokens: int=48, min_pixels: int=64 * 28 * 28, max_pixels: int=256 * 28 * 28) -> None
LocalQwenBackend.health(self) -> tuple[bool, str]
LocalQwenBackend.infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]
QwenDecisionService.__init__(self, backend: DecisionBackend, *, config: QwenServiceConfig | None=None, registry: InterfaceRegistry | None=None, qwen_mode: str='atomic_v1', clock_ns: Any=time.monotonic_ns) -> None
QwenDecisionService.infer(self, payload: Mapping[str, Any]) -> dict[str, Any]
QwenDecisionService.health(self) -> dict[str, Any]
QwenDecisionService.metrics(self) -> dict[str, Any]
QwenDecisionService.close(self, *, wait: bool=False) -> None
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `DecisionBackend.model_id` | `str` | `无声明默认（构造/赋值方提供）` |
| `DecisionBackend.production_ready` | `bool` | `无声明默认（构造/赋值方提供）` |
| `QwenServiceConfig.timeout_ms` | `float` | `300.0` |
| `QwenServiceConfig.max_concurrency` | `int` | `1` |
| `QwenServiceConfig.max_request_bytes` | `int` | `262144` |

### [qwen_service/server.py](../../../qwen_service/server.py) 的入口与声明

```python
QwenHTTPServer.__init__(self, address: tuple[str, int], service: QwenDecisionService) -> None
QwenRequestHandler.setup(self) -> None
QwenRequestHandler.do_GET(self) -> None
QwenRequestHandler.do_POST(self) -> None
QwenRequestHandler.log_message(self, format: str, *args: Any) -> None
build_service(args: argparse.Namespace) -> QwenDecisionService
main() -> None
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `QwenRequestHandler.server` | `QwenHTTPServer` | `无声明默认（构造/赋值方提供）` |

以上为核心交接入口；模块内其余实现、CLI和资源的完整字段/拒绝条件见本页功能小文档索引。类型未声明的返回值不凭名称推断。当前代码基线fe1ba839，静态复核不证明实际CARLA/GPU/板端运行成功。

## 功能小文档完整索引

以下功能页分别记录实现入口、输入输出声明、内部调用、异常、配置和静态上下游；测试文件保留在源码索引中。

- [qwen_service/__init__.py](../functions/qwen_service--__init__--py.md)
- [qwen_service/__main__.py](../functions/qwen_service--__main__--py.md)
- [qwen_service/client.py](../functions/qwen_service--client--py.md)
- [qwen_service/runtime.py](../functions/qwen_service--runtime--py.md)
- [qwen_service/server.py](../functions/qwen_service--server--py.md)
- [qwen_service/service.py](../functions/qwen_service--service--py.md)

## 诊断与维护交接

本模块证据：profile/SHA、原始响应、构造后Plan；health恒真见AUDIT A04。功能实现与上下游见本页原索引；跨模块回查[追踪矩阵](../TRACEABILITY.md)与[诊断入口](../DIAGNOSIS.md)。实际run必须核对版本，未执行的检查不视为已通过。

专项记录：[目标身份、空值与验收归因](../functions/target-grounding.md)。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `qwen_service/tests/test_runtime.py`

来源 SHA256：`bdc08ab96527b26c2c386f9b103d6f0771d0f9c882fc9b1d884d61c21398e02d`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_BlockingAdapter.infer` / 72 | `not self.release.wait(timeout=2.0)` | `raise RuntimeError('test did not release inference')` |
### `qwen_service/tests/test_server.py`

来源 SHA256：`8d43fe41d63cb9f69299b27a3c44235ab7cdd7b98691397312d80be5c14ee2b4`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。

### `qwen_service/tests/test_stress_set_semantic_repair.py`

来源 SHA256：`a38b27a262e69c5f0c9225acc15d6c7c3e7e2b9af9c7eec53cf4fb3bd83dcbed`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。

## 第17模块逐入口精读结论（2026-09-22）

本轮按基线 `4e41f990` 核对6份实现页和2份语义页，改写78处泛用占位。结论覆盖当前HTTP服务、client、历史runtime及全部backend，但不把确定性backend或静态health当成真实Qwen证据。

### 请求到计划的实际边界

`QwenServiceClient` 负责JSON HTTP、request transform与客户端计时；`QwenRequestHandler` 只暴露 `/health`、`/infer`、`/metrics`；`QwenDecisionService` 负责请求大小、Schema、并发槽位、future超时、响应Schema、计数和延迟分位数。backend才拥有模型推理。服务超时、客户端HTTP超时和车辆编排超时属于三个时钟，必须分别记录。

`atomic_v1` 返回单动作决策，`planner_v2` 返回 `ManeuverPlan V2`。当前vLLM planner不是让模型自由生成完整JSON，而是约束生成一个语义choice，再由确定性代码展开步骤、目标、速度与完成条件；因此评测要同时保留模型choice和规则组装后的计划，不能把全部正确率归因给模型。

### Backend身份与健康语义

- unavailable与两个deterministic backend都不是生产模型；它们只适合合同、故障和流程测试。
- local Transformers和vLLM路径的模型加载、图像解析与生成栈不同，测试通过不能互相代替。
- vLLM planner签名允许 `max_new_tokens=256`，构造后实际固定为1；`image_max_side` 必须为224。调用记录应写生效值而非只抄CLI默认。
- A04仍未关闭：vLLM backend当前health不探测远端模型，配置完成可被上报为READY。正式门禁必须另有可达性、模型ID/revision/fingerprint和真实infer证据。
- A05仍未关闭：旧 `qwen_service/tests/test_server.py` 使用已删除的 `create_server` 和历史runtime，不能代表当前server回归。

### 修改联动与门禁

改请求/计划字段时同步Interface Schema、client/server、backend、orchestrator、Teacher backend、场景合同和数据标签；改语义规则时还要重跑目标排序、复合动作、故障注入与闭环终态。最低发布证据包括固定源码SHA、模型exact revision/fingerprint、启动参数、health与独立infer、原始请求/响应、Schema结果及超时/并发测试；缺少任一身份项时只能称服务Smoke。
