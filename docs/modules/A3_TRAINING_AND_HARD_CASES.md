# A3 训练、评测、断点恢复与 Hard-case 闭环

## 1. 模块目标

A3 负责把 B1 发布的、可审计的 Teacher 监督数据转换为可复现的 Student FP32
训练结果，并把 Validation 误差沉淀为下一轮数据改进线索。A3 不负责设计 A1
Student 结构、不采集 B1 Teacher 数据、不读取 B2 Frozen Test，也不执行 A2
量化或 A4 板端部署。

本模块依赖：

- [`B1_TO_A3_DATA_PIPELINE.md`](B1_TO_A3_DATA_PIPELINE.md)：数据身份、划分与发布门禁。
- [`MODEL_AND_WEIGHT_LIFECYCLE.md`](MODEL_AND_WEIGHT_LIFECYCLE.md)：Teacher、Student、FP32、INT8 与运行时权重的身份链。
- [`challenge/distillation/HANDOFF.md`](../../challenge/distillation/HANDOFF.md)：A1/B1/B2/B3 与 A3 的字段级交接合同。

## 2. 四种运行等级

| 等级 | 输入 | 目的 | 可以证明什么 | 不能证明什么 |
|---|---|---|---|---|
| Mock smoke | 合成样本 + Dummy Student | 检查 Dataset → Loss → Backward → Checkpoint | 训练链路可执行 | 真实数据正确、模型精度 |
| Real integration smoke | 已签名 release 的小切片，最多 Train/Val 各 50 条、最多 2 次更新 | 检查真实 schema、RGB、packer 和 A1 Student 接口 | 数据与模型能接通 | 收敛、泛化、正式指标 |
| Formal training | 完整签名 Train/Val、固定配置和真实 A1 Student | 生成 FP32 candidate、Validation 指标和 hard cases | 固定输入上的可复现开发结果 | Frozen Test PASS、板端性能 |
| Independent evaluation | B2 独立保管的 Frozen Test | 给出最终 PASS/FAIL 和错误分类 | 未见测试集上的验收结果 | 不能反向参与训练或选 checkpoint |

四种等级的产物必须分目录保存。Smoke 成功不能写成“FP32 Gate 通过”；Formal
Validation 成功也不能替代 B2 的 Frozen Test 结论。

## 3. 当前正式配置

当前正式入口为 `challenge/distillation/train.py`，D2 v1.1 配置为
`challenge/distillation/d2_v1_1_formal_config.yaml`。

| 项 | 当前值 |
|---|---|
| 数据发布 | `challenge/dataset/releases/d2_v1_1/` |
| 随机种子 | `20260918` |
| Epoch | `3` |
| Batch size | `8` |
| 优化器 | AdamW |
| Learning rate | `1e-4` |
| Weight decay | `1e-4` |
| Gradient clipping | `1.0` |
| Checkpoint 选择指标 | `plan_sequence_accuracy` |
| 类别均衡 | 关闭；实现保留，且只允许由 Train 统计 |
| 训练输出 | `artifacts/challenge/distillation/d2_v1_1_fp32_baseline_v1/` |

`challenge/distillation/train_config.yaml` 是通用模板，不是正式 D2 证据；模板中的
`PENDING_B1` 等占位值在正式运行前必须被固定版本和哈希替代。

## 4. Loss 合同

训练使用结构化 hard label。当前正式配置 `soft_alpha=0.0`；代码虽能读取
Teacher 的 behavior/target-pointer soft logits，但正式 D2 不使用它们，不能把当前
结果描述为 soft-logit 蒸馏。

| Head | Loss | 权重 | 有效位置 |
|---|---|---:|---|
| Behavior | Cross Entropy | 2.0 | `step_mask` |
| Target pointer | Cross Entropy | 1.5 | `step_mask` |
| Target lane | Cross Entropy | 0.5 | `step_mask` |
| Target speed | Smooth L1 | 0.5 | `step_mask ∩ speed_mask` |
| Completion type | Cross Entropy | 0.5 | `step_mask` |
| On failure | Cross Entropy | 0.3 | `step_mask` |
| Confidence | Smooth L1 | 0.2 | 样本级 |
| Replan conditions | Multi-label BCE | 0.2 | 样本级 |
| Plan length | Cross Entropy | 0.5 | 样本级 |
| Requires confirmation | BCE | 0.2 | 样本级 |

计划不足 4 步时，后续位置必须 padding 且 `step_mask=0`；padding 不得进入任何
逐步 loss。Target speed 缺失时还必须令对应 `speed_mask=0`。样本风险权重当前为
normal `1.0`、complex `1.5`、safety-critical `2.5`。如果启用 class balance，只能
从 Train 估计，禁止读取 Val 或 Test 标签分布。

## 5. 训练前 fail-closed 检查

正式运行必须在以下任一项不满足时直接失败，而不是降级继续：

1. Git 工作区不干净，或记录的 Git SHA 与实际代码不一致。
2. release manifest、split manifest、JSONL、RGB mapping 或图像集合哈希不匹配。
3. Train/Val 的 `sample_id`、分组键或 RGB 出现交叉。
4. 输入带有 `test`、`frozen` 等受保护 provenance。
5. 数据集版本、Teacher repo/revision/fingerprint、schema 版本不一致。
6. target pointer 越界、计划超过 4 步、类别非法或张量 shape/dtype 不符合合同。
7. JSON、模型输出、loss 或 gradient 出现 NaN/Inf。

数据预检结果必须写入 `dataset_preflight.json`，不能只保留终端截图。

## 6. Validation 指标与 checkpoint 选择

| 指标 | 含义 |
|---|---|
| `behavior_accuracy` | 有效步骤上的行为分类准确率 |
| `target_pointer_accuracy` | 有效步骤上的目标槽位准确率 |
| `target_lane_accuracy` | 有效步骤上的目标车道准确率 |
| `target_speed_mae` | 有速度标签步骤上的速度 MAE，单位 m/s |
| `completion_accuracy` | 有效步骤上的完成条件准确率 |
| `failure_accuracy` | 有效步骤上的失败策略准确率 |
| `plan_length_accuracy` | 计划长度准确率 |
| `confirmation_accuracy` | 是否需要确认的准确率 |
| `replan_recall` | 重规划条件多标签召回率 |
| `plan_sequence_accuracy` | 长度及五个离散逐步字段全部正确的样本比例 |
| `safety_critical_behavior_recall` | safety-critical 样本上的行为召回率 |

当前 checkpoint 只按 `plan_sequence_accuracy` 选择，且使用严格 `>`；并列时保留
更早的 checkpoint。这个复合指标包含计划长度、behavior、target pointer、lane、
completion 和 on-failure，但**不包含** target speed、confidence、confirmation 和
replan。因此“best”不等于所有 Head 都最优，正式报告必须同时列出逐 Head 指标，
尤其是 speed MAE 与 safety-critical recall。没有有效分母的指标序列化为 `null`，
不能伪装成 0 或 100%。

## 7. 确定性与断点恢复

训练固定 Python、NumPy、PyTorch 和 DataLoader generator 的 seed，并启用
`CUBLAS_WORKSPACE_CONFIG`、cuDNN deterministic 和 PyTorch deterministic
algorithms。Checkpoint 保存：

- 模型、优化器、scheduler 状态；
- epoch、global step、best metric 和运行 metadata；
- Python、Torch、CUDA RNG 状态；
- DataLoader generator 状态。

当前恢复粒度是 **epoch 边界**，不是 batch 中点。恢复前必须校验配置、数据集和
模型身份；不得用另一个 release 或另一版代码继续旧 checkpoint。现有证据只能支持
同一软件/硬件环境中的可重复性，不能仅凭 seed 宣称跨服务器逐 bit 一致。

## 8. 正式输出与语义

正式输出目录至少包含：

- `training.jsonl`：逐 epoch 的 Train/Val loss、指标和选择状态；
- `student_fp32_best.pt`：按选择指标得到的最佳训练 checkpoint；
- `student_fp32_last.pt`：最后一个 epoch 的恢复点，不等于最佳模型；
- `student_v0_fp32_candidate.pt` 与 `.json`：待独立评测的候选件和身份 manifest；
- `training_summary.json` 与 `training_report.md`：配置、指标和限制；
- `dataset_preflight.json`：训练前数据门禁证据；
- `hard_cases/`：Validation 误差样本和分类汇总。

训练结束后应重新加载 `student_fp32_best.pt` 计算最终 Validation 指标，再生成
hard cases 和 candidate manifest，避免把内存中最后一轮模型误当成最佳模型。

## 9. 三类 Hard-case 的边界

### 9.1 B1 发布前隔离样本

B1 的 quarantine/reserved pool 用于数据 provenance 审计。例如终态不一致、lane
gap 不安全或发布门禁失败的样本不得混入普通 Train/Val。A3 只读取 B1 明确签发的
可训练 split。

### 9.2 A3 Validation 误差

A3 在 Val 上比较 Student 与 Teacher，按 behavior、target pointer、lane、speed、
completion、on-failure、plan length、confirmation、replan 分类，并附加
safety-critical 与 multi-step 标签。Speed 绝对误差大于 `1.0 m/s` 视为 hard case。
挖掘器拒绝名称含 `test` 或 `frozen` 的 split。

### 9.3 B3 闭环外部回传

`challenge/hil/hard_cases_handoff.md` 已定义 B3 回传格式，但当前 A3 尚无 importer、
样本 join、去重和重划分实现。因此外部 hard case 目前只能审计，不能直接进入下一轮
训练。正式接入至少需要：

1. 校验 B3 artifact、运行时模型和场景身份；
2. 用稳定键关联原样本/场景，禁止按自然语言模糊匹配；
3. 去除 Frozen Test 来源和不可训练数据；
4. 保留失败证据并由 B1/Teacher 重新签发标签；
5. 按 group key 重建 Train/Val，重新做 overlap 检查；
6. 生成新的 dataset version 和 release manifest，禁止原地改旧 release。

## 10. 当前 baseline 可以和不可以声称什么

D2 baseline 记录为 Train `2332`、Val `489`、3 epochs、876 updates，
`plan_sequence_accuracy=1.0`，`target_speed_mae≈0.980 m/s`，并产生 217 条 speed
hard cases。这证明训练、重载 best、逐 Head 评测和 hard-case 导出链路可执行。

但当前 Train/Val 的文本与场景模式高度重叠，Val 中 477/489 可由文本查表命中。
因此 100% 的离散计划准确率不能表述为真实泛化。后续必须同时报告 shortcut audit、
text-only/vision-only/full-modality ablation 和真正按 route/scenario family 隔离的验证。

## 11. 可执行命令

从仓库根目录运行：

```bash
# 真实 release 小切片，只验证集成链路
python -m challenge.distillation.train \
  --config challenge/distillation/d2_v1_1_smoke_config.yaml \
  --integration-smoke

# 完整正式训练
python -m challenge.distillation.train \
  --config challenge/distillation/d2_v1_1_formal_config.yaml

# 从已完成 epoch 的 checkpoint 恢复
python -m challenge.distillation.train \
  --config challenge/distillation/d2_v1_1_formal_config.yaml \
  --resume artifacts/challenge/distillation/d2_v1_1_fp32_baseline_v1/student_fp32_last.pt

# 训练后的 shortcut 与模态贡献审计
python -m challenge.distillation.shortcut_probe \
  --view-dir artifacts/a3_d2_v1_1_positive_view_v1
python -m challenge.distillation.ablation_eval \
  --config challenge/distillation/d2_v1_1_formal_config.yaml \
  --run-dir artifacts/challenge/distillation/d2_v1_1_fp32_baseline_v1
```

命令行参数以 `--help` 和当前代码为准；若入口变化，必须同步更新本文而不是保留失效命令。

## 12. 实验交付与完成定义

每次正式实验至少交付：Git SHA、Python/PyTorch/CUDA 环境、Student factory、完整
config、数据和 Teacher 身份、release/preflight manifest、逐 epoch 日志、best/last
checkpoint 哈希、逐 Head Validation 指标、hard-case 分类、shortcut/ablation 结果和
已知限制。不得为了提升结果随机重切数据或查看 Frozen Test 后重训。

A3 阶段完成的条件不是“loss 下降”，而是：正式数据身份可复核、训练可恢复、最佳
checkpoint 选择可解释、逐 Head 误差可定位、hard cases 可回流、FP32 candidate
manifest 可签发，并由 B2 在独立 Frozen Test 上给出结论。当前仓库尚无真实
`A3_FP32_GATE_PASSED` manifest；在独立评测完成前，candidate 必须保持待验状态。
