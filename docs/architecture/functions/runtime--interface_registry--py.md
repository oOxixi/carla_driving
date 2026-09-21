# interface_registry：功能记录

上级模块：[模块说明](../modules/vehicle-planner.md) · 实现：[runtime/interface_registry.py](../../../runtime/interface_registry.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [异步等待、旧结果拒绝与多层命令ID](async-plan-dispatch.md)
- [计划可行性校验与内部步骤展开](plan-validation-compilation.md)

## 功能职责与范围

Cached strict validation for A-owned JSON interface files.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

<a id="fn-interfacevalidationerror"></a>

### `InterfaceValidationError`

源码位置：[runtime/interface_registry.py 第 22 行](../../../runtime/interface_registry.py#L22)。类型：`ClassDef`。

One shared boundary payload failed its frozen V1 contract.

<a id="fn-interfaceregistry"></a>

### `InterfaceRegistry`

源码位置：[runtime/interface_registry.py 第 26 行](../../../runtime/interface_registry.py#L26)。类型：`ClassDef`。

管理7种共享 JSON Schema：driving_command/model_request/decision_plan/maneuver_plan/perception_state/control_command/execution_feedback。按名称缓存 validator 并加锁；它做载荷结构校验，不验证目标实时存在或动作可执行性。

<a id="fn-interfaceregistry---init--"></a>

### `InterfaceRegistry.__init__`

源码位置：[runtime/interface_registry.py 第 27 行](../../../runtime/interface_registry.py#L27)。类型：`FunctionDef`。

```python
InterfaceRegistry.__init__(self, root: str | Path | None=None) -> None
```

root=None 使用仓库 interfaces；自定义 root resolve 后使用。初始化空 validator 缓存和锁；此时不读所有 Schema，也不导入 jsonschema，warm/validate 才触发。

<a id="fn-interfaceregistry-validate"></a>

### `InterfaceRegistry.validate`

源码位置：[runtime/interface_registry.py 第 36 行](../../../runtime/interface_registry.py#L36)。类型：`FunctionDef`。

```python
InterfaceRegistry.validate(self, name: str, payload: object) -> dict[str, Any]
```

未知 name 抛 ValueError，非 Mapping 或首个 Schema 错误抛带字段路径的 InterfaceValidationError。通过后执行 allow_nan=False 的 JSON 往返深复制，拒绝非 JSON 对象/非有限数并切断嵌套可变引用；返回规范化 dict，不修改输入。

<a id="fn-interfaceregistry-warm"></a>

### `InterfaceRegistry.warm`

源码位置：[runtime/interface_registry.py 第 53 行](../../../runtime/interface_registry.py#L53)。类型：`FunctionDef`。

```python
InterfaceRegistry.warm(self, names: tuple[str, ...] | None=None) -> None
```

Compile validators before an official latency window begins.

names=None按排序预热全部7项，否则先确认每项都在允许集合；随后逐项加载缓存validator。无返回载荷、不运行实例数据校验，目的是避免首个请求承担jsonschema导入和编译开销。

<a id="fn-interfaceregistry--validator"></a>

### `InterfaceRegistry._validator`

源码位置：[runtime/interface_registry.py 第 61 行](../../../runtime/interface_registry.py#L61)。类型：`FunctionDef`。

```python
InterfaceRegistry._validator(self, name: str) -> Any
```

锁内按 name 获取缓存；首次惰性导入 jsonschema、读取 name.schema.json、选择对应草案 validator 并检查 Schema，再缓存。缺库转 RuntimeError，文件/JSON/Schema 错误向上传播；文件后续改变不会自动使已有缓存失效。

## 内部调用与异常路径

- `__init__` 调用：`Lock`, `Path`, `Path(__file__).resolve`, `Path(root).resolve`.
- `validate` 调用：`'.'.join`, `InterfaceValidationError`, `ValueError`, `dict`, `isinstance`, `json.dumps`, `json.loads`, `list`, `self._validator`, `sorted`, `str`, `validator.iter_errors`.
- `warm` 调用：`ValueError`, `any`, `self._validator`, `sorted`, `tuple`.
- `_validator` 调用：`RuntimeError`, `json.loads`, `jsonschema.validators.validator_for`, `path.read_text`, `self._validators.get`, `validator_type`, `validator_type.check_schema`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_validator`，第 69 行：`RuntimeError('jsonschema is required for shared interface validation')`。
- `validate`，第 38 行：`ValueError(f'unknown interface: {name!r}')`。
- `validate`，第 40 行：`InterfaceValidationError(f'{name} must be a JSON object')`。
- `validate`，第 46 行：`InterfaceValidationError(f'{name}.{location}: {first.message}')`。
- `validate`，第 51 行：`InterfaceValidationError(f'{name} is not strict JSON: {error}')`。
- `warm`，第 57 行：`ValueError('warm names must be known interfaces')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [car_control_D/control_runtime.py](../../../car_control_D/control_runtime.py)
- [car_control_D/execution_feedback.py](../../../car_control_D/execution_feedback.py)
- [challenge/distillation/label_encoder.py](../../../challenge/distillation/label_encoder.py)
- [challenge/export/validate_artifacts.py](../../../challenge/export/validate_artifacts.py)
- [challenge/planner/frozen_contracts.py](../../../challenge/planner/frozen_contracts.py)
- [challenge/planner/student_backend.py](../../../challenge/planner/student_backend.py)
- [challenge/planner/teacher_backend.py](../../../challenge/planner/teacher_backend.py)
- [challenge/tests/test_a1_student.py](../../../challenge/tests/test_a1_student.py)
- [integration/canonical_bridge.py](../../../integration/canonical_bridge.py)
- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/second_group_runtime.py](../../../integration/second_group_runtime.py)
- [perception/fusion_tracker.py](../../../perception/fusion_tracker.py)
- [qwen_service/service.py](../../../qwen_service/service.py)
- [runtime/healthcheck.py](../../../runtime/healthcheck.py)
- [runtime/orchestrator.py](../../../runtime/orchestrator.py)
- [runtime/plan_validator.py](../../../runtime/plan_validator.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-planner.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-runtime-interface-registry-py"></a>

### `runtime/interface_registry.py`

来源 SHA256：`8463cc9681576af1abc1a47d7e2ce623b6e3cd76810f3a6f3090654b1db23e26`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `InterfaceRegistry.validate` / 38 | `name not in INTERFACE_NAMES` | `raise ValueError(f'unknown interface: {name!r}')` |
| `InterfaceRegistry.validate` / 40 | `not isinstance(payload, Mapping)` | `raise InterfaceValidationError(f'{name} must be a JSON object')` |
| `InterfaceRegistry.validate` / 46 | `errors` | `raise InterfaceValidationError(f'{name}.{location}: {first.message}')` |
| `InterfaceRegistry.validate` / 51 | `except (TypeError, ValueError)` | `raise InterfaceValidationError(f'{name} is not strict JSON: {error}') from error` |
| `InterfaceRegistry.warm` / 57 | `any((name not in INTERFACE_NAMES for name in selected))` | `raise ValueError('warm names must be known interfaces')` |
| `InterfaceRegistry._validator` / 69 | `except ImportError` | `raise RuntimeError('jsonschema is required for shared interface validation') from error` |
