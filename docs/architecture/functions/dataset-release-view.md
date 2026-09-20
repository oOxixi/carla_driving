# Teacher 原始数据、冻结发布与 A3 训练视图

上级：[数据治理模块](../modules/challenge-data.md)。

## 三层数据不是重复备份

原始采集记录保存实际 Teacher 请求/响应、图像与闭环事实；release 冻结样本、切分与哈希；A3 view 根据训练资格派生 Train/Val。筛除样本应记录排除原因，不修改原始 Teacher 结果来“修好标签”。

## D2 视图的实际逻辑

[build_a3_d2_view.build_view](../../../challenge/dataset/build_a3_d2_view.py) 先调用 validate_release，要求有效且权威文件是 release_manifest.json。只读取 train/val，不读 Test。

每条记录先按顶层 dataset_version 查 COHORTS，校验采集 Teacher SHA 与该 cohort 的 pinned manifest。然后 `_exclusion_reason` 排除 HARD_NEGATIVE、不具备训练资格或闭环 run/command/plan/scenario_acceptance 未全部成功的样本；资格缺失并非默认为合格。

输出包括 train.jsonl、val.jsonl、excluded_sample_ids.jsonl 和 a3_view_manifest.json。manifest 保存源 release 哈希、cohort manifest 哈希、样本数、排除原因及输出文件哈希。

## 同一样本为何有两个版本字段

顶层 dataset_version 保留采集 cohort；metadata.source_dataset_version 保存源身份，metadata.dataset_version 记录派生 VIEW_VERSION。它们承担不同职责，不能通过批量统一字符串来“消除矛盾”。消费者必须明确使用哪一层。

## 接入新一批数据需要做什么

当前 builder 显式绑定 D2 v1.1 与已知 cohort。新增 D3 release 之后，不能只把 --release-dir 指向 D3 并假设兼容。需要检查治理策略、cohort 身份、目录定位（代码使用 release_dir.parents[3] 推断 repo）、split 规则、A3 preflight 和训练配置，并为新视图赋版本。

验证：[dataset tests](../../../challenge/dataset/tests)、[validate_d2_release](../../../challenge/dataset/validate_d2_release.py)、[A3 audit](../../../challenge/distillation/audit_d2_view.py)、[输入核验](../../../challenge/distillation/validate_a1_inputs.py)。发布完整性检查只证明记录匹配清单；不等于每条 Teacher 语义标签正确。

运行来源见[场景来源](scenario-lineage.md)及[Wave2核查](wave2-audit.md)。组合group split不自动等于family holdout，重分组不能消除历史训练暴露。
