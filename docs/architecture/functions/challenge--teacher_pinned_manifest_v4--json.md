# teacher_pinned_manifest_v4：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/teacher_pinned_manifest_v4.json](../../../challenge/teacher_pinned_manifest_v4.json)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

teacher_pinned_manifest_v4

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 维护时要核对的内容

原文件为执行权威；此页不复制整份代码或配置，避免两份正文各自漂移。

- `schema_version`：'1.0'。
- `teacher_profile`：'b1-pinned-teacher-v4'。
- `teacher_git_sha`：'95e97b00def8ec36f12937da34ce8bb9082c4a04'。
- `model_id`：'Qwen/Qwen3.5-2B'。
- `model_revision`：'15852e8c16360a2fea060d615a32b45270f8a8fc'。
- `model_artifact_sha256`：'4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa'。
- `quantization`：None。
- `dtype`：'bfloat16'。
- `max_model_len`：2048。
- `qwen_mode`：'planner_v2'。
- `serving`：对象，直接字段：vllm_version, torch_version, flashinfer_sampler, max_num_seqs, gpu_memory_utilization, image_max_side。
- `verification`：对象，直接字段：service_health, main_regression, challenge_regression, challenge_main_test_suite_parity, directional_semantic_gate, directional_closed_loop_gate, service_gate, cold_start_observation。
- `legacy_smoke_note`：'Previous B1 Smoke used a shared local Qwen/Qwen3.5-2B service whose exact Hugging Face revision was not recorded. This pinned revision must not be retroactively attributed to the legacy Smoke dataset.'。
- `teacher_tag`：'teacher-baseline-v4'。
- `previous_teacher_git_sha`：'1a363c15b9b1790534358c11acbd100a3011fa93'。

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-data.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/teacher_pinned_manifest_v4.json`

来源 SHA256：`852e4f4a7118d7638a2646e04dd1a6f5c25276973f897de2380a90fbd7521654`。

非Python/Schema资源：已核对内容指纹与来源存在性；参数生效和业务语义不能由指纹证明，参见所属模块与原资源记录。
