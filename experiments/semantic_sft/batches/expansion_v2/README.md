# 200/50之前的待审扩充批次

用户选择先达到200条Train、50条Val后再训练。旧候选为26/15；本批提出180/36，
全部审核且分组不需调整时合计206/51。当前新增批准数是0，不能把计划数量当已审核数量。

本批216条是AI模板构造文本，不是Teacher推理、CARLA闭环或真实用户语料。
六类各36条、48个模板槽位；每个Train槽位5个词面/参数变体，每个Val槽位3个变体。
2个歧义槽位沿用旧group_id与集合，其余46个是拟定组，并未自动证明独立。
转弯、变道、否定、条件、目标、速度、距离和HOLD均需审核；长动作链的自然性也需检查。

## 复核入口

本机和独立服务器工作区的相同相对目录：

`artifacts/semantic_sft/expansion_v2_20261101_review03/`

- `review_index.md`：48组概览，列出每条原句并链接完整表。
- `draft_review_sheet.md`：216条候选标签，逐步参数、证据、条件与禁止事项。
- `draft_review_queue.jsonl`：原句和proposal，label/reviews仍为空，split未分配。
- `planned_groups.json`：仅为拟定分组，不是已冻结发布。
- `report.json`：来源快照及交付文件SHA256，ready_for_training=false。

先按组核对全部变体，再核对旧41条及保护集合的语义近重复。
若需要合组或改标签，先修正并重新绑定审核；不能仅换ID来维持206/51。
负责人实际确认后才登记审批；没有代签或自动继承旧批批准。
旧split-preview的“每类只选一个Val组”是小样本预览规则，不适用于整批重排。

## 可复现生成

```bash
python -m experiments.semantic_sft.batches.expansion_v2.build \
  --existing-split artifacts/semantic_sft/approved_cumulative_20261101/split_preview.jsonl \
  --test-registry artifacts/semantic_sft/frozen_test_v1_20261101/exclusion_registry.json \
  --supplemental-registry artifacts/semantic_sft/known_holdout_exclusions_20261101/exclusion_registry.json \
  --output-dir artifacts/semantic_sft/expansion_v2_<新目录>
```

生成器校验已审核来源、规范化完全重复、保护文本/组、旧组集合，并拒绝覆盖既有输出。
这些静态检查不证明语义独立、自然性或标签正确，更不是训练/模型效果Gate。
完整复核、split冻结和业务数据token/mask审计之后，才实现并验证业务训练入口。
