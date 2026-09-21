# flops_report：功能记录

上级模块：[模块说明](../modules/challenge-structure.md) · 实现：[challenge/flops_report.json](../../../challenge/flops_report.json)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [预处理真实变换与信息损失](student-preprocessing.md)

## 功能职责与范围

flops_report

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 维护时要核对的内容

原文件为执行权威；此页不复制整份代码或配置，避免两份正文各自漂移。

- `schema_version`：'1.0'。
- `model_id`：'student-v0-r3-fp32'。
- `source_git_sha`：'f8e567ef8cd3cce592b920947dee9c6a2f3a9cf0'。
- `dataset_version`：'NOT_APPLICABLE_RANDOM_INIT'。
- `config_id`：'student-v0-r3-structure-20260911'。
- `precision`：'fp32'。
- `input_shapes`：对象，直接字段：rgb, text_tokens, targets, state。
- `parameters`：23006581。
- `trainable_parameters`：23006581。
- `parameter_size_bytes_fp32`：92026324。
- `macs_per_fixed_batch`：249320448。
- `flops_per_fixed_batch`：498640896。
- `teacher_model_id`：'Qwen/Qwen3.5-2B'。
- `teacher_model_revision`：'15852e8c16360a2fea060d615a32b45270f8a8fc'。
- `teacher_artifact_fingerprint_sha256`：'4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa'。
- `teacher_non_embedding_active_parameters_lower_bound`：1409286144。
- `teacher_flops_lower_bound_one_text_token`：2818572288。
- `flops_ratio_student_over_teacher_lower_bound`：0.17691258021763392。
- `ratio_target`：0.5。
- `ratio_pass`：True。
- `counting_convention`：'Conv2D/Linear only; 1 MAC = 2 FLOPs'。
- `teacher_bound_scope`：'2B-class conservative one-token bound; Teacher identity is pinned but this is not an exact-model FLOPs calculation; excludes vision and sequence work; not latency or board evidence'。
- `macs_by_module`：对象，直接字段：vision_encoder.features.0, vision_encoder.features.2, vision_encoder.features.4, vision_encoder.features.6, vision_encoder.features.8, vision_encoder.projection, text_encoder.layers.0, text_encoder.layers.2, target_encoder.layers.0, target_encoder.layers.2, state_encoder.layers.0, state_encoder.layers.2, fusion.0, fusion.2, fusion.4, plan_length_head, behavior_head, target_pointer_head, target_lane_head, target_speed_head, completion_head, failure_head, confidence_head, confirmation_head, replan_head。

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

### `challenge/flops_report.json`

来源 SHA256：`2f323e307aeb4426dbb15d7ec63935222f3c62b04df8b21fbfd00cdf2f24a9c0`。

非Python/Schema资源：已核对内容指纹与来源存在性；参数生效和业务语义不能由指纹证明，参见所属模块与原资源记录。
