# export_onnx：功能记录

上级模块：[模块说明](../modules/challenge-export.md) · 实现：[challenge/export/export_onnx.py](../../../challenge/export/export_onnx.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [随机结构导出、来源SHA与报告](onnx-delivery.md)

## 功能职责与范围

Export Student V0 with fixed shapes and no dynamic axes.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_source_git_sha`

源码位置：[challenge/export/export_onnx.py 第 19 行](../../../challenge/export/export_onnx.py#L19)。类型：`FunctionDef`。

```python
_source_git_sha() -> str
```

`_source_git_sha` 解析源码或产物身份，用于把导出文件绑定到固定提交和权重；UNKNOWN或脏工作树不能作为正式发布身份。

### `StudentOnnxExportWrapper`

源码位置：[challenge/export/export_onnx.py 第 25 行](../../../challenge/export/export_onnx.py#L25)。类型：`ClassDef`。

Convert the public named dict to ONNX's stable positional output list.

### `StudentOnnxExportWrapper.__init__`

源码位置：[challenge/export/export_onnx.py 第 28 行](../../../challenge/export/export_onnx.py#L28)。类型：`FunctionDef`。

```python
StudentOnnxExportWrapper.__init__(self, model: StudentPlannerV0) -> None
```

`__init__` 保存导出包装器或FLOPs统计所需结构，并注册算子hook；统计/包装不改变原模型权重，但结果依赖实际输入shape和受支持算子。

### `StudentOnnxExportWrapper.forward`

源码位置：[challenge/export/export_onnx.py 第 32 行](../../../challenge/export/export_onnx.py#L32)。类型：`FunctionDef`。

```python
StudentOnnxExportWrapper.forward(self, *inputs: torch.Tensor) -> tuple[torch.Tensor, ...]
```

`forward` 在导出或统计时按冻结输入/输出顺序执行一次前向或记录算子量；返回位置顺序必须与OUTPUT_NAMES一致，不能用Python dict偶然顺序替代合同。

### `export_student_v0`

源码位置：[challenge/export/export_onnx.py 第 37 行](../../../challenge/export/export_onnx.py#L37)。类型：`FunctionDef`。

```python
export_student_v0(output: str | Path, *, seed: int=20260911, source_git_sha: str | None=None) -> Path
```

`export_student_v0` 执行模型分析、ONNX导出、产物校验或X86推理；必须记录结构、权重、opset、动态轴、元数据与数值对齐，结构smoke不能冒充真实候选部署。

### `main`

源码位置：[challenge/export/export_onnx.py 第 117 行](../../../challenge/export/export_onnx.py#L117)。类型：`FunctionDef`。

```python
main() -> int
```

解析导出、校验或X86运行参数，执行对应结构/产物流程并以退出码报告门禁；命令成功不代表训练权重、量化或J6P部署已经验收。

## 内部调用与异常路径

- `_source_git_sha` 调用：`subprocess.check_output`, `subprocess.check_output(('git', 'rev-parse', 'HEAD'), text=True, encoding='utf-8').strip`.
- `export_student_v0` 调用：`(path.parent / filename).write_text`, `Path`, `RuntimeError`, `StudentModelConfig`, `StudentOnnxExportWrapper`, `StudentOnnxExportWrapper(model).eval`, `StudentPlannerV0`, `StudentPlannerV0(contract, config).eval`, `StudentShapeContract`, `_source_git_sha`, `analyze_model`, `contract.input_shapes.values`, `contract.output_shapes.items`, `hashlib.sha256`, `hashlib.sha256(path.read_bytes()).hexdigest`, `json.dumps`, `list`, `model.named_children`, `onnx.checker.check_model`, `onnx.helper.set_model_props`, `onnx.load`, `onnx.save`, `path.parent.mkdir`, `path.read_bytes`, `sorted`, `str`, `structure.update`, `torch.manual_seed`, `torch.onnx.export`, `torch.zeros`, `tuple`, `zip`.
- `main` 调用：`argparse.ArgumentParser`, `export_student_v0`, `parser.add_argument`, `parser.parse_args`, `print`.
- `__init__` 调用：`super`, `super().__init__`.
- `forward` 调用：`self.model`, `tuple`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `export_student_v0`，第 64 行：`RuntimeError('onnx is required to verify the exported model')`。
- `export_student_v0`，第 82 行：`RuntimeError(f'dynamic or wrong ONNX shape for {value.name}: {actual} != {expected}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 119 行：`parser.add_argument('--output', default='challenge/student_v0_fp32.onnx')`。
- 第 120 行：`parser.add_argument('--source-git-sha')`。

## 上下游与关联验证

静态导入的项目内实现：

- [challenge/export/compute_flops.py](../../../challenge/export/compute_flops.py)
- [challenge/planner/frozen_contracts.py](../../../challenge/planner/frozen_contracts.py)
- [challenge/student/contract.py](../../../challenge/student/contract.py)
- [challenge/student/model.py](../../../challenge/student/model.py)

静态 import 消费者（含测试）：

- [challenge/tests/test_a1_student.py](../../../challenge/tests/test_a1_student.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-export.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/export/export_onnx.py`

来源 SHA256：`eb3166317245254b002c2dc51111105a13e2679372567991f4fd5540e6d0324d`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 119 | `'--output'` | `default='challenge/student_v0_fp32.onnx'` |
| 120 | `'--source-git-sha'` | `` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `export_student_v0` / 64 | `except ImportError` | `raise RuntimeError('onnx is required to verify the exported model') from error` |
| `export_student_v0` / 82 | `actual != expected` | `raise RuntimeError(f'dynamic or wrong ONNX shape for {value.name}: {actual} != {expected}')` |
