# dummy_student：功能记录

上级模块：[模块说明](../modules/challenge-training.md) · 实现：[challenge/distillation/dummy_student.py](../../../challenge/distillation/dummy_student.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [各Head损失、mask与加权](distillation-objective.md)
- [恢复、纯权重候选与晋级身份](checkpoint-and-promotion.md)

## 功能职责与范围

Tiny D1-only Student used to prove the training path before A1 handoff.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `DummyStudent`

源码位置：[challenge/distillation/dummy_student.py 第 19 行](../../../challenge/distillation/dummy_student.py#L19)。类型：`ClassDef`。

A shared MLP with the exact structured output dictionary A3 expects.

### `DummyStudent.__init__`

源码位置：[challenge/distillation/dummy_student.py 第 22 行](../../../challenge/distillation/dummy_student.py#L22)。类型：`FunctionDef`。

```python
DummyStudent.__init__(self, *, feature_dim: int=32, hidden_dim: int=48, max_steps: int=4, max_targets: int=8) -> None
```

`__init__` 固化本对象的训练结构、配置或依赖，并执行源码中的初始一致性检查；后续批次仍必须保持shape、device、dtype和身份一致。

### `DummyStudent.forward`

源码位置：[challenge/distillation/dummy_student.py 第 50 行](../../../challenge/distillation/dummy_student.py#L50)。类型：`FunctionDef`。

```python
DummyStudent.forward(self, model_inputs: Mapping[str, Tensor]) -> dict[str, Tensor]
```

`forward` 执行Student前向并按冻结Head合同返回或校验具名Tensor；训练路径还需检查shape、device、有限值和梯度，不能只看模型调用成功。

### `build_dummy_student`

源码位置：[challenge/distillation/dummy_student.py 第 78 行](../../../challenge/distillation/dummy_student.py#L78)。类型：`FunctionDef`。

```python
build_dummy_student(config: Mapping[str, Any] | None=None) -> DummyStudent
```

`build_dummy_student` 构造模型、输入打包器、mock样本或标签所需对象；mock/integration smoke只验证链路，禁止作为正式训练或晋级精度证据。

## 内部调用与异常路径

- `build_dummy_student` 调用：`', '.join`, `DummyStudent`, `ValueError`, `dict`, `set`, `set(raw).difference`, `sorted`.
- `__init__` 调用：`int`, `len`, `nn.Linear`, `nn.ReLU`, `nn.Sequential`, `super`, `super().__init__`.
- `forward` 调用：`len`, `self.backbone`, `self.behavior`, `self.behavior(hidden).reshape`, `self.completion`, `self.completion(hidden).reshape`, `self.confidence`, `self.confidence(hidden).sigmoid`, `self.confirmation`, `self.failure`, `self.failure(hidden).reshape`, `self.plan_length`, `self.replan`, `self.target_lane`, `self.target_lane(hidden).reshape`, `self.target_pointer`, `self.target_pointer(hidden).reshape`, `self.target_speed`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `build_dummy_student`，第 83 行：`ValueError('unknown DummyStudent option(s): ' + ', '.join(sorted(unknown)))`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [challenge/distillation/label_encoder.py](../../../challenge/distillation/label_encoder.py)

静态 import 消费者（含测试）：

- [challenge/distillation/tests/test_artifacts.py](../../../challenge/distillation/tests/test_artifacts.py)
- [challenge/distillation/tests/test_evaluate_class_metrics.py](../../../challenge/distillation/tests/test_evaluate_class_metrics.py)
- [challenge/distillation/tests/test_losses.py](../../../challenge/distillation/tests/test_losses.py)
- [challenge/distillation/tests/test_student_contract.py](../../../challenge/distillation/tests/test_student_contract.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-training.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/distillation/dummy_student.py`

来源 SHA256：`4c2e7e4589d1a8d8c0f454d37e1e30af89288665f4b6c7fa61e722b211ace07f`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `build_dummy_student` / 83 | `unknown` | `raise ValueError('unknown DummyStudent option(s): ' + ', '.join(sorted(unknown)))` |
