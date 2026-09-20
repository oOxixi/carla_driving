# d2_v1_1_smoke_config：功能记录

上级模块：[模块说明](../modules/challenge-training.md) · 实现：[challenge/distillation/d2_v1_1_smoke_config.yaml](../../../challenge/distillation/d2_v1_1_smoke_config.yaml)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [各Head损失、mask与加权](distillation-objective.md)
- [恢复、纯权重候选与晋级身份](checkpoint-and-promotion.md)

## 功能职责与范围

d2_v1_1_smoke_config

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 维护时要核对的内容

原文件为执行权威；此页不复制整份代码或配置，避免两份正文各自漂移。

配置项摘要（按文件顺序，层级以源文件缩进为准）：

- `config_id: a3-b1-d2-v1-1-integration-smoke`
- `seed: 20260918`
- `teacher:`
- `git_sha: MULTI_PINNED_B1_D2_V1_1`
- `model_id: Qwen/Qwen3.5-2B`
- `model_revision: 15852e8c16360a2fea060d615a32b45270f8a8fc`
- `artifact_fingerprint_sha256: 4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa`
- `identity_policy: signed_d2_release_smoke`
- `contract:`
- `max_steps: 4`
- `max_targets: 8`
- `dataset:`
- `version: b1_d2_v1_1_a3_strict_positive_v1`
- `train_path: artifacts/a3_d2_v1_1_positive_view_v1/train.jsonl`
- `val_path: artifacts/a3_d2_v1_1_positive_view_v1/val.jsonl`
- `view_manifest_path: artifacts/a3_d2_v1_1_positive_view_v1/a3_view_manifest.json`
- `release_manifest_path: challenge/dataset/releases/d2_v1_1/release_manifest.json`
- `asset_root: .`
- `require_rgb: true`
- `verify_teacher_identity: true`
- `require_pinned_teacher_provenance: true`
- `model:`
- `model_id: student-v0-r3-fp32`
- `config_id: student-v0-r3-structure-20260911`
- `factory: challenge.distillation.a1_student:build_a1_student`
- `options: {}`
- `input:`
- `factory: challenge.distillation.a1_student:build_a1_input_packer`
- `options: {}`
- `training:`
- `device: auto`
- `epochs: 1`
- `batch_size: 4`
- `learning_rate: 0.0001`
- `weight_decay: 0.0001`
- `gradient_clip_norm: 1.0`
- `max_updates: 2`
- `selection_metric: plan_sequence_accuracy`
- `resume: null`
- `sampling:`
- `weights: {normal: 1.0, complex: 1.5, safety_critical: 2.5}`
- `class_balance:`
- `enabled: false`
- `heads: [behavior]`
- `smoothing: 1.0`
- `max_weight: 5.0`
- `loss_weights:`
- `behavior: 2.0`
- `target_pointer: 1.5`
- `target_lane: 0.5`
- `target_speed: 0.5`
- `completion: 0.5`
- `on_failure: 0.3`
- `confidence: 0.2`
- `replan: 0.2`
- `plan_length: 0.5`
- `requires_confirmation: 0.2`
- `distillation: {soft_alpha: 0.0, temperature: 1.0}`
- `output:`
- `directory: artifacts/challenge/distillation/d2_v1_1_smoke`

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-training.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/distillation/d2_v1_1_smoke_config.yaml`

来源 SHA256：`79459d56f578d5a46dabec28c79f6db7d82e9ca7a0acc7d5e30bc82c94cff0e6`。

非Python/Schema资源：已核对内容指纹与来源存在性；参数生效和业务语义不能由指纹证明，参见所属模块与原资源记录。
