# A3：D2 v1.1 分工前预检与试运行

基线：GitHub `challenge` 提交 `64577ea046ced0fef3a177f39d88280a82f45253`。
下游数据只使用 `challenge/dataset/releases/d2_v1_1/`；`d2_v1/` 为历史发布，不参与本轮新训练。

## 已完成的准备

1. `python -m challenge.dataset.validate_d2_release` 核验 B1 的 `release_manifest.json`、各文件 SHA256/字节数、3592 张 RGB 的逐张哈希与图片集哈希、Train/Val/Reserved 的 sample ID 和 group key 隔离、8 条 quarantine 未回流。服务器结果：`valid=true`，`error_count=0`。
2. A3 图片读取器兼容仓库相对路径 `<sample_id>.jpg` 和历史 `<rgb_sha256>.jpg`；两种路径均逐张核对 SHA256 与大小，拒绝路径越界。
3. `python -m challenge.dataset.build_a3_d2_view` 在 `artifacts/` 生成**派生**普通监督视图，不改 B1 发布文件。它逐样本核验 cohort 与 D1/v3/v4 pinned Teacher manifest，并添加来源清楚的 A3 metadata。`excluded_sample_ids.jsonl` 明确记录全部排除项。
4. A3 严格视图：Train 2332、Val 489；完整预检（ModelRequest、Plan、Teacher model/revision/fingerprint、RGB、split、标签、交叉泄漏）为 **0 错误、0 警告**。
5. 服务器两步 integration smoke：最多 50 条 Train、50 条 Val，A1 Student 前向、loss、反向、checkpoint、Val 评估全部完成；`global_step=2`，CUDA，产物 `MOCK_ONLY`。这只证明管线可运行，**不是模型准确率结论**（初始 `plan_sequence_accuracy=0.0`）。

## 数据角色与额外保守隔离

B1 签发包：Train 2513、Val 539、Reserved 540、图片 3592；另有 B1 quarantine 8 条。

A3 派生普通监督视图额外排除：

| 原因 | Train | Val | 处理 |
| --- | ---: | ---: | --- |
| B1 `HARD_NEGATIVE` / `valid_for_training=false` | 143 | 31 | 不当作正确 Teacher Plan 监督；另行设计安全训练或难例分析 |
| `run_status`、command/plan terminal 或场景 acceptance 非完整成功 | 38 | 19 | 保守隔离，等待 B1/B2 评估其是否可作部分监督 |

第二行中有 8 条旧 D1 plan 失败/安全覆盖记录，与 B1 本次 quarantine 的 8 条“run 失败但 plan/command 成功”**不是同一组**。A3 不修改 B1 标签，只在普通监督视图中保守排除。Train/Val 所有保留样本维持原 sample ID、group key、来源 dataset version、原始 Teacher SHA；新增的模型 revision/fingerprint 明确记录所依托的 pinned cohort manifest 及其 SHA。

## 服务器路径与复现命令

独立工作目录：`/home/tiaozhansai/carla-driving-challenge-a3-prep`。
Python：`/home/tiaozhansai/carla-driving-challenge/.venv/bin/python`。

在工作目录下执行：

```bash
python -m challenge.dataset.validate_d2_release --output artifacts/a3_d2_prep/v1_1_release_integrity.json
python -m challenge.dataset.build_a3_d2_view
python -m challenge.distillation.preflight \
  --train artifacts/a3_d2_v1_1_positive_view_v1/train.jsonl \
  --val artifacts/a3_d2_v1_1_positive_view_v1/val.jsonl \
  --dataset-version b1_d2_v1_1_a3_strict_positive_v1 \
  --teacher-model-id Qwen/Qwen3.5-2B \
  --teacher-model-revision 15852e8c16360a2fea060d615a32b45270f8a8fc \
  --teacher-artifact-fingerprint-sha256 4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa \
  --asset-root . --require-rgb \
  --output artifacts/a3_d2_prep/v1_1_a3_strict_view_preflight.json
python -m challenge.distillation.train \
  --config challenge/distillation/d2_v1_1_smoke_config.yaml --integration-smoke
```

两步 Smoke 输出：`artifacts/challenge/distillation/d2_v1_1_smoke/integration_gate/`。
现阶段策略 `signed_d2_release_smoke` 只允许 integration smoke；正式大规模训练和 FP32 promotion 仍需单独评审并提交干净代码，不能把 Smoke checkpoint 当正式 Student。

## 之后如何分工

所有实验使用同一份固定 Train/Val 和同一个派生视图 manifest，不要按人随机分拆样本后各报准确率。可并行分配损失权重、采样/类别平衡、模型容量或优化器实验；每个实验单独配置、随机种子、输出目录，提交代码 SHA、B1 release manifest SHA、A3 view manifest SHA、训练日志、各 Head Val 指标、安全关键召回、难例分类和 checkpoint SHA。Reserved 候选仅供 B1/B2 保管，不用于训练、调参或选 checkpoint。
