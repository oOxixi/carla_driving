# A3 训练、评测与候选晋级

## 开发维护先读：实际语义

以下功能页说明实现理由、分支、接口含义、改动联动与验证。先读这些内容，再按逐文件索引定位方法；不要用函数名推断业务语义。

- [各Head损失、mask与加权](../functions/distillation-objective.md)
- [恢复、纯权重候选与晋级身份](../functions/checkpoint-and-promotion.md)

上级：[挑战赛道](../modules/challenge.md)。

## 功能分组

代码目录：[distillation](../../../challenge/distillation)。

| 功能 | 实现 |
|---|---|
| 数据读取、RGB 解析、collate、真实及 mock 输入打包 | dataset.py、a1_student.py、dummy_student.py |
| 标签编码、固定 Head/设备/有限值校验 | label_encoder.py、student_contract.py、validate_a1_inputs.py |
| 数据及发布预检、D2 视图审查 | preflight.py、audit_d2_view.py |
| loss、类别平衡、指标分母与分组评估 | losses.py、class_balance.py、metrics.py、evaluate.py |
| 训练循环、配置/Teacher 身份校验、随机种子、恢复 | train.py、checkpoint.py |
| hard case、消融、shortcut 检查 | hard_cases.py、ablation_eval.py、shortcut_probe.py |
| 报告、纯权重候选及 Gate 晋级 | run_report.py、artifacts.py、promote.py |

## 端到端契约

B1 train/val → preflight → DistillationDataset → label_encoder → A1 模型 → loss/evaluate → checkpoint 与纯 state_dict 候选 → 独立 Validation 证据 → promote。

标签共享 student/contract.py 类别，padding 的 step_mask 排除无效步，target_speed_mask 排除缺失速度；plan_length 为实际步数减 1。超过 4 步/8 目标、计划 request_id/command_id 不匹配、目标不在请求内会抛 LabelEncodingError。输出必须是具名浮点张量，shape/device 匹配且有限；梯度也检查有限性。

训练 checkpoint 与部署纯 state_dict 不同，不能直接把 checkpoint 传 StudentBackend。candidate 包含 git_sha、Teacher 身份、model_id/config_id、weights_sha256、dataset_version、checkpoint 和发布/视图 hash。Smoke 为 MOCK_ONLY；正式候选为 PENDING_A3_FP32_GATE。

Gate 默认核心指标最大下降 0.015，安全 recall 最大下降 0，schema_validity 必须 1；仅接受 Validation，拒绝冻结 Test；需要干净来源工作树、固定 Teacher revision/fingerprint、当前候选文件 SHA 一致。通过后为 A3_FP32_GATE_PASSED，仍须 B2/B3 独立验收。

## 已确认缺口

[artifacts.py](../../../challenge/distillation/artifacts.py):130-149 仅验证评测的 dataset_version、evaluation_id 和 Teacher 身份，未验证 Student 评测的 weights_sha256、model_id/config_id，也未绑定相同 Validation 样本清单 hash。因此另一个 Student 的指标可能晋级当前权重；应增加证据到候选和数据切分的身份校验。该结论来自静态代码审查，本页不声称运行过攻击样例。

## 测试及联动

[tests](../../../challenge/distillation/tests) 覆盖标签、loss、输出、checkpoint、preflight、A1/B1 接口、D2 Gate、指标、artifacts、报告与 smoke。训练配置、预处理、标签/Head、数据视图版本必须共同变更；修改 Gate 时联动生产加载器、评测证据格式和测试。当前 evaluate 输出训练指标，不能自动等同于最终 Adapter/PlanValidator 的闭环结果。



## 模块接口与参数核对（2026-09-20）

run_training消费配置mapping，先preflight/dataset/label，再模型与loss、验证和checkpoint，最后形成候选。checkpoint含恢复状态，不能直接交给只收state_dict的StudentBackend。

### 参数语义与生效边界

run_training的smoke=False、integration_smoke=False、output_dir_override/resume_override=None为函数默认。实际epochs/batch/lr等由选中配置提供：通用train_config为1轮/batch2/max_updates1，D2 formal为3轮/batch8/max_updates0；训练循环仅在max_updates为真且global_step到达上限时提前结束，因此0表示不启用此更新数上限，仍受epochs控制；smoke又会收紧配置。

### 上下游与修改影响

mask区分padding/缺速度，plan_length标签为真实步数减1；评估层次需区分head与最终Plan。晋级绑定候选权重、数据和Teacher，当前Student评估身份缺口见AUDIT A01，不能因manifest字段齐全就宣称绑定完整。

### [challenge/distillation/train.py](../../../challenge/distillation/train.py) 的入口与声明

```python
run_training(config: Mapping[str, Any], *, smoke: bool=False, output_dir_override: str | Path | None=None, resume_override: str | Path | None=None, integration_smoke: bool=False) -> dict[str, Any]
main() -> int
```

### [challenge/distillation/label_encoder.py](../../../challenge/distillation/label_encoder.py) 的入口与声明

```python
DistillationLabelEncoder.vocabulary(self) -> dict[str, tuple[str, ...]]
DistillationLabelEncoder.encode(self, request: Mapping[str, Any], plan: Mapping[str, Any]) -> dict[str, Any]
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `DistillationLabelEncoder.max_steps` | `int` | `4` |
| `DistillationLabelEncoder.max_targets` | `int` | `8` |
| `DistillationLabelEncoder.validate_contracts` | `bool` | `True` |

### [challenge/distillation/losses.py](../../../challenge/distillation/losses.py) 的入口与声明

```python
LossWeights.from_mapping(cls, value: Mapping[str, Any] | None) -> 'LossWeights'
MultiHeadDistillationLoss.__init__(self, weights: LossWeights | None=None, *, soft_alpha: float=0.0, temperature: float=1.0, class_weights: Mapping[str, Any] | None=None) -> None
MultiHeadDistillationLoss.forward(self, outputs: Mapping[str, Tensor], labels: Mapping[str, Tensor]) -> tuple[Tensor, dict[str, Tensor]]
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `LossWeights.behavior` | `float` | `2.0` |
| `LossWeights.target_pointer` | `float` | `1.5` |
| `LossWeights.target_lane` | `float` | `0.5` |
| `LossWeights.target_speed` | `float` | `0.5` |
| `LossWeights.completion` | `float` | `0.5` |
| `LossWeights.on_failure` | `float` | `0.3` |
| `LossWeights.confidence` | `float` | `0.2` |
| `LossWeights.replan` | `float` | `0.2` |
| `LossWeights.plan_length` | `float` | `0.5` |
| `LossWeights.requires_confirmation` | `float` | `0.2` |

### [challenge/distillation/artifacts.py](../../../challenge/distillation/artifacts.py) 的入口与声明

```python
export_candidate_weights(output_directory: str | Path, *, model: torch.nn.Module, identity: Mapping[str, Any], validation: Mapping[str, Any], checkpoint_sha256: str) -> dict[str, Any]
promote_fp32_candidate(candidate_manifest: Mapping[str, Any], *, weights_path: str | Path, teacher_evaluation: Mapping[str, Any], student_evaluation: Mapping[str, Any], output_path: str | Path, max_core_drop: float=0.015, max_safety_drop: float=0.0, core_metrics: Sequence[str]=CORE_METRICS, safety_metrics: Sequence[str]=SAFETY_METRICS) -> dict[str, Any]
```

以上为核心交接入口；模块内其余实现、CLI和资源的完整字段/拒绝条件见本页功能小文档索引。类型未声明的返回值不凭名称推断。当前代码基线fe1ba839，静态复核不证明实际CARLA/GPU/板端运行成功。

## 功能小文档完整索引

以下功能页分别记录实现入口、输入输出声明、内部调用、异常、配置和静态上下游；测试文件保留在源码索引中。

- [challenge/distillation/__init__.py](../functions/challenge--distillation--__init__--py.md)
- [challenge/distillation/a1_student.py](../functions/challenge--distillation--a1_student--py.md)
- [challenge/distillation/ablation_eval.py](../functions/challenge--distillation--ablation_eval--py.md)
- [challenge/distillation/artifacts.py](../functions/challenge--distillation--artifacts--py.md)
- [challenge/distillation/audit_d2_view.py](../functions/challenge--distillation--audit_d2_view--py.md)
- [challenge/distillation/b1_smoke_config.yaml](../functions/challenge--distillation--b1_smoke_config--yaml.md)
- [challenge/distillation/checkpoint.py](../functions/challenge--distillation--checkpoint--py.md)
- [challenge/distillation/class_balance.py](../functions/challenge--distillation--class_balance--py.md)
- [challenge/distillation/d2_v1_1_formal_config.yaml](../functions/challenge--distillation--d2_v1_1_formal_config--yaml.md)
- [challenge/distillation/d2_v1_1_smoke_config.yaml](../functions/challenge--distillation--d2_v1_1_smoke_config--yaml.md)
- [challenge/distillation/dataset.py](../functions/challenge--distillation--dataset--py.md)
- [challenge/distillation/dummy_student.py](../functions/challenge--distillation--dummy_student--py.md)
- [challenge/distillation/evaluate.py](../functions/challenge--distillation--evaluate--py.md)
- [challenge/distillation/hard_cases.py](../functions/challenge--distillation--hard_cases--py.md)
- [challenge/distillation/label_encoder.py](../functions/challenge--distillation--label_encoder--py.md)
- [challenge/distillation/losses.py](../functions/challenge--distillation--losses--py.md)
- [challenge/distillation/metrics.py](../functions/challenge--distillation--metrics--py.md)
- [challenge/distillation/preflight.py](../functions/challenge--distillation--preflight--py.md)
- [challenge/distillation/promote.py](../functions/challenge--distillation--promote--py.md)
- [challenge/distillation/run_report.py](../functions/challenge--distillation--run_report--py.md)
- [challenge/distillation/shortcut_probe.py](../functions/challenge--distillation--shortcut_probe--py.md)
- [challenge/distillation/student_contract.py](../functions/challenge--distillation--student_contract--py.md)
- [challenge/distillation/train.py](../functions/challenge--distillation--train--py.md)
- [challenge/distillation/train_config.yaml](../functions/challenge--distillation--train_config--yaml.md)
- [challenge/distillation/validate_a1_inputs.py](../functions/challenge--distillation--validate_a1_inputs--py.md)

## 诊断与维护交接

本模块证据：dataset/checkpoint/RNG、权重SHA与评估身份；缺口见AUDIT A01。功能实现与上下游见本页原索引；跨模块回查[追踪矩阵](../TRACEABILITY.md)与[诊断入口](../DIAGNOSIS.md)。实际run必须核对版本，未执行的检查不视为已通过。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/distillation/tests/__init__.py`

来源 SHA256：`e4f75175efcc8bc7348977770675048a0942616b8f30723e08eb01a69b7a0d0e`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `challenge/distillation/tests/test_a1_integration.py`

来源 SHA256：`c74746ceb529a332296b8f42f12cfc8125627bfb15b116d88eb3cdd1db3e40c8`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `challenge/distillation/tests/test_ablation_eval.py`

来源 SHA256：`1fd0b45dd8149d8bbf2d2c9d7684f47474aedc43fa7cf66021079ab29effdcac`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `challenge/distillation/tests/test_artifacts.py`

来源 SHA256：`740b727d86f72eadeb02bed1792f5e319dca1c5b571f90e7b36e14b64495d804`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `challenge/distillation/tests/test_audit_d2_view.py`

来源 SHA256：`adf6eca599ca8a97e401c55b8959f753a9a1ee22ef3fa7b0b5c6bcad3c5e81fb`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `challenge/distillation/tests/test_b1_d1_interface.py`

来源 SHA256：`ac01f42b1eb11823fa0c34b5db9a5a1f0ccb554605ef481f542790f41a52d83c`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `challenge/distillation/tests/test_b1_smoke_integration.py`

来源 SHA256：`d4e6be85b0af6aac840db6fcda950cdefe1c6a64f2f9726698c05573c2afae11`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `challenge/distillation/tests/test_checkpoint.py`

来源 SHA256：`3250f7c259883a635cd9807966b63af324b3ef74f74d5d54a4d648d7a802150c`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `challenge/distillation/tests/test_d2_v1_1_smoke_gate.py`

来源 SHA256：`1e376efaef84c99362362b246a1967736758ad23a643b088aa23e8bad7f3c9c4`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `challenge/distillation/tests/test_evaluate_class_metrics.py`

来源 SHA256：`8cf36958ae349e81b886359e1711d4f4439d8614955d9af5774eea7497d122f3`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `challenge/distillation/tests/test_label_encoder.py`

来源 SHA256：`49c672f1a378d6b60bd5c68b20faaf39460d1776b46a7f0430ef0464a707b642`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `challenge/distillation/tests/test_losses.py`

来源 SHA256：`63e035593980bca22b174dca1c95ad4d118cf2c6a90beda6529c18b42759bbb9`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `challenge/distillation/tests/test_preflight.py`

来源 SHA256：`a5ad6ace4bfcc19d073bdbcf27989434f1092e4c5a8eac54b5870d88dd9f4d9c`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `challenge/distillation/tests/test_run_report.py`

来源 SHA256：`044a1a222f7251890764bf5d0101494af115198a79c2f831327fe74c38b0beef`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `challenge/distillation/tests/test_shortcut_probe.py`

来源 SHA256：`e0d6a6237eaa8fe21ecb0fff6fcc4058d750b5e5e382d45672b50831a08c2006`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `challenge/distillation/tests/test_student_contract.py`

来源 SHA256：`a8860bdfafa61dd3a87d8840d0193b434b0a8ffe983506b50bd7ae9300df5548`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `challenge/distillation/tests/test_train_smoke.py`

来源 SHA256：`85dcb1fbf9456d8df9506c92edc2d6df57b67738bcf6f9519adb6c9960ff906f`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `challenge/distillation/tests/test_validate_a1_inputs.py`

来源 SHA256：`42cde0a307aa9abe107c44e91f5431c367c492a6ad6d57683cfab9845e9853ed`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。

### [challenge/distillation/train_config.yaml](../../../challenge/distillation/train_config.yaml) 配置值快照

这些是此文件的值；只有实际入口选择并装载此文件后才参与生效，不覆盖上文的显式override规则。

| 参数路径 | 文件值 |
|---|---|
| `config_id` | `"a3-distillation-v1-a1-r3"` |
| `seed` | `20260910` |
| `teacher.git_sha` | `"a05c8b76efcd4c176965223c661f40b153cb1836"` |
| `teacher.model_id` | `"Qwen/Qwen3.5-2B"` |
| `teacher.model_revision` | `"15852e8c16360a2fea060d615a32b45270f8a8fc"` |
| `teacher.artifact_fingerprint_sha256` | `"4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa"` |
| `teacher.identity_policy` | `"frozen_manifest"` |
| `contract.max_steps` | `4` |
| `contract.max_targets` | `8` |
| `dataset.version` | `"PENDING_B1"` |
| `dataset.train_path` | `null` |
| `dataset.val_path` | `null` |
| `dataset.verify_teacher_identity` | `true` |
| `dataset.require_pinned_teacher_provenance` | `true` |
| `dataset.mock_samples` | `8` |
| `dataset.mock_train_fraction` | `0.75` |
| `model.model_id` | `"student-v0-r3-fp32"` |
| `model.config_id` | `"student-v0-r3-structure-20260911"` |
| `model.factory` | `"challenge.distillation.a1_student:build_a1_student"` |
| `model.options` | `{}` |
| `input.factory` | `"challenge.distillation.a1_student:build_a1_input_packer"` |
| `input.options` | `{}` |
| `training.device` | `"auto"` |
| `training.epochs` | `1` |
| `training.batch_size` | `2` |
| `training.learning_rate` | `0.0001` |
| `training.weight_decay` | `0.0001` |
| `training.gradient_clip_norm` | `1.0` |
| `training.max_updates` | `1` |
| `training.selection_metric` | `"plan_sequence_accuracy"` |
| `training.resume` | `null` |
| `sampling.weights.normal` | `1.0` |
| `sampling.weights.complex` | `1.5` |
| `sampling.weights.safety_critical` | `2.5` |
| `class_balance.enabled` | `false` |
| `class_balance.heads` | `["behavior"]` |
| `class_balance.smoothing` | `1.0` |
| `class_balance.max_weight` | `5.0` |
| `loss_weights.behavior` | `2.0` |
| `loss_weights.target_pointer` | `1.5` |
| `loss_weights.target_lane` | `0.5` |
| `loss_weights.target_speed` | `0.5` |
| `loss_weights.completion` | `0.5` |
| `loss_weights.on_failure` | `0.3` |
| `loss_weights.confidence` | `0.2` |
| `loss_weights.replan` | `0.2` |
| `loss_weights.plan_length` | `0.5` |
| `loss_weights.requires_confirmation` | `0.2` |
| `distillation.soft_alpha` | `0.0` |
| `distillation.temperature` | `1.0` |
| `output.directory` | `"artifacts/challenge/distillation/a1_r3_smoke"` |

### [challenge/distillation/d2_v1_1_formal_config.yaml](../../../challenge/distillation/d2_v1_1_formal_config.yaml) 配置值快照

这些是此文件的值；只有实际入口选择并装载此文件后才参与生效，不覆盖上文的显式override规则。

| 参数路径 | 文件值 |
|---|---|
| `config_id` | `"a3-b1-d2-v1-1-fp32-baseline-v1"` |
| `seed` | `20260918` |
| `teacher.git_sha` | `"MULTI_PINNED_B1_D2_V1_1"` |
| `teacher.model_id` | `"Qwen/Qwen3.5-2B"` |
| `teacher.model_revision` | `"15852e8c16360a2fea060d615a32b45270f8a8fc"` |
| `teacher.artifact_fingerprint_sha256` | `"4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa"` |
| `teacher.identity_policy` | `"signed_d2_release_formal"` |
| `contract.max_steps` | `4` |
| `contract.max_targets` | `8` |
| `dataset.version` | `"b1_d2_v1_1_a3_strict_positive_v1"` |
| `dataset.train_path` | `"artifacts/a3_d2_v1_1_positive_view_v1/train.jsonl"` |
| `dataset.val_path` | `"artifacts/a3_d2_v1_1_positive_view_v1/val.jsonl"` |
| `dataset.view_manifest_path` | `"artifacts/a3_d2_v1_1_positive_view_v1/a3_view_manifest.json"` |
| `dataset.release_manifest_path` | `"challenge/dataset/releases/d2_v1_1/release_manifest.json"` |
| `dataset.asset_root` | `"."` |
| `dataset.require_rgb` | `true` |
| `dataset.verify_teacher_identity` | `true` |
| `dataset.require_pinned_teacher_provenance` | `true` |
| `model.model_id` | `"student-v0-r3-fp32"` |
| `model.config_id` | `"student-v0-r3-structure-20260911"` |
| `model.factory` | `"challenge.distillation.a1_student:build_a1_student"` |
| `model.options` | `{}` |
| `input.factory` | `"challenge.distillation.a1_student:build_a1_input_packer"` |
| `input.options` | `{}` |
| `training.device` | `"auto"` |
| `training.epochs` | `3` |
| `training.batch_size` | `8` |
| `training.learning_rate` | `0.0001` |
| `training.weight_decay` | `0.0001` |
| `training.gradient_clip_norm` | `1.0` |
| `training.max_updates` | `0` |
| `training.selection_metric` | `"plan_sequence_accuracy"` |
| `training.resume` | `null` |
| `sampling.weights.normal` | `1.0` |
| `sampling.weights.complex` | `1.5` |
| `sampling.weights.safety_critical` | `2.5` |
| `class_balance.enabled` | `false` |
| `class_balance.heads` | `["behavior"]` |
| `class_balance.smoothing` | `1.0` |
| `class_balance.max_weight` | `5.0` |
| `loss_weights.behavior` | `2.0` |
| `loss_weights.target_pointer` | `1.5` |
| `loss_weights.target_lane` | `0.5` |
| `loss_weights.target_speed` | `0.5` |
| `loss_weights.completion` | `0.5` |
| `loss_weights.on_failure` | `0.3` |
| `loss_weights.confidence` | `0.2` |
| `loss_weights.replan` | `0.2` |
| `loss_weights.plan_length` | `0.5` |
| `loss_weights.requires_confirmation` | `0.2` |
| `distillation.soft_alpha` | `0.0` |
| `distillation.temperature` | `1.0` |
| `output.directory` | `"artifacts/challenge/distillation/d2_v1_1_fp32_baseline_v1"` |
