# negative_v1：禁止类补充待审批次

本批新增8条AI编写原句/候选标签，拟定4个语义组，每组2条改写。不是B1 Teacher数据、
不是实测Qwen输出或正式Train/Val。用户于2026-10-30明确回复“批准新增8条”，已单独记录首轮批准，
仍不是完成双人复核的金标。旧24条材料与已记录的21条首轮批准不变，源候选文件也保留原稿。

| 样本编号后缀 | 禁止事项 | 肯定任务顺序 | 拟定同组改写标识 |
| --- | --- | --- | --- |
| 001/002 | TURN_RIGHT | KEEP_LANE → 停车标线前STOP | neg_right_turn_keep_stop_v1 |
| 003/004 | TURN_LEFT | SET_SPEED(23) → 指示牌通过后STOP | neg_left_turn_speed_stop_v1 |
| 005/006 | FOLLOW | YIELD行人 → 停止线前STOP | neg_follow_yield_stop_v1 |
| 007/008 | PULL_OVER | SET_SPEED(31) → KEEP_LANE | neg_pull_over_speed_keep_v1 |

不是只给旧句换数值/左右方向：候选组在禁止动作、任务组合、条件和目标关联上不同。
但分组仍须人工检查跨批近重复，不能因group_id不同就宣称已经独立；正式Test排除清单尚未提供。

## 复核重点

- 禁止转弯不能扩大成禁止同方向变道，也不是要求朝另一方向转弯。
- 出租车是背景，不是要求让行的行人，不能错绑目标；原句使用全局的“禁止跟车”，不伪装成现有格式尚不能精确表示的actor级禁止项。
- 禁止靠边停车不等于禁止普通停车或紧急制动；本批不改变安全层。
- 位置/通过条件应绑定后续停车；速度值只来自原句，不由规则补齐。
- 同组两条不能跨Train/Val。本批8条已经单独获得首轮批准，不是从旧批准自动继承；仍需另一位真实复核人。
- 即使8条都审核完成，也只是缓解禁止类覆盖缺口，远不足以宣称达到200/50工程样本门槛或训练有效。

复用既有准备命令，不新增批次框架：

```bash
python -m experiments.semantic_sft.prepare draft \
  --input experiments/semantic_sft/batches/negative_v1/seeds.jsonl \
  --proposals experiments/semantic_sft/batches/negative_v1/draft_labels.jsonl \
  --output-dir artifacts/semantic_sft/negative_v1_<新批次>
```

输出`draft_review_sheet.md`供人阅读，`draft_review_queue.jsonl`中的label仍为null、reviews仍为空。
这是生成初始草稿的行为，不会抹去已有审批。已批准的本批快照另存
`artifacts/semantic_sft/negative_v1_first_review_20261030/review_queue.jsonl`，对应report保存真实批准原句及哈希。
累计旧批和新批的快照位于`artifacts/semantic_sft/cumulative_first_review_20261030/`：29条首轮批准、3条隔离。
本批不修改原动作契约，也不放行旧013/014/023；那些问题仍需独立设计。
