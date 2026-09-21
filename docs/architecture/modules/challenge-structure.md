# Student 结构与输入张量

## 开发维护先读：实际语义

以下功能页说明实现理由、分支、接口含义、改动联动与验证。先读这些内容，再按逐文件索引定位方法；不要用函数名推断业务语义。

- [预处理真实变换与信息损失](../functions/student-preprocessing.md)

上级：[挑战赛道](../modules/challenge.md)。

## 功能与实现

[contract.py](../../../challenge/student/contract.py) 定义类别、输入输出顺序和 StudentShapeContract；[model.py](../../../challenge/student/model.py) 定义 StudentModelConfig、CNN/MLP 融合及十个输出 Head；[preprocess.py](../../../challenge/student/preprocess.py) 完成 RGB、文本、目标和状态打包；[training_contract.py](../../../challenge/student/training_contract.py) 定义训练侧契约。

固定导出输入均为 float32：rgb [1,3,224,224]、text_tokens [1,32]、targets [1,8,14]、state [1,64]。训练可用批量 B。最多 4 步、8 个目标，无目标 pointer 为 8；候选顺序保持 ModelRequest.targets 顺序。行为 14 类、车道 6 类、完成条件 8 类、失败动作 4 类、重规划条件 7 类。Python 输出具名 dict；ONNX 按 OUTPUT_NAMES 转为稳定位置顺序。

十个 Head：plan_length_logits、behavior_logits、target_pointer_logits、target_lane_logits、target_speed_mps、completion_type_logits、on_failure_logits、confidence、requires_confirmation_logits、replan_condition_logits。准确 shape、枚举顺序以 contract.py 属性为准，避免在文档复制多套版本。

## 边界与异常

上游为经过 Schema 验证的 ModelRequest V1；下游为 A3 loss、Planner Adapter、ONNX 和 HIL。训练标签必须匹配设备、维度和浮点输出，拒绝 NaN/Inf。运行预处理中的截断、缺失 RGB 行为必须与训练打包一致；不得重新排序 targets 后沿用旧 pointer。

## 验证及修改联动

测试：[A1 结构测试](../../../challenge/tests/test_a1_student.py)、[A3 集成测试](../../../challenge/distillation/tests/test_a1_integration.py)、[输出契约测试](../../../challenge/distillation/tests/test_student_contract.py)、[输入验证](../../../challenge/distillation/tests/test_validate_a1_inputs.py)。

改变任何维度/枚举时同步检查 label_encoder、losses、student_adapter、导出顺序、ONNX Runtime、HIL 和交付结构报告；变更 model_id/config_id 并重新训练/导出，不能继续使用旧权重。

## 第10模块逐入口精读结论（2026-09-22）

### 固定结构与输出语义

- 默认四路输入是 float32 batch1；模型从 RGB 首维取得 batch，并假定其他三路一致。分类/完成/失败/重规划/确认均为 logits，只有 `target_speed_mps` 和 `confidence` 已经 sigmoid。
- 视觉骨干的五次 stride-2 卷积和固定 2×2 pool 针对 224×224 形成 3×3 投影输入；修改分辨率不是单改 contract 字段即可兼容。
- `max_target_speed_mps=50` 只是 Head 数值上界，Planner adapter 还会按 request speed limit/max target speed 收紧；它不是车辆控制许可速度。
- 枚举顺序、目标候选顺序和 `OUTPUT_NAMES` 都属于权重语义。shape 相同但顺序变化仍必须更换 config/model/weights 身份并重训。

### 预处理信息与损失边界

| 输入 | 实际编码 | 截断/缺失 |
|---|---|---|
| RGB | letterbox 后 ImageNet 归一化 | 无路径/不存在返回全零；解码错误抛出 |
| source_text | 每字符 code point 比例 | 32字符右截断、补零；不是 tokenizer |
| targets | 原顺序前8个、14维手工特征 | 非list/非Mapping补零；第9个起丢弃 |
| state | 摘要/约束/能力/hint/routing 写入固定槽位 | 当前槽63未用；部分值只限上界 |

训练计划长度必须为 `[B]` 整数且1..4；step mask 才是 padding 的权威，PAD 类别值不得参与 loss。`masked_step_mean` 会把 mask 扩展到额外特征维，并对所有有效元素取均值。

### 当前边界与联动

- M10-01：contract 允许 `batch!=1`，但预处理除 RGB 外三路固定 batch1；见 [AUDIT](../AUDIT.md)。正式导出合同仍是 batch1，训练批处理应由 Dataset/collate 逐样本堆叠，而不是把该 runtime preprocessor 的 contract.batch 改大。
- 预处理无独立 finite/shape 清洗；在线 `StudentBackend` 先做 ModelRequest Schema 校验，离线 Dataset 也必须通过同等 manifest/label gate。
- 改任何槽位需同步 B1 数据发布、A3 label/loss、Student adapter、ONNX 输出顺序、A2量化、A4 runtime 与B3 HIL，且重新签发权重/配置 manifest。



## 模块接口与参数核对（2026-09-20）

StudentPreprocessor将ModelRequest和RGB打包为rgb/text_tokens/targets/state，StudentPlannerV0产生十个head。模块接口同时被训练、Planner、导出与HIL消费；Python具名输出到ONNX位置输出必须按OUTPUT_NAMES。

### 参数语义与生效边界

固定导出batch1、float32：RGB[1,3,224,224]、文本[1,32]、目标[1,8,14]、状态[1,64]。最多4步、8目标，NONE pointer为8。模型max_target_speed_mps=50是结构输出范围，不等于车辆获准速度。

### 上下游与修改影响

修改维度/类别/槽位顺序必须联动label encoder、loss、adapter、ONNX与runtime并更新配置/权重身份；不允许shape相同就沿用旧语义权重。

### [challenge/student/contract.py](../../../challenge/student/contract.py) 的入口与声明

```python
StudentShapeContract.input_shapes(self) -> dict[str, tuple[int, ...]]
StudentShapeContract.output_shapes(self) -> dict[str, tuple[int, ...]]
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
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

### [challenge/student/model.py](../../../challenge/student/model.py) 的入口与声明

```python
StudentModelConfig.as_dict(self) -> dict[str, object]
TinyVisionEncoder.__init__(self, output_width: int=512, channels: tuple[int, ...]=(3, 32, 64, 128, 256, 384)) -> None
TinyVisionEncoder.forward(self, rgb: Tensor) -> Tensor
FixedVectorEncoder.__init__(self, input_width: int, output_width: int=512) -> None
FixedVectorEncoder.forward(self, value: Tensor) -> Tensor
StudentPlannerV0.__init__(self, contract: StudentShapeContract | None=None, config: StudentModelConfig | None=None) -> None
StudentPlannerV0.reset_parameters(self) -> None
StudentPlannerV0.forward(self, rgb: Tensor, text_tokens: Tensor, targets: Tensor, state: Tensor) -> dict[str, Tensor]
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `StudentModelConfig.config_id` | `str` | `'student-v0-r3-structure-20260911'` |
| `StudentModelConfig.vision_channels` | `tuple[int, ...]` | `(3, 32, 64, 128, 256, 384)` |
| `StudentModelConfig.encoder_width` | `int` | `512` |
| `StudentModelConfig.fusion_widths` | `tuple[int, ...]` | `(3072, 3072, 1024)` |
| `StudentModelConfig.max_target_speed_mps` | `float` | `50.0` |
| `StudentModelConfig.initialization` | `str` | `'kaiming_normal_conv_xavier_uniform_linear_zero_bias'` |

### [challenge/student/training_contract.py](../../../challenge/student/training_contract.py) 的入口与声明

```python
plan_length_to_class(plan_length: Tensor, *, max_steps: int=4) -> Tensor
build_step_mask(plan_length: Tensor, *, max_steps: int=4) -> Tensor
padded_target_pointer_index(contract: StudentShapeContract | None=None) -> int
masked_step_mean(loss: Tensor, step_mask: Tensor) -> Tensor
```

以上为核心交接入口；模块内其余实现、CLI和资源的完整字段/拒绝条件见本页功能小文档索引。类型未声明的返回值不凭名称推断。当前代码基线fe1ba839，静态复核不证明实际CARLA/GPU/板端运行成功。

## 功能小文档完整索引

以下功能页分别记录实现入口、输入输出声明、内部调用、异常、配置和静态上下游；测试文件保留在源码索引中。

- [challenge/__init__.py](../functions/challenge--__init__--py.md)
- [challenge/flops_report.json](../functions/challenge--flops_report--json.md)
- [challenge/model_structure.json](../functions/challenge--model_structure--json.md)
- [challenge/requirements.txt](../functions/challenge--requirements--txt.md)
- [challenge/student/__init__.py](../functions/challenge--student--__init__--py.md)
- [challenge/student/contract.py](../functions/challenge--student--contract--py.md)
- [challenge/student/model.py](../functions/challenge--student--model--py.md)
- [challenge/student/preprocess.py](../functions/challenge--student--preprocess--py.md)
- [challenge/student/training_contract.py](../functions/challenge--student--training_contract--py.md)
- [challenge/student_config.json](../functions/challenge--student_config--json.md)

## 诊断与维护交接

本模块证据：contract、目标排序、截断、dtype/shape；shape一致不足以验收。功能实现与上下游见本页原索引；跨模块回查[追踪矩阵](../TRACEABILITY.md)与[诊断入口](../DIAGNOSIS.md)。实际run必须核对版本，未执行的检查不视为已通过。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/tests/test_a1_student.py`

来源 SHA256：`2434894d9b1293e5e626090b07bc5a998256443b903f387adef6e53471774b5a`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `test_teacher_wrapper_rejects_invalid_request_before_delegate.Delegate.infer` / 286 | `本地无直接if；检查上下文` | `raise AssertionError('delegate must not be called')` |
| `test_teacher_health_cannot_promote_non_production_delegate.TestOnlyDelegate.infer` / 303 | `本地无直接if；检查上下文` | `raise NotImplementedError` |
### `challenge/tests/test_delivery.py`

来源 SHA256：`998b956555b071971c701e40e85cfbd604dadf5f5b974168d687fd4685e8bcbc`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
