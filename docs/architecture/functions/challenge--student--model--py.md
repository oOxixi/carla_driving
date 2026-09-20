# model：功能记录

上级模块：[模块说明](../modules/challenge-structure.md) · 实现：[challenge/student/model.py](../../../challenge/student/model.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [预处理真实变换与信息损失](student-preprocessing.md)

## 功能职责与范围

Fixed-shape, structured-output Student V0 using J6P-friendly operators.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `StudentModelConfig.config_id: str`；默认：`'student-v0-r3-structure-20260911'`。
- `StudentModelConfig.vision_channels: tuple[int, ...]`；默认：`(3, 32, 64, 128, 256, 384)`。
- `StudentModelConfig.encoder_width: int`；默认：`512`。
- `StudentModelConfig.fusion_widths: tuple[int, ...]`；默认：`(3072, 3072, 1024)`。
- `StudentModelConfig.max_target_speed_mps: float`；默认：`50.0`。
- `StudentModelConfig.initialization: str`；默认：`'kaiming_normal_conv_xavier_uniform_linear_zero_bias'`。

## 功能入口：输入、输出与实现说明

### `StudentModelConfig`

源码位置：[challenge/student/model.py 第 21 行](../../../challenge/student/model.py#L21)。类型：`ClassDef`。

Versioned architectural values used to construct Student V0.

### `StudentModelConfig.as_dict`

源码位置：[challenge/student/model.py 第 31 行](../../../challenge/student/model.py#L31)。类型：`FunctionDef`。

```python
StudentModelConfig.as_dict(self) -> dict[str, object]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `TinyVisionEncoder`

源码位置：[challenge/student/model.py 第 35 行](../../../challenge/student/model.py#L35)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `TinyVisionEncoder.__init__`

源码位置：[challenge/student/model.py 第 36 行](../../../challenge/student/model.py#L36)。类型：`FunctionDef`。

```python
TinyVisionEncoder.__init__(self, output_width: int=512, channels: tuple[int, ...]=(3, 32, 64, 128, 256, 384)) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `TinyVisionEncoder.forward`

源码位置：[challenge/student/model.py 第 56 行](../../../challenge/student/model.py#L56)。类型：`FunctionDef`。

```python
TinyVisionEncoder.forward(self, rgb: Tensor) -> Tensor
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `FixedVectorEncoder`

源码位置：[challenge/student/model.py 第 61 行](../../../challenge/student/model.py#L61)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `FixedVectorEncoder.__init__`

源码位置：[challenge/student/model.py 第 62 行](../../../challenge/student/model.py#L62)。类型：`FunctionDef`。

```python
FixedVectorEncoder.__init__(self, input_width: int, output_width: int=512) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `FixedVectorEncoder.forward`

源码位置：[challenge/student/model.py 第 71 行](../../../challenge/student/model.py#L71)。类型：`FunctionDef`。

```python
FixedVectorEncoder.forward(self, value: Tensor) -> Tensor
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StudentPlannerV0`

源码位置：[challenge/student/model.py 第 75 行](../../../challenge/student/model.py#L75)。类型：`ClassDef`。

23.0M-parameter fixed-shape planner with ten named output heads.

### `StudentPlannerV0.__init__`

源码位置：[challenge/student/model.py 第 80 行](../../../challenge/student/model.py#L80)。类型：`FunctionDef`。

```python
StudentPlannerV0.__init__(self, contract: StudentShapeContract | None=None, config: StudentModelConfig | None=None) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StudentPlannerV0.reset_parameters`

源码位置：[challenge/student/model.py 第 117 行](../../../challenge/student/model.py#L117)。类型：`FunctionDef`。

```python
StudentPlannerV0.reset_parameters(self) -> None
```

Apply the documented, seed-controlled initialization policy.

### `StudentPlannerV0.forward`

源码位置：[challenge/student/model.py 第 129 行](../../../challenge/student/model.py#L129)。类型：`FunctionDef`。

```python
StudentPlannerV0.forward(self, rgb: Tensor, text_tokens: Tensor, targets: Tensor, state: Tensor) -> dict[str, Tensor]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `as_dict` 调用：`asdict`.
- `__init__` 调用：`FixedVectorEncoder`, `StudentModelConfig`, `StudentShapeContract`, `TinyVisionEncoder`, `layers.extend`, `len`, `nn.AvgPool2d`, `nn.Conv2d`, `nn.Linear`, `nn.ReLU`, `nn.Sequential`, `self.reset_parameters`, `super`, `super().__init__`, `zip`.
- `forward` 调用：`len`, `self.activation`, `self.behavior_head`, `self.behavior_head(fused).reshape`, `self.completion_head`, `self.completion_head(fused).reshape`, `self.confidence_head`, `self.confirmation_head`, `self.failure_head`, `self.failure_head(fused).reshape`, `self.features`, `self.fusion`, `self.layers`, `self.plan_length_head`, `self.pool`, `self.pool(self.features(rgb)).flatten`, `self.projection`, `self.replan_head`, `self.state_encoder`, `self.target_encoder`, `self.target_lane_head`, `self.target_lane_head(fused).reshape`, `self.target_pointer_head`, `self.target_pointer_head(fused).reshape`, `self.target_speed_head`, `self.text_encoder`, `self.vision_encoder`, `targets.flatten`, `torch.cat`, `torch.sigmoid`, `torch.sigmoid(self.target_speed_head(fused)).reshape`.
- `reset_parameters` 调用：`isinstance`, `nn.init.kaiming_normal_`, `nn.init.xavier_uniform_`, `nn.init.zeros_`, `self.modules`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [challenge/student/contract.py](../../../challenge/student/contract.py)

静态 import 消费者（含测试）：

- [challenge/export/compute_flops.py](../../../challenge/export/compute_flops.py)
- [challenge/export/export_onnx.py](../../../challenge/export/export_onnx.py)
- [challenge/export/validate_artifacts.py](../../../challenge/export/validate_artifacts.py)
- [challenge/planner/student_backend.py](../../../challenge/planner/student_backend.py)
- [challenge/student/__init__.py](../../../challenge/student/__init__.py)
- [challenge/tests/test_a1_student.py](../../../challenge/tests/test_a1_student.py)
- [challenge/tests/test_delivery.py](../../../challenge/tests/test_delivery.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-structure.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/student/model.py`

来源 SHA256：`070f490099e9a77715e0c1731cd5e825535e6b9230ddb0ac9413e4347b2da86c`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `StudentModelConfig.config_id` | `str` | `'student-v0-r3-structure-20260911'` |
| `StudentModelConfig.vision_channels` | `tuple[int, ...]` | `(3, 32, 64, 128, 256, 384)` |
| `StudentModelConfig.encoder_width` | `int` | `512` |
| `StudentModelConfig.fusion_widths` | `tuple[int, ...]` | `(3072, 3072, 1024)` |
| `StudentModelConfig.max_target_speed_mps` | `float` | `50.0` |
| `StudentModelConfig.initialization` | `str` | `'kaiming_normal_conv_xavier_uniform_linear_zero_bias'` |
