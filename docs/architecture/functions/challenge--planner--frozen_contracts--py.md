# frozen_contracts：功能记录

上级模块：[模块说明](../modules/challenge-planner.md) · 实现：[challenge/planner/frozen_contracts.py](../../../challenge/planner/frozen_contracts.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [Head解码、约束修复和就绪判定](student-plan-decoding.md)

## 功能职责与范围

Byte-level fingerprints for the Teacher/Student planner boundary.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `canonical_schema_sha256`

源码位置：[challenge/planner/frozen_contracts.py 第 18 行](../../../challenge/planner/frozen_contracts.py#L18)。类型：`FunctionDef`。

```python
canonical_schema_sha256(path: str | Path) -> str
```

读取 JSON Schema，按键排序、紧凑分隔符和 UTF-8 非 ASCII 保留形式重新序列化，再返回 SHA256。它消除空白/键顺序差异，但数组顺序、数值和字段语义变化仍改变指纹；文件/JSON错误直接传播。

### `assert_frozen_contracts`

源码位置：[challenge/planner/frozen_contracts.py 第 29 行](../../../challenge/planner/frozen_contracts.py#L29)。类型：`FunctionDef`。

```python
assert_frozen_contracts(registry: InterfaceRegistry) -> None
```

逐一核对 `model_request` 和 `maneuver_plan` 当前规范化指纹；任一不等即拒绝加载 Teacher/Student backend。它不核对其他五种接口，也不证明 producer/consumer 已迁移；真实合同变更必须走版本化 A1 更新。

## 内部调用与异常路径

- `canonical_schema_sha256` 调用：`Path`, `Path(path).read_text`, `hashlib.sha256`, `hashlib.sha256(canonical).hexdigest`, `json.dumps`, `json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode`, `json.loads`.
- `assert_frozen_contracts` 调用：`FROZEN_CONTRACT_SHA256.items`, `Path`, `RuntimeError`, `canonical_schema_sha256`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `assert_frozen_contracts`，第 34 行：`RuntimeError(f'frozen {name} contract changed: {actual} != {expected}; create a versioned A1 contract update before loading a backend')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [runtime/interface_registry.py](../../../runtime/interface_registry.py)

静态 import 消费者（含测试）：

- [challenge/export/export_onnx.py](../../../challenge/export/export_onnx.py)
- [challenge/export/validate_artifacts.py](../../../challenge/export/validate_artifacts.py)
- [challenge/planner/student_backend.py](../../../challenge/planner/student_backend.py)
- [challenge/planner/teacher_backend.py](../../../challenge/planner/teacher_backend.py)
- [challenge/tests/test_a1_student.py](../../../challenge/tests/test_a1_student.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-planner.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/planner/frozen_contracts.py`

来源 SHA256：`b06f36f56415ec508cfa74bef1fdb07425e8a138d87d98df41bd196418aaf7c9`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `assert_frozen_contracts` / 34 | `actual != expected` | `raise RuntimeError(f'frozen {name} contract changed: {actual} != {expected}; create a versioned A1 contract update before loading a backend')` |
