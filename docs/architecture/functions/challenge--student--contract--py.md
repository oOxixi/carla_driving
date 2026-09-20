# contract：功能记录

上级模块：[模块说明](../modules/challenge-structure.md) · 实现：[challenge/student/contract.py](../../../challenge/student/contract.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [预处理真实变换与信息损失](student-preprocessing.md)

## 功能职责与范围

Frozen Student V0 tensor dimensions and structured vocabularies.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `StudentShapeContract.batch: int`；默认：`1`。
- `StudentShapeContract.rgb_channels: int`；默认：`3`。
- `StudentShapeContract.rgb_height: int`；默认：`224`。
- `StudentShapeContract.rgb_width: int`；默认：`224`。
- `StudentShapeContract.text_length: int`；默认：`32`。
- `StudentShapeContract.max_targets: int`；默认：`8`。
- `StudentShapeContract.target_features: int`；默认：`14`。
- `StudentShapeContract.state_features: int`；默认：`64`。
- `StudentShapeContract.max_steps: int`；默认：`4`。

## 功能入口：输入、输出与实现说明

### `StudentShapeContract`

源码位置：[challenge/student/contract.py 第 40 行](../../../challenge/student/contract.py#L40)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StudentShapeContract.input_shapes`

源码位置：[challenge/student/contract.py 第 52 行](../../../challenge/student/contract.py#L52)。类型：`FunctionDef`。

```python
StudentShapeContract.input_shapes(self) -> dict[str, tuple[int, ...]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StudentShapeContract.output_shapes`

源码位置：[challenge/student/contract.py 第 61 行](../../../challenge/student/contract.py#L61)。类型：`FunctionDef`。

```python
StudentShapeContract.output_shapes(self) -> dict[str, tuple[int, ...]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `output_shapes` 调用：`len`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [challenge/distillation/label_encoder.py](../../../challenge/distillation/label_encoder.py)
- [challenge/distillation/tests/test_a1_integration.py](../../../challenge/distillation/tests/test_a1_integration.py)
- [challenge/export/compute_flops.py](../../../challenge/export/compute_flops.py)
- [challenge/export/export_onnx.py](../../../challenge/export/export_onnx.py)
- [challenge/export/validate_artifacts.py](../../../challenge/export/validate_artifacts.py)
- [challenge/planner/student_adapter.py](../../../challenge/planner/student_adapter.py)
- [challenge/student/__init__.py](../../../challenge/student/__init__.py)
- [challenge/student/model.py](../../../challenge/student/model.py)
- [challenge/student/preprocess.py](../../../challenge/student/preprocess.py)
- [challenge/student/training_contract.py](../../../challenge/student/training_contract.py)
- [challenge/tests/test_a1_student.py](../../../challenge/tests/test_a1_student.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-structure.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/student/contract.py`

来源 SHA256：`d7d1cc57c712ae2ec2e86424dfa093b1c366af8256a8061b58f7d976d2b66d51`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `StudentShapeContract.batch` | `int` | `1` |
| `StudentShapeContract.rgb_channels` | `int` | `3` |
| `StudentShapeContract.rgb_height` | `int` | `224` |
| `StudentShapeContract.rgb_width` | `int` | `224` |
| `StudentShapeContract.text_length` | `int` | `32` |
| `StudentShapeContract.max_targets` | `int` | `8` |
| `StudentShapeContract.target_features` | `int` | `14` |
| `StudentShapeContract.state_features` | `int` | `64` |
| `StudentShapeContract.max_steps` | `int` | `4` |
