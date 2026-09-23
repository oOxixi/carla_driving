# teacher_backend：功能记录

上级模块：[模块说明](../modules/challenge-planner.md) · 实现：[challenge/planner/teacher_backend.py](../../../challenge/planner/teacher_backend.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [Head解码、约束修复和就绪判定](student-plan-decoding.md)

## 功能职责与范围

Strict adapter around the frozen Qwen Teacher backend.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `QwenTeacherBackend`

源码位置：[challenge/planner/teacher_backend.py 第 15 行](../../../challenge/planner/teacher_backend.py#L15)。类型：`ClassDef`。

Validate both sides of an existing Qwen Planner V2 implementation.

### `QwenTeacherBackend.__init__`

源码位置：[challenge/planner/teacher_backend.py 第 18 行](../../../challenge/planner/teacher_backend.py#L18)。类型：`FunctionDef`。

```python
QwenTeacherBackend.__init__(self, delegate: Any, *, registry: InterfaceRegistry | None=None) -> None
```

要求 delegate 暴露可调用 `infer`，保存 registry/validator，并在构造时复制 delegate 的 model_id 与 production_ready；随后核对 ModelRequest/ManeuverPlan 冻结指纹。复制的是构造时快照，delegate 后续改变就绪字段不会自动更新包装器。

### `QwenTeacherBackend.infer`

源码位置：[challenge/planner/teacher_backend.py 第 28 行](../../../challenge/planner/teacher_backend.py#L28)。类型：`FunctionDef`。

```python
QwenTeacherBackend.infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]
```

先验证并深复制 ModelRequest，再调用 delegate；返回计划由 PlanValidator 校验 schema、低层字段、请求/命令ID、时效及场景可行性。`allow_confirmation=True` 允许需确认计划返回，但不代表已获执行授权。

### `QwenTeacherBackend.health`

源码位置：[challenge/planner/teacher_backend.py 第 40 行](../../../challenge/planner/teacher_backend.py#L40)。类型：`FunctionDef`。

```python
QwenTeacherBackend.health(self) -> tuple[bool, str]
```

若 delegate 有 health，先调用并返回其 detail；包装器构造时的 production_ready 为假会强制返回假。没有 health 时直接返回生产就绪快照及 model_id。该检查不发起试推理，也不核对具体 Teacher revision/fingerprint。

## 内部调用与异常路径

- `__init__` 调用：`InterfaceRegistry`, `PlanValidator`, `TypeError`, `assert_frozen_contracts`, `bool`, `callable`, `getattr`, `str`.
- `infer` 调用：`self._delegate.infer`, `self._registry.validate`, `self._validator.validate`, `validation_scene`.
- `health` 调用：`bool`, `callable`, `getattr`, `health`, `str`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 20 行：`TypeError('delegate must provide infer(request)')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [challenge/planner/common.py](../../../challenge/planner/common.py)
- [challenge/planner/frozen_contracts.py](../../../challenge/planner/frozen_contracts.py)
- [runtime/interface_registry.py](../../../runtime/interface_registry.py)
- [runtime/plan_validator.py](../../../runtime/plan_validator.py)

静态 import 消费者（含测试）：

- [challenge/planner/__init__.py](../../../challenge/planner/__init__.py)
- [challenge/tests/test_a1_student.py](../../../challenge/tests/test_a1_student.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-planner.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/planner/teacher_backend.py`

来源 SHA256：`eb130409006b0dad2b0f0ee2061bd83dac1c7bfbd3b112371fcbcb3c76b0d0f5`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `QwenTeacherBackend.__init__` / 20 | `not callable(getattr(delegate, 'infer', None))` | `raise TypeError('delegate must provide infer(request)')` |
