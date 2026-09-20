# validate_artifacts：功能记录

上级模块：[模块说明](../modules/challenge-export.md) · 实现：[challenge/export/validate_artifacts.py](../../../challenge/export/validate_artifacts.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [随机结构导出、来源SHA与报告](onnx-delivery.md)

## 功能职责与范围

Fail closed when A1 code, reports, contracts and ONNX drift apart.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `validate_artifacts`

源码位置：[challenge/export/validate_artifacts.py 第 22 行](../../../challenge/export/validate_artifacts.py#L22)。类型：`FunctionDef`。

```python
validate_artifacts(root: str | Path) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[challenge/export/validate_artifacts.py 第 78 行](../../../challenge/export/validate_artifacts.py#L78)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `validate_artifacts` 调用：`(challenge_path / 'flops_report.json').read_text`, `(challenge_path / 'model_structure.json').read_text`, `FORBIDDEN_ONNX_OPS.intersection`, `InterfaceRegistry`, `Path`, `Path(root).resolve`, `RuntimeError`, `StudentPlannerV0`, `StudentPlannerV0().parameters`, `StudentShapeContract`, `artifact.read_bytes`, `artifact.relative_to`, `assert_frozen_contracts`, `contract.input_shapes.items`, `flops.get`, `hashlib.sha256`, `hashlib.sha256(artifact.read_bytes()).hexdigest`, `json.loads`, `list`, `metadata.get`, `onnx.checker.check_model`, `onnx.load`, `parameter.numel`, `sorted`, `str`, `structure.get`, `sum`.
- `main` 调用：`argparse.ArgumentParser`, `json.dumps`, `parser.add_argument`, `parser.parse_args`, `print`, `validate_artifacts`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `validate_artifacts`，第 32 行：`RuntimeError('ONNX SHA256 does not match model_structure.json')`。
- `validate_artifacts`，第 43 行：`RuntimeError(f'ONNX input contract drift: {input_shapes} != {expected_shapes}')`。
- `validate_artifacts`，第 46 行：`RuntimeError('ONNX structured output order drift')`。
- `validate_artifacts`，第 50 行：`RuntimeError(f'forbidden dynamic/control-flow ONNX operators: {forbidden}')`。
- `validate_artifacts`，第 52 行：`RuntimeError('reported ONNX operator set drift')`。
- `validate_artifacts`，第 55 行：`RuntimeError('ONNX model_id metadata drift')`。
- `validate_artifacts`，第 57 行：`RuntimeError('ONNX source_git_sha metadata drift')`。
- `validate_artifacts`，第 61 行：`RuntimeError('parameter report drift')`。
- `validate_artifacts`，第 64 行：`RuntimeError(f'candidate identity drift: {key}')`。
- `validate_artifacts`，第 66 行：`RuntimeError('reported input shape drift')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 80 行：`parser.add_argument('--root', default='.')`。

## 上下游与关联验证

静态导入的项目内实现：

- [challenge/planner/frozen_contracts.py](../../../challenge/planner/frozen_contracts.py)
- [challenge/student/contract.py](../../../challenge/student/contract.py)
- [challenge/student/model.py](../../../challenge/student/model.py)
- [runtime/interface_registry.py](../../../runtime/interface_registry.py)

静态 import 消费者（含测试）：

- [challenge/tests/test_delivery.py](../../../challenge/tests/test_delivery.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-export.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/export/validate_artifacts.py`

来源 SHA256：`bea0d2ab0b3bae059d41809d17680d0404e4284f609fe6093a384740a5b965a5`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 80 | `'--root'` | `default='.'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `validate_artifacts` / 32 | `artifact_sha256 != structure['artifact_sha256']` | `raise RuntimeError('ONNX SHA256 does not match model_structure.json')` |
| `validate_artifacts` / 43 | `input_shapes != expected_shapes` | `raise RuntimeError(f'ONNX input contract drift: {input_shapes} != {expected_shapes}')` |
| `validate_artifacts` / 46 | `output_names != list(OUTPUT_NAMES)` | `raise RuntimeError('ONNX structured output order drift')` |
| `validate_artifacts` / 50 | `forbidden` | `raise RuntimeError(f'forbidden dynamic/control-flow ONNX operators: {forbidden}')` |
| `validate_artifacts` / 52 | `structure.get('onnx_operators') != operators` | `raise RuntimeError('reported ONNX operator set drift')` |
| `validate_artifacts` / 55 | `metadata.get('model_id') != StudentPlannerV0.model_id` | `raise RuntimeError('ONNX model_id metadata drift')` |
| `validate_artifacts` / 57 | `metadata.get('source_git_sha') != structure.get('source_git_sha')` | `raise RuntimeError('ONNX source_git_sha metadata drift')` |
| `validate_artifacts` / 61 | `structure['parameters'] != parameters or flops['parameters'] != parameters` | `raise RuntimeError('parameter report drift')` |
| `validate_artifacts` / 64 | `structure.get(key) != flops.get(key)` | `raise RuntimeError(f'candidate identity drift: {key}')` |
| `validate_artifacts` / 66 | `structure['input_shapes'] != expected_shapes or flops['input_shapes'] != expected_shapes` | `raise RuntimeError('reported input shape drift')` |
