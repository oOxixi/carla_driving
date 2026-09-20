# qwen_plan_adapter：功能记录

上级模块：[模块说明](../modules/vehicle-planner.md) · 实现：[integration/qwen_plan_adapter.py](../../../integration/qwen_plan_adapter.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [异步等待、旧结果拒绝与多层命令ID](async-plan-dispatch.md)
- [计划可行性校验与内部步骤展开](plan-validation-compilation.md)

## 功能职责与范围

Strict Qwen Planner V2 prompt, JSON parser, validation and compilation.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `PlannerV2Result.raw_summary: str`；默认：`未在声明处设置`。
- `PlannerV2Result.plan: Mapping[str, Any]`；默认：`未在声明处设置`。
- `PlannerV2Result.compiled: CompiledManeuverPlan`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

<a id="fn-qwenplanparseerror"></a>

### `QwenPlanParseError`

源码位置：[integration/qwen_plan_adapter.py 第 39 行](../../../integration/qwen_plan_adapter.py#L39)。类型：`ClassDef`。

模型文本不能解析成计划 JSON 对象时使用的 ValueError 子类；与 PlanValidationError 的语义/契约失败分开，后者有 reason_code。

<a id="fn-plannerv2result"></a>

### `PlannerV2Result`

源码位置：[integration/qwen_plan_adapter.py 第 44 行](../../../integration/qwen_plan_adapter.py#L44)。类型：`ClassDef`。

冻结结果容器，持有校验后的 ManeuverPlan 映射、编译计划及截断 raw_summary。dataclass 冻结属性不等于嵌套映射深度不可变。

<a id="fn-build-planner-v2-prompt"></a>

### `build_planner_v2_prompt`

源码位置：[integration/qwen_plan_adapter.py 第 50 行](../../../integration/qwen_plan_adapter.py#L50)。类型：`FunctionDef`。

```python
build_planner_v2_prompt(request: Mapping[str, Any], routing: QwenRoutingDecision | Mapping[str, Any], *, scene_capabilities: Mapping[str, Any] | None=None) -> str
```

将 request 序列化进 V2 提示，要求 JSON 对象、1–4 个语义步骤、严格 ID/目标/高层动作和禁止低层控制。转弯 30 秒、变道 12 秒、避障 20 秒是提示建议，不是此函数执行的参数校验；序列化错误在调用 infer 的 try 之前可能直接抛出。

<a id="fn-parse-maneuver-plan"></a>

### `parse_maneuver_plan`

源码位置：[integration/qwen_plan_adapter.py 第 87 行](../../../integration/qwen_plan_adapter.py#L87)。类型：`FunctionDef`。

```python
parse_maneuver_plan(raw: str | bytes | Mapping[str, Any]) -> dict[str, Any]
```

Mapping 经严格 JSON 往返复制并拒绝 NaN/Infinity；bytes 用 UTF-8 解码；str 必须去空白后以 { 开始、} 结束，JSONDecoder 必须消费完整文本且结果为对象，拒绝 fence/解释/尾部内容。注意字符串分支沿用 Python JSONDecoder，NaN/Infinity 常量可被解析；完整契约仍依赖后续 validator，不能把该函数单独当作严格 JSON 安全边界。

<a id="fn-qwenplannerv2adapter"></a>

### `QwenPlannerV2Adapter`

源码位置：[integration/qwen_plan_adapter.py 第 116 行](../../../integration/qwen_plan_adapter.py#L116)。类型：`ClassDef`。

Turn one backend JSON response into a validated, compiled plan.

<a id="fn-qwenplannerv2adapter---init--"></a>

### `QwenPlannerV2Adapter.__init__`

源码位置：[integration/qwen_plan_adapter.py 第 119 行](../../../integration/qwen_plan_adapter.py#L119)。类型：`FunctionDef`。

```python
QwenPlannerV2Adapter.__init__(self, generate: Callable[[str, str | None], str | bytes | Mapping[str, Any]], *, validator: PlanValidator | None=None, compiler: PlanCompiler | None=None) -> None
```

generate 必须可调用；未提供 validator/compiler 时创建默认 PlanValidator/PlanCompiler，last_raw_summary/last_error 初始化为空。generate 接收 prompt 和 rgb_ref；构造时不连接模型服务。

<a id="fn-qwenplannerv2adapter-infer"></a>

### `QwenPlannerV2Adapter.infer`

源码位置：[integration/qwen_plan_adapter.py 第 134 行](../../../integration/qwen_plan_adapter.py#L134)。类型：`FunctionDef`。

```python
QwenPlannerV2Adapter.infer(self, request: Mapping[str, Any], *, routing: QwenRoutingDecision | Mapping[str, Any], scene: Mapping[str, Any]) -> PlannerV2Result
```

构建 prompt，调用 generate、生成至多 512 字符摘要、解析、按 request_id/command_id 与 request.created_at_ns 校验并编译，成功清空 last_error 并返回 PlannerV2Result(raw_summary, plan, compiled)。try 内异常保存 last_error 并重新抛出；prompt 构建异常不经过该记录路径。这里的 now 是提交时间，不自行测量模型耗时，编排器还需完成时限检查。

<a id="fn--summary"></a>

### `_summary`

源码位置：[integration/qwen_plan_adapter.py 第 161 行](../../../integration/qwen_plan_adapter.py#L161)。类型：`FunctionDef`。

```python
_summary(raw: Any) -> str
```

将原始文本或 JSON 形式响应折叠空白并截断到 512 字符，用于诊断摘要；不是完整模型输出存档，也不能据此重放计划。

## 内部调用与异常路径

- `build_planner_v2_prompt` 调用：`TypeError`, `dict`, `isinstance`, `json.dumps`, `list`, `routing.features.to_dict`.
- `parse_maneuver_plan` 调用：`QwenPlanParseError`, `decoder.raw_decode`, `dict`, `isinstance`, `json.JSONDecoder`, `json.dumps`, `json.loads`, `raw.decode`, `raw.strip`, `text.endswith`, `text.startswith`, `text[end:].strip`.
- `_summary` 调用：`' '.join`, `dict`, `isinstance`, `json.dumps`, `len`, `raw.decode`, `str`, `text.split`.
- `__init__` 调用：`PlanCompiler`, `PlanValidator`, `TypeError`, `callable`.
- `infer` 调用：`PlannerV2Result`, `_summary`, `build_planner_v2_prompt`, `int`, `parse_maneuver_plan`, `request.get`, `self.compiler.compile`, `self.generate`, `self.validator.validate`, `str`, `type`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 127 行：`TypeError('generate must be callable')`。
- `build_planner_v2_prompt`，第 57 行：`TypeError('request must be a mapping')`。
- `build_planner_v2_prompt`，第 69 行：`TypeError('routing must be QwenRoutingDecision or mapping')`。
- `parse_maneuver_plan`，第 93 行：`QwenPlanParseError(f'MODEL_OUTPUT_NOT_STRICT_JSON: {error}')`。
- `parse_maneuver_plan`，第 98 行：`QwenPlanParseError('MODEL_OUTPUT_NOT_UTF8')`。
- `parse_maneuver_plan`，第 100 行：`QwenPlanParseError('MODEL_OUTPUT_MUST_BE_JSON_OBJECT')`。
- `parse_maneuver_plan`，第 103 行：`QwenPlanParseError('MODEL_OUTPUT_MUST_BE_BARE_JSON_OBJECT')`。
- `parse_maneuver_plan`，第 108 行：`QwenPlanParseError(f'MODEL_OUTPUT_INVALID_JSON: {error.msg}')`。
- `parse_maneuver_plan`，第 110 行：`QwenPlanParseError('MODEL_OUTPUT_HAS_TRAILING_CONTENT')`。
- `parse_maneuver_plan`，第 112 行：`QwenPlanParseError('MODEL_OUTPUT_MUST_BE_JSON_OBJECT')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [runtime/complexity_router.py](../../../runtime/complexity_router.py)
- [runtime/plan_compiler.py](../../../runtime/plan_compiler.py)
- [runtime/plan_validator.py](../../../runtime/plan_validator.py)

静态 import 消费者（含测试）：

- [integration/tests/test_qwen_plan_boundary.py](../../../integration/tests/test_qwen_plan_boundary.py)
- [integration/tests/test_qwen_service.py](../../../integration/tests/test_qwen_service.py)
- [qwen_service/service.py](../../../qwen_service/service.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-planner.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-integration-qwen-plan-adapter-py"></a>

### `integration/qwen_plan_adapter.py`

来源 SHA256：`ea8087cd7d502053b63a2c538b903208551543c55ea895324f544a4cf3f2ca4e`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `PlannerV2Result.raw_summary` | `str` | `无声明默认；构造/赋值方提供` |
| `PlannerV2Result.plan` | `Mapping[str, Any]` | `无声明默认；构造/赋值方提供` |
| `PlannerV2Result.compiled` | `CompiledManeuverPlan` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `build_planner_v2_prompt` / 57 | `not isinstance(request, Mapping)` | `raise TypeError('request must be a mapping')` |
| `build_planner_v2_prompt` / 69 | `NOT (isinstance(routing, QwenRoutingDecision)) AND NOT (isinstance(routing, Mapping))` | `raise TypeError('routing must be QwenRoutingDecision or mapping')` |
| `parse_maneuver_plan` / 93 | `isinstance(raw, Mapping) AND except (TypeError, ValueError)` | `raise QwenPlanParseError(f'MODEL_OUTPUT_NOT_STRICT_JSON: {error}') from error` |
| `parse_maneuver_plan` / 98 | `isinstance(raw, bytes) AND except UnicodeDecodeError` | `raise QwenPlanParseError('MODEL_OUTPUT_NOT_UTF8') from error` |
| `parse_maneuver_plan` / 100 | `not isinstance(raw, str)` | `raise QwenPlanParseError('MODEL_OUTPUT_MUST_BE_JSON_OBJECT')` |
| `parse_maneuver_plan` / 103 | `not text or text.startswith('') or (not (text.startswith('{') and text.endswith('}')))` | `raise QwenPlanParseError('MODEL_OUTPUT_MUST_BE_BARE_JSON_OBJECT')` |
| `parse_maneuver_plan` / 108 | `except json.JSONDecodeError` | `raise QwenPlanParseError(f'MODEL_OUTPUT_INVALID_JSON: {error.msg}') from error` |
| `parse_maneuver_plan` / 110 | `text[end:].strip()` | `raise QwenPlanParseError('MODEL_OUTPUT_HAS_TRAILING_CONTENT')` |
| `parse_maneuver_plan` / 112 | `not isinstance(payload, dict)` | `raise QwenPlanParseError('MODEL_OUTPUT_MUST_BE_JSON_OBJECT')` |
| `QwenPlannerV2Adapter.__init__` / 127 | `not callable(generate)` | `raise TypeError('generate must be callable')` |
| `QwenPlannerV2Adapter.infer` / 156 | `except Exception` | `raise` |
