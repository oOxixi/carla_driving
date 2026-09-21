# model_structure：功能记录

上级模块：[模块说明](../modules/challenge-structure.md) · 实现：[challenge/model_structure.json](../../../challenge/model_structure.json)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [预处理真实变换与信息损失](student-preprocessing.md)

## 功能职责与范围

model_structure

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 维护时要核对的内容

原文件为执行权威；此页不复制整份代码或配置，避免两份正文各自漂移。

- `schema_version`：'1.0'。
- `model_id`：'student-v0-r3-fp32'。
- `source_git_sha`：'f8e567ef8cd3cce592b920947dee9c6a2f3a9cf0'。
- `dataset_version`：'NOT_APPLICABLE_RANDOM_INIT'。
- `config_id`：'student-v0-r3-structure-20260911'。
- `parameters`：23006581。
- `precision`：'fp32'。
- `input_shapes`：对象，直接字段：rgb, text_tokens, targets, state。
- `status`：'A1_STRUCTURE_READY_A3_WEIGHTS_PENDING'。
- `artifact`：'student_v0_fp32.onnx'。
- `artifact_sha256`：'ffb1ed5e9b23aa7100343bb4f02c8cfef3da5049e9c5eba4c0e66247c96ee243'。
- `opset`：17。
- `dynamic_axes`：False。
- `onnx_operators`：列表，共 11 项。
- `modules`：对象，直接字段：vision_encoder, text_encoder, target_encoder, state_encoder, fusion, plan_length_head, behavior_head, target_pointer_head, target_lane_head, target_speed_head, completion_head, failure_head, confidence_head, confirmation_head, replan_head。
- `output_names`：列表，共 10 项。
- `output_shapes`：对象，直接字段：plan_length_logits, behavior_logits, target_pointer_logits, target_lane_logits, target_speed_mps, completion_type_logits, on_failure_logits, confidence, requires_confirmation_logits, replan_condition_logits。
- `input_dtype`：'float32'。
- `output_dtype`：'float32'。
- `forbidden_outputs`：列表，共 4 项。
- `training_state`：'random_initialization_for_export_smoke_only'。

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-structure.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/model_structure.json`

来源 SHA256：`971c6e70b42ac338190bb1779875bb2da89e9d23d8a480963a3a35a266f493fb`。

非Python/Schema资源：已核对内容指纹与来源存在性；参数生效和业务语义不能由指纹证明，参见所属模块与原资源记录。
