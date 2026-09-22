# artifact：功能记录

上级模块：[模块说明](../modules/challenge-hil.md) · 实现：[challenge/hil/artifact.py](../../../challenge/hil/artifact.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [Adapter能力、时钟域与测量范围](hil-trace-semantics.md)

## 功能职责与范围

Independent verification of a model artifact (FP32 or INT8 ONNX).

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_shape_of`

源码位置：[challenge/hil/artifact.py 第 27 行](../../../challenge/hil/artifact.py#L27)。类型：`FunctionDef`。

```python
_shape_of(value: Any) -> list[int]
```

`_shape_of` 实现本文件对应的HIL测量辅助步骤；具体输入、阶段、副作用和异常见本页签名/调用/拒绝表，修改时须同步schema与报告。

### `verify_onnx_artifact`

源码位置：[challenge/hil/artifact.py 第 31 行](../../../challenge/hil/artifact.py#L31)。类型：`FunctionDef`。

```python
verify_onnx_artifact(onnx_path: str | Path, *, repo_root: str | Path | None=None, reference_structure: str | Path | None=None, expected_opset: int | None=17) -> dict[str, Any]
```

`verify_onnx_artifact` 检查runtime合同、artifact、输出一致性、结构或身份完整性；结果只覆盖声明能力，model-only与full-chain、宿主与板端证据不得混写。

### `verify_onnx_artifact.check`

源码位置：[challenge/hil/artifact.py 第 48 行](../../../challenge/hil/artifact.py#L48)。类型：`FunctionDef`。

```python
verify_onnx_artifact.check(name: str, passed: bool, detail: str, *, fatal: bool=True) -> None
```

`check` 检查runtime合同、artifact、输出一致性、结构或身份完整性；结果只覆盖声明能力，model-only与full-chain、宿主与板端证据不得混写。

## 内部调用与异常路径

- `_shape_of` 调用：`int`.
- `verify_onnx_artifact` 调用：`AdapterError`, `FORBIDDEN_OPS.intersection`, `Path`, `Path(onnx_path).resolve`, `Path(reference_structure).read_text`, `_RepoModules`, `_shape_of`, `all`, `check`, `checks.append`, `contract.input_shapes.items`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `inputs.values`, `int`, `json.loads`, `len`, `list`, `modules.get`, `modules.get('challenge.student.contract.StudentShapeContract')`, `onnx.checker.check_model`, `onnx.load`, `opsets.get`, `path.is_file`, `path.stat`, `reference.get`, `sha256_file`, `sorted`, `str`, `sum`, `type`.
- `check` 调用：`checks.append`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `verify_onnx_artifact`，第 40 行：`AdapterError(f'artifact not found: {path}')`。
- `verify_onnx_artifact`，第 44 行：`AdapterError('onnx is required for artifact verification')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [challenge/hil/identity.py](../../../challenge/hil/identity.py)
- [challenge/hil/runtime_adapter.py](../../../challenge/hil/runtime_adapter.py)

静态 import 消费者（含测试）：

- [challenge/hil/cli.py](../../../challenge/hil/cli.py)
- [challenge/hil/tests/test_artifact.py](../../../challenge/hil/tests/test_artifact.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-hil.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/hil/artifact.py`

来源 SHA256：`224855bcce4aa7e7ae2833c2b18a9edb35d65fc3ee491d31b4824cd8cf4f0731`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `verify_onnx_artifact` / 40 | `not path.is_file()` | `raise AdapterError(f'artifact not found: {path}')` |
| `verify_onnx_artifact` / 44 | `except ImportError` | `raise AdapterError('onnx is required for artifact verification') from error` |
