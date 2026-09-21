# teacher_baseline_manifest：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/teacher_baseline_manifest.json](../../../challenge/teacher_baseline_manifest.json)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

teacher_baseline_manifest

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 维护时要核对的内容

原文件为执行权威；此页不复制整份代码或配置，避免两份正文各自漂移。

- `schema_version`：'1.0'。
- `baseline_id`：'teacher-baseline-v1'。
- `verification_status`：'PINNED_ARTIFACT_VERIFIED_B2_BENCHMARK_PENDING'。
- `source_remote`：'https://github.com/oOxixi/carla_driving.git'。
- `source_branch`：'main'。
- `git_sha`：'a05c8b76efcd4c176965223c661f40b153cb1836'。
- `model_profile`：'qwen3.5-2b'。
- `model_id`：'Qwen/Qwen3.5-2B'。
- `model_revision`：'15852e8c16360a2fea060d615a32b45270f8a8fc'。
- `artifact_fingerprint_sha256`：'4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa'。
- `artifact_source`：'public Hugging Face repository pinned by exact revision'。
- `runtime_validation`：对象，直接字段：independent_download, model_fingerprint, vllm_inference, planner_v2_adapter_health。
- `input_contract`：对象，直接字段：name, schema_version, canonical_json_sha256。
- `output_contract`：对象，直接字段：name, schema_version, canonical_json_sha256。
- `contract_fingerprint_method`：'SHA256(canonical JSON: UTF-8, sorted keys, compact separators)'。
- `scope`：'formal B1 Teacher identity and contracts are pinned; old unpinned Smoke is historical only; benchmark evidence remains B2-owned'。

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

### `challenge/teacher_baseline_manifest.json`

来源 SHA256：`937c32a0f67b708430e6080cb667b4227e0626b16a832a1dfa4b2188b999cc26`。

非Python/Schema资源：已核对内容指纹与来源存在性；参数生效和业务语义不能由指纹证明，参见所属模块与原资源记录。
