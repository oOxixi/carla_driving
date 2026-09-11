# B1 Teacher Dataset Smoke v0 交接说明

## 1. 当前阶段

本次交付属于：`B1 Teacher 数据与数据治理 - Smoke v0`

当前数据集版本：`teacher_distill_v0.1_smoke`

本次 Smoke 用于验证 Teacher 数据采集、数据格式、RGB/ModelRequest/ManeuverPlan 对齐、target pointer 编码、训练质量策略、Train/Val 分组划分以及交付链路。

**这不是最终 D3 数据集，也不是 Frozen Test。**

后续 B1 仍需继续完成：
- D1 `dataset_sample_200+`
- Seen / Variant / Unseen 数据治理
- D2 3000~5000 有效 Teacher samples
- D3 大规模蒸馏数据
- 独立 Train / Val / Frozen Test
- Calibration 300~500
- `official_like_1000`
- 最终 dataset manifest / quality report

## 2. Teacher 基线

- Teacher Git SHA：`a05c8b76efcd4c176965223c661f40b153cb1836`
- Teacher Model：`Qwen/Qwen3.5-2B`
- Planner mode：`planner_v2`
- Teacher 输出边界：`ModelRequest V1 -> Qwen Teacher -> ManeuverPlan V2`

本次 B1 数据工作没有重新设计基础 A/B/C/D 控制链，也没有绕过 SafetySupervisor。

## 3. Smoke 数据最终统计

- Raw structurally valid Teacher samples：`30`
- Train eligible：`28`
- Quarantined hard cases：`2`
- Train：`22`
- Val：`6`
- SafetySupervisor override samples retained：`7`
- Run-level FAILED but supervision command/plan successful：`2`
- 实际 RGB：`30 / 30`
- Unique RGB SHA256：`30`
- Rejected collection records：`2`
- Group overlap：`0`
- Sample ID overlap：`0`
- TARGET_OUTSIDE_TOPK：`0`

最终 Gate：
- `Leakage Validation = PASS`
- `B1 Smoke Dataset Acceptance = PASS`
- `DELIVERY_PACKAGING = PASS`

## 4. 两条 Hard Cases

以下两条 Teacher supervision 结构合法，因此保留在 raw Teacher 数据中，但因为闭环 plan 最终执行失败，不进入普通 supervised Train/Val。

### ACC_A05_lane_change_left
- command terminal：`FAILED`
- plan terminal：`FAILED`
- reason：`LANE_GAP_UNSAFE`

### SUP_A13_lane_change_right
- command terminal：`FAILED`
- plan terminal：`FAILED`
- reason：`LANE_GAP_UNSAFE`

对应文件：`challenge/dataset/smoke_v0/data/smoke_hard_cases.jsonl`

处理原则：
- 不删除真实 Teacher 数据；
- 不把执行失败 plan 当普通正监督；
- hard cases 单独保留用于后续分析、困难样本训练或专项评测。

## 5. Safety-critical / SafetySupervisor override 样本

共有 `7` 条样本发生 SafetySupervisor override。

如果 Teacher label 合法、supervision command 成功且 plan 成功，则仍允许进入 Train/Val，同时保留 safety override flag、safety override frames 和 closed-loop evidence。

## 6. 14 项交付要求逐条对应

### 1）dataset_schema.md 或数据格式说明
文件：`challenge/dataset/dataset_schema.md`
交付包副本：`challenge/dataset/smoke_v0/dataset_schema.md`
状态：`DONE`

### 2）20~50 条真实 Teacher Smoke Test
实际完成：`30` 条真实 Teacher samples。
每条来自真实 `canonical SUBMIT -> Teacher -> RESOLVE`。
状态：`DONE`

### 3）每条样本完整 ModelRequest V1
30 / 30 样本保留完整 `model_request`，schema version `1.0`。
状态：`DONE`

### 4）Teacher 实际使用的 RGB 图像或路径
30 / 30 保存实际 Teacher RGB。
目录：`challenge/dataset/smoke_v0/rgb/`
映射：`challenge/dataset/smoke_v0/manifests/rgb_manifest.json`
状态：`DONE`

### 5）每条样本完整 ManeuverPlan V2
30 / 30 保存 Teacher 原始 `teacher_plan`。
没有使用 downstream `compiled_plan` 替代 Teacher label。
状态：`DONE`

### 6）每条样本 metadata
包含或可追溯：scenario_id、scenario_family、map、route_hash、seed、frame_id、sim_time、run_id、command_id、request_id、plan_id、teacher_git_sha、teacher_model_id、teacher mode、latency information。
状态：`DONE`

### 7）targets 字段定义、排序和 TopK 截取规则
Raw dataset 保留完整 `ModelRequest.targets`，严格保持原始顺序。
Smoke target-pointer 验证暂时使用 `TopK = 8`。
**TopK=8 只是 Smoke 验证配置，不是最终 Student frozen contract。**
状态：`DONE`

### 8）target_id -> target_pointer 映射和无目标编码规则
- candidate pointer：`0..7`
- `NO_TARGET = 8`
- Teacher target_id 在 retained TopK：映射为 candidate index
- Teacher target 为 null：`NO_TARGET`
- Teacher target 被 TopK 截断：`TARGET_OUTSIDE_TOPK`
- 禁止把 `TARGET_OUTSIDE_TOPK` 静默转为 `NO_TARGET`

Smoke 结果：`TARGET_OUTSIDE_TOPK = 0`
工具：`challenge/dataset/target_pointer.py`
状态：`DONE`

### 9）各数值字段 dtype、单位和缺失值处理
详见 `challenge/dataset/dataset_schema.md`。
核心原则：
- continuous numeric：`float32`
- index/frame/pointer：`int64`
- boolean：`bool / int8`
- categorical：`int64 + UNKNOWN`
- distance：meter
- speed：m/s
- time：second
- latency：ms
- missing numeric 与物理意义上的 0 分离
- Student preprocessing 使用 validity mask
状态：`DONE`

### 10）Train/Val manifest 和 dataset_manifest
数据：
- `challenge/dataset/smoke_v0/data/train.jsonl`
- `challenge/dataset/smoke_v0/data/val.jsonl`

Manifest：
- `challenge/dataset/smoke_v0/manifests/train_manifest.json`
- `challenge/dataset/smoke_v0/manifests/val_manifest.json`
- `challenge/dataset/smoke_v0/manifests/dataset_manifest_v0.json`
- `challenge/dataset/smoke_v0/manifests/split_manifest.json`
- `challenge/dataset/smoke_v0/manifests/delivery_manifest.json`

当前 Train=`22`，Val=`6`。
状态：`DONE`

### 11）按 scenario/map/route/seed 划分、防止相邻帧泄漏
Group definition：`scenario_family + map + route_hash + seed`
禁止相邻帧随机 row split。
当前 split seed=`1`，Train groups=`10`，Val groups=`2`，Group overlap=`0`，Sample ID overlap=`0`。
状态：`DONE`

### 12）普通 / Complex / Safety-critical 样本分类字段
Raw Smoke：
- NORMAL=`17`
- COMPLEX=`6`
- SAFETY_CRITICAL=`7`

最终 train-eligible split：
Train：NORMAL=`14`，COMPLEX=`3`，SAFETY_CRITICAL=`5`
Val：NORMAL=`3`，COMPLEX=`1`，SAFETY_CRITICAL=`2`
状态：`DONE`

### 13）闭环质量字段
已保留：
- run status
- scenario acceptance
- command terminal status
- plan terminal state
- plan reason
- collision
- lane invasion
- route deviation
- red-light violation
- SafetySupervisor override
- safety override frames

`teacher_label_valid` 表示监督本身是否合法。

`closed_loop_success` 当前定义为：
`command_terminal_status == SUCCEEDED` 且 `plan_terminal_state == SUCCEEDED`

Normal supervised Train eligibility：
`teacher_label_valid AND closed_loop_success`

工具：`challenge/dataset/apply_training_policy.py`
状态：`DONE`

### 14）数据集版本号和后续更新规则
当前：`teacher_distill_v0.1_smoke`

规则：
- 已发布数据集不 silent mutate；
- 修复需要新 version / patch；
- Teacher SHA 改变必须记录；
- Teacher model 改变必须记录；
- Frozen Test 一旦冻结不得修改；
- Smoke Train/Val 不是最终 D3 Test；
- official-like 数据不得混入普通蒸馏 Train。

状态：`DONE`

## 7. Smoke v0 文件结构

```text
challenge/dataset/smoke_v0/
├── README.md
├── dataset_schema.md
├── data/
│   ├── smoke_valid.jsonl
│   ├── smoke_with_targets.jsonl
│   ├── smoke_with_policy.jsonl
│   ├── smoke_train_eligible.jsonl
│   ├── smoke_hard_cases.jsonl
│   ├── smoke_rejected.jsonl
│   ├── train.jsonl
│   └── val.jsonl
├── manifests/
│   ├── dataset_manifest_v0.json
│   ├── train_manifest.json
│   ├── val_manifest.json
│   ├── split_manifest.json
│   ├── rgb_manifest.json
│   └── delivery_manifest.json
├── reports/
│   └── dataset_quality_report.md
└── rgb/
    └── 30 actual Teacher RGB images
```

## 8. B1 数据代码

```text
challenge/dataset/
├── collector.py
├── collect_smoke_batch.py
├── target_pointer.py
├── apply_training_policy.py
├── split_dataset.py
├── validate_dataset.py
├── build_manifest.py
├── dataset_quality_report.py
├── package_smoke_delivery.py
├── dataset_schema.md
├── B1_SMOKE_HANDOFF.md
└── smoke_v0/
```

## 9. 当前质量 Gate

```text
RAW_TEACHER_SAMPLES=30
TRAIN_ELIGIBLE_SAMPLES=28
HARD_CASES=2
TRAIN_SAMPLES=22
VAL_SAMPLES=6

RGB_SAMPLE_ENTRIES=30
UNIQUE_RGB_FILES=30
MISSING_RGB_ENTRIES=0

GROUP_LEAKAGE=0
SAMPLE_ID_LEAKAGE=0

TARGET_OUTSIDE_TOPK=0

Leakage Validation=PASS
B1 Smoke Dataset Acceptance=PASS
DELIVERY_PACKAGING=PASS
```

## 10. 当前限制

本 Smoke 数据用于：
- schema 验证
- Teacher collection 验证
- multimodal alignment 验证
- target pointer 验证
- data governance 验证
- Train/Val split 验证

不能把本版本描述成：
- 最终 B1 dataset
- Frozen Test
- 官方 1000-frame dataset
- 最终 Student training corpus

## 11. 下一阶段 B1

### D1
目标：`dataset_sample_200+`

重点：
- 继续真实 Teacher collection
- 不通过重复相同 frame/sample 注水
- 扩展 scenario / route / seed / command 覆盖
- 保持 Teacher provenance
- hard cases 独立治理
- RGB / ModelRequest / ManeuverPlan 严格对齐

### D2
继续扩展：
- Seen
- Variant
- Unseen
- language-equivalent expansion

### D3
进一步建立：
- 大规模 Train
- 独立 Val
- Frozen Test
- Calibration 300~500
- official_like_1000

Frozen Test 不用于调参。

## 12. 给负责人最重要的信息

当前完成的是：

**B1 Teacher 数据管线的真实 Smoke 验证与第一版数据治理交付。**

已经证明：

真实 ModelRequest + 实际 RGB + Qwen Teacher + ManeuverPlan V2 + closed-loop evidence 可以稳定转换为可追溯、可分组、可训练的数据。

下一步不是重新设计数据格式，而是在这套冻结规则上扩大到 D1 200+，随后继续 D2/D3。

## 13. 建议负责人优先查看

1. `challenge/dataset/B1_SMOKE_HANDOFF.md`
2. `challenge/dataset/smoke_v0/README.md`
3. `challenge/dataset/smoke_v0/reports/dataset_quality_report.md`
4. `challenge/dataset/smoke_v0/manifests/delivery_manifest.json`
5. `challenge/dataset/dataset_schema.md`

## 14. Git 分支交付建议

本次成果最终应合并到：`challenge`

不要把服务器原始 `artifacts/` 目录整体提交 GitHub。

GitHub 只提交整理后的 `challenge/dataset/`。

其中 `smoke_v0/` 已包含 JSONL、manifest、quality report、30 张 RGB、schema 和 README。
