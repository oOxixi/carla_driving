# B1 数据采集、治理与发布

## 开发维护先读：实际语义

以下功能页说明实现理由、分支、接口含义、改动联动与验证。先读这些内容，再按逐文件索引定位方法；不要用函数名推断业务语义。

- [原始样本、冻结发布与派生训练视图](../functions/dataset-release-view.md)

上级：[挑战赛道](../modules/challenge.md)。

## 功能分组和入口

代码目录：[dataset](../../../challenge/dataset)。

| 功能 | 源码入口 |
|---|---|
| 日志配对、RGB、Teacher 时序、闭环结果、目标落地和样本分类 | collector.py |
| 基础构建、切分、manifest、质量检查 | build_dataset.py、split_dataset.py、build_manifest.py、validate_dataset.py、dataset_quality_report.py |
| Teacher 文件身份、pointer 编码 | teacher_model_fingerprint.py、target_pointer.py |
| Smoke 采集及交付 | collect_smoke_batch.py、collect_pinned_mini_smoke.py、package_smoke_delivery.py |
| D1 场景注册、采集、扩展计划及完成交付 | build_d1_scenario_registry.py、collect_d1_200.py、build_d1_extension_plan.py、collect_d1_extension.py、finalize_d1_extension.py、build_d1_delivery.py |
| D2 第一批扩展、训练池与切分 | build_d2_expansion_plan.py、collect_d2_expansion.py、build_d2_training_pool.py、build_d2_split_v1.py、materialize_d2_student_split.py |
| D2 第二批计划、采集和冻结 | build_d2_wave2_plan.py、collect_d2_wave2.py、build_d2_wave2_freeze.py |
| 语义/训练资格/累计治理 | apply_training_policy.py、build_semantic_governance_v4.py、build_training_eligibility_v4.py、build_d2_cumulative_governance_v5.py |
| D3 增量 | build_d3_wave1_plan.py、collect_d3_wave1.py |
| 发布完整性与 A3 严格正样本视图 | validate_d2_release.py、build_a3_d2_view.py |

各批次脚本记录历史生产阶段，不是可任意替换的同义入口。原始日志、samples、release、training view 有不同职责，不应覆盖原始记录来修训练语义。

## 权威数据与接口

[dataset_schema.md](../../../challenge/dataset/dataset_schema.md) 描述样本；执行验证由 collector、validate_dataset、validate_d2_release 和 A3 preflight 分层完成。核心数据为 sample_id、model_request、teacher_plan、metadata、quality、closed_loop_quality、视觉资产引用和 student_targets。指针对应当前 targets 顺序；空目标用 top_k，默认 8；越出 top-k 必须隔离或拒绝。

发布身份由 release_manifest.json 及文件 hash 确定；A3 派生视图另有 a3_view_manifest.json，记录源发布 hash、cohort manifest hash、排除 ID 与输出文件 hash。Teacher baseline、pinned 和 pinned_v4 清单分别对应历史 cohort，不能用最新文件覆盖所有历史身份。

build_a3_d2_view.py:18-31 固定 D2 v1.1 视图和三个支持 cohort；82-96 隔离 HARD_NEGATIVE、无训练资格以及闭环终态非全部成功的样本；99-158 先验签再生成 train/val 视图。元数据保留 source_dataset_version，metadata.dataset_version 变为视图版本，而顶层 dataset_version 仍保留源 cohort；消费者必须明确字段优先级。这是设计上的双身份，不应直接判定为脏数据。

## 异常与验证

发布校验失败、未知 cohort、Teacher 身份冲突、缺失正样本资格直接拒绝生成。严格正样本过滤产生 exclusion 清单。冻结 Test 不可进入训练和阈值调整。

测试目录：[dataset/tests](../../../challenge/dataset/tests)，覆盖 collector 治理、D2/D3 计划与采集、D2 发布、A3 view；交叉验证见 A3 preflight 和 audit_d2_view 测试。

修改采集字段时联动 Schema、训练资格策略、release 校验、A3 dataset/preflight 和历史样本迁移说明。D3 累计接入 A3 的能力不能由 D2 固定视图自动推断；应新增版本化视图与测试。



## 模块接口与参数核对（2026-09-20）

collector从run_start/submit/resolve/run_complete及maneuver事件构造sample，以command身份对齐request与Teacher Plan；结构有效、闭环成功、训练资格是不同判断。collect_file返回样本与拒绝记录两类列表。

### 参数语义与生效边界

build_sample的repo_root/log_path/run记录/scenario_data/dataset_version为显式调用参数；缺run_complete不能按成功补齐。release_manifest保存冻结文件身份，view保存来源hash和排除记录；D2 view固定cohort不能直接视作通用D3入口。

### 上下游与修改影响

更换Teacher/采集字段要联动provenance、quality、release validator、A3 preflight/labels；Train/Val/Reserved和HN隔离，重新划分不能消除训练暴露。原始run文件不因过滤而改写。

### [challenge/dataset/collector.py](../../../challenge/dataset/collector.py) 的入口与声明

```python
canonical_json(value: Any) -> str
sha256_bytes(data: bytes) -> str
sha256_file(path: Path) -> str
stable_route_hash(route: Any) -> str | None
read_jsonl(path: Path) -> list[dict[str, Any]]
load_scenario(repo_root: Path, config_path: str | None) -> dict[str, Any] | None
index_rows(rows: list[dict[str, Any]]) -> dict[str, Any]
extract_model_request(row: dict[str, Any]) -> dict[str, Any] | None
extract_teacher_plan(row: dict[str, Any]) -> dict[str, Any] | None
extract_model_timing(row: dict[str, Any]) -> dict[str, Any] | None
get_disposition(row: dict[str, Any]) -> str | None
find_rgb(repo_root: Path, rgb_ref: Any) -> tuple[Path | None, bool]
classify_sample(model_request: dict[str, Any], teacher_plan: dict[str, Any], closed_loop: dict[str, Any]) -> dict[str, Any]
classify_training_role(structurally_valid: bool, closed_loop: dict[str, Any]) -> tuple[str, list[str]]
extract_closed_loop(run_complete: dict[str, Any] | None, command_id: str, maneuver_events: list[dict[str, Any]]) -> dict[str, Any]
validate_pair(model_request: dict[str, Any] | None, teacher_plan: dict[str, Any] | None, rgb_exists: bool, resolve_disposition: str | None) -> tuple[bool, list[str]]
target_grounding(model_request: dict[str, Any], teacher_plan: dict[str, Any]) -> dict[str, Any]
build_sample(*, repo_root: Path, log_path: Path, run_start: dict[str, Any] | None, run_complete: dict[str, Any] | None, submit: dict[str, Any], resolve: dict[str, Any], maneuver_events: list[dict[str, Any]], scenario_data: dict[str, Any] | None, dataset_version: str) -> dict[str, Any]
build_run_level_rejection(*, log_path: Path, dataset_version: str, run_start: dict[str, Any] | None, failure: dict[str, Any] | None, reason: str) -> dict[str, Any]
collect_file(*, repo_root: Path, log_path: Path, dataset_version: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]
write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None
main() -> None
```

### [challenge/dataset/build_a3_d2_view.py](../../../challenge/dataset/build_a3_d2_view.py) 的入口与声明

```python
build_view(release_dir: Path, output_dir: Path) -> dict[str, Any]
main() -> int
```

### [challenge/dataset/validate_d2_release.py](../../../challenge/dataset/validate_d2_release.py) 的入口与声明

```python
canonical_text_sha256(path: Path) -> str
validate_release(release_dir: Path, *, check_images: bool=True) -> dict[str, Any]
main() -> int
```

以上为核心交接入口；模块内其余实现、CLI和资源的完整字段/拒绝条件见本页功能小文档索引。类型未声明的返回值不凭名称推断。当前代码基线fe1ba839，静态复核不证明实际CARLA/GPU/板端运行成功。

## 功能小文档完整索引

以下功能页分别记录实现入口、输入输出声明、内部调用、异常、配置和静态上下游；测试文件保留在源码索引中。

- [challenge/dataset/apply_training_policy.py](../functions/challenge--dataset--apply_training_policy--py.md)
- [challenge/dataset/build_a3_d2_view.py](../functions/challenge--dataset--build_a3_d2_view--py.md)
- [challenge/dataset/build_d1_delivery.py](../functions/challenge--dataset--build_d1_delivery--py.md)
- [challenge/dataset/build_d1_extension_plan.py](../functions/challenge--dataset--build_d1_extension_plan--py.md)
- [challenge/dataset/build_d1_scenario_registry.py](../functions/challenge--dataset--build_d1_scenario_registry--py.md)
- [challenge/dataset/build_d2_cumulative_governance_v5.py](../functions/challenge--dataset--build_d2_cumulative_governance_v5--py.md)
- [challenge/dataset/build_d2_expansion_plan.py](../functions/challenge--dataset--build_d2_expansion_plan--py.md)
- [challenge/dataset/build_d2_split_v1.py](../functions/challenge--dataset--build_d2_split_v1--py.md)
- [challenge/dataset/build_d2_training_pool.py](../functions/challenge--dataset--build_d2_training_pool--py.md)
- [challenge/dataset/build_d2_wave2_freeze.py](../functions/challenge--dataset--build_d2_wave2_freeze--py.md)
- [challenge/dataset/build_d2_wave2_plan.py](../functions/challenge--dataset--build_d2_wave2_plan--py.md)
- [challenge/dataset/build_d3_wave1_plan.py](../functions/challenge--dataset--build_d3_wave1_plan--py.md)
- [challenge/dataset/build_dataset.py](../functions/challenge--dataset--build_dataset--py.md)
- [challenge/dataset/build_manifest.py](../functions/challenge--dataset--build_manifest--py.md)
- [challenge/dataset/build_semantic_governance_v4.py](../functions/challenge--dataset--build_semantic_governance_v4--py.md)
- [challenge/dataset/build_training_eligibility_v4.py](../functions/challenge--dataset--build_training_eligibility_v4--py.md)
- [challenge/dataset/collect_d1_200.py](../functions/challenge--dataset--collect_d1_200--py.md)
- [challenge/dataset/collect_d1_extension.py](../functions/challenge--dataset--collect_d1_extension--py.md)
- [challenge/dataset/collect_d2_expansion.py](../functions/challenge--dataset--collect_d2_expansion--py.md)
- [challenge/dataset/collect_d2_wave2.py](../functions/challenge--dataset--collect_d2_wave2--py.md)
- [challenge/dataset/collect_d3_wave1.py](../functions/challenge--dataset--collect_d3_wave1--py.md)
- [challenge/dataset/collect_pinned_mini_smoke.py](../functions/challenge--dataset--collect_pinned_mini_smoke--py.md)
- [challenge/dataset/collect_smoke_batch.py](../functions/challenge--dataset--collect_smoke_batch--py.md)
- [challenge/dataset/collector.py](../functions/challenge--dataset--collector--py.md)
- [challenge/dataset/dataset_quality_report.py](../functions/challenge--dataset--dataset_quality_report--py.md)
- [challenge/dataset/finalize_d1_extension.py](../functions/challenge--dataset--finalize_d1_extension--py.md)
- [challenge/dataset/materialize_d2_student_split.py](../functions/challenge--dataset--materialize_d2_student_split--py.md)
- [challenge/dataset/package_smoke_delivery.py](../functions/challenge--dataset--package_smoke_delivery--py.md)
- [challenge/dataset/split_dataset.py](../functions/challenge--dataset--split_dataset--py.md)
- [challenge/dataset/target_pointer.py](../functions/challenge--dataset--target_pointer--py.md)
- [challenge/dataset/teacher_model_fingerprint.py](../functions/challenge--dataset--teacher_model_fingerprint--py.md)
- [challenge/dataset/validate_d2_release.py](../functions/challenge--dataset--validate_d2_release--py.md)
- [challenge/dataset/validate_dataset.py](../functions/challenge--dataset--validate_dataset--py.md)
- [challenge/teacher_baseline_manifest.json](../functions/challenge--teacher_baseline_manifest--json.md)
- [challenge/teacher_pinned_manifest.json](../functions/challenge--teacher_pinned_manifest--json.md)
- [challenge/teacher_pinned_manifest_v4.json](../functions/challenge--teacher_pinned_manifest_v4--json.md)

## 诊断与维护交接

本模块证据：run/sample/cohort、split/hash、excluded原因；Wave2原始证据缺失。功能实现与上下游见本页原索引；跨模块回查[追踪矩阵](../TRACEABILITY.md)与[诊断入口](../DIAGNOSIS.md)。实际run必须核对版本，未执行的检查不视为已通过。

专项记录：[场景来源与泛化漂移](../functions/scenario-lineage.md)、[B1 D3 Wave2核查记录](../functions/wave2-audit.md)。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/dataset/tests/test_build_a3_d2_view.py`

来源 SHA256：`89f225ca0eb1f48fe9d4d39287800e71f17701e949d71f8954440fe1b9b98bda`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `challenge/dataset/tests/test_collector_governance.py`

来源 SHA256：`87d72009912e943304a6ab9d4407983410d94a213474362cbe8ca6e4f1de05c8`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `challenge/dataset/tests/test_d2_expansion_plan.py`

来源 SHA256：`204f54f55f0ba9a8ed86eba02ce1e9d9aae7646f123f6cc4b17df4b64ddaec40`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `challenge/dataset/tests/test_d2_wave2_collector.py`

来源 SHA256：`71729b7a20e0d10adbd2ba1a1a5131afbdcf23592fd7d8c525760adfd8adc7c7`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `challenge/dataset/tests/test_d2_wave2_plan.py`

来源 SHA256：`5e957d1a3442a287a0538a240cae14ff9dcc08babfd12358671834e726d7a2d7`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `challenge/dataset/tests/test_d3_wave1_collector.py`

来源 SHA256：`82e940672cd5946955590479795d4536fdfaad8af6c6505a1868198b481f951f`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `challenge/dataset/tests/test_d3_wave1_plan.py`

来源 SHA256：`65f1e8102a675b75725c0edf01068ca270531418d5291104882f1a5b5d883ed6`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `challenge/dataset/tests/test_validate_d2_release.py`

来源 SHA256：`73ca710dee49f98079a28dbe0f6a416330e2fbd19a9e9f8001eb9c605e587847`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
