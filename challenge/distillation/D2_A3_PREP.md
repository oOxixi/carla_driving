# A3：D2 v1.1 分工前预检与试运行

基线：GitHub `challenge` 提交 `64577ea046ced0fef3a177f39d88280a82f45253`。
下游数据只使用 `challenge/dataset/releases/d2_v1_1/`；`d2_v1/` 为历史发布，不参与本轮新训练。

## 已完成的准备

1. `python -m challenge.dataset.validate_d2_release` 核验 B1 的 `release_manifest.json`、各文件 SHA256/字节数、3592 张 RGB 的逐张哈希与图片集哈希、Train/Val/Reserved 的 sample ID 和 group key 隔离、8 条 quarantine 未回流。服务器结果：`valid=true`，`error_count=0`。
2. A3 图片读取器兼容仓库相对路径 `<sample_id>.jpg` 和历史 `<rgb_sha256>.jpg`；两种路径均逐张核对 SHA256 与大小，拒绝路径越界。
3. `python -m challenge.dataset.build_a3_d2_view` 在 `artifacts/` 生成**派生**普通监督视图，不改 B1 发布文件。它逐样本核验 cohort 与 D1/v3/v4 pinned Teacher manifest，并添加来源清楚的 A3 metadata。`excluded_sample_ids.jsonl` 明确记录全部排除项。
4. A3 严格视图：Train 2332、Val 489；完整预检（ModelRequest、Plan、Teacher model/revision/fingerprint、RGB、split、标签、交叉泄漏）为 **0 错误、0 警告**。
5. 服务器两步 integration smoke：最多 50 条 Train、50 条 Val，A1 Student 前向、loss、反向、checkpoint、Val 评估全部完成；`global_step=2`，CUDA，产物 `MOCK_ONLY`。这只证明管线可运行，**不是模型准确率结论**（初始 `plan_sequence_accuracy=0.0`）。
6. `audit_d2_view` 逐项复核签发包、派生视图与排除样本的精确分区，并输出只含聚合计数的标签覆盖报告；验证指标已补充 `normal_*`、`complex_*`、`safety_critical_*` 三类独立结果，分母按有效标签/样本加权，空批次不会污染统计。
7. 全量 A1 四模态输入检查通过：2332/2332 Train、489/489 Val 的真实 RGB 均成功读取并打包成固定形状，0 错误；这仍是数据/输入管线检查，不是 Student 前向或准确率证明。服务器产物为 `artifacts/a3_d2_prep/a1_full_input_check.json`。

## 数据角色与额外保守隔离

B1 签发包：Train 2513、Val 539、Reserved 540、图片 3592；另有 B1 quarantine 8 条。

A3 派生普通监督视图额外排除：

| 原因 | Train | Val | 处理 |
| --- | ---: | ---: | --- |
| B1 `HARD_NEGATIVE` / `valid_for_training=false` | 143 | 31 | 不当作正确 Teacher Plan 监督；另行设计安全训练或难例分析 |
| `run_status`、command/plan terminal 或场景 acceptance 非完整成功 | 38 | 19 | 保守隔离，等待 B1/B2 评估其是否可作部分监督 |

第二行中有 8 条旧 D1 plan 失败/安全覆盖记录，与 B1 本次 quarantine 的 8 条“run 失败但 plan/command 成功”**不是同一组**。A3 不修改 B1 标签，只在普通监督视图中保守排除。Train/Val 所有保留样本维持原 sample ID、group key、来源 dataset version、原始 Teacher SHA；新增的模型 revision/fingerprint 明确记录所依托的 pinned cohort manifest 及其 SHA。

## 数据覆盖审计与需要 B1/B2 关注的缺口

服务器 `artifacts/a3_d2_prep/label_coverage.json` 的结果为 `PASS`，签发包 SHA 为 `cf153d2f536f9180241f02a9d644aca6da2a508beb785591399dbb75b847462f`，派生视图 manifest SHA 为 `f797725014f297bf1ca43444b95a9aa43bf566abb4fcaebfc1841b4851cd8fcf`。该报告是**标签/来源覆盖统计，不是模型评分**。

| 项目 | Train | Val | 解释 |
| --- | ---: | ---: | --- |
| 普通 / 复杂 / 安全关键 | 1858 / 332 / 142 | 338 / 117 / 34 | 安全关键单独出指标和分母 |
| `safety_D` 内安全关键 | 10 | 1 | 此切片的 Val 结论方差极大，需补数据或独立评测 |
| `Town03_Opt` | 1 | 0 | 不能宣称此地图已有 Val 泛化验证 |
| 1 步 / 2 步计划 | 2178 / 154 | 437 / 52 | 无 3–4 步正样本，不能宣称完整 4 步规划能力 |
| 有指向具体目标的步骤 | 421 | 117 | 与无目标指针分开观察 |

严格正样本 Train+Val 共 2821，低于分工文件 D2 建议的 3000–5000 有效 Teacher 样本下限。A3 不自行改 B1 划分或混入 Reserved 来补数量。需要 B1 针对薄弱切片补采，并由 B2 定义独立评价口径；现有 B1 Train/Val 和 A3 视图 SHA 在本轮实验中保持不变。

现有 `safety_critical_behavior_recall` 指标是安全关键样本中**有效步骤的多类别 Behavior micro recall**（数值等同该切片的 Behavior accuracy），不是事故检出率，也不能替代 B2 的安全闭环评测。三类独立指标用于定位模型偏差，最终成绩仍以 B2 冻结口径为准。

当前正样本 Train/Val 还都没有 `YIELD`、`PULL_OVER`、`HOLD` Behavior 标签。针对总量、地图、安全切片、计划长度与缺失标签的具体 B1 补采请求见 [B1_D2_COVERAGE_REQUEST.md](B1_D2_COVERAGE_REQUEST.md)。这些不能通过复制样本、将 hard negative 当正例或手工扩写 Teacher plan 补足。

## 服务器路径与复现命令

独立工作目录：`/home/tiaozhansai/carla-driving-challenge-a3-prep`。
Python：`/home/tiaozhansai/carla-driving-challenge/.venv/bin/python`。

在工作目录下执行：

```bash
python -m challenge.dataset.validate_d2_release --output artifacts/a3_d2_prep/v1_1_release_integrity.json
python -m challenge.dataset.build_a3_d2_view
python -m challenge.distillation.audit_d2_view \
  --output artifacts/a3_d2_prep/label_coverage.json
python -m challenge.distillation.validate_a1_inputs \
  --output artifacts/a3_d2_prep/a1_full_input_check.json
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
策略 `signed_d2_release_smoke` 只允许 integration smoke，不能把 Smoke checkpoint 当正式 Student。另备 `d2_v1_1_formal_config.yaml` 与 `signed_d2_release_formal` 门禁：必须在干净提交上运行，检查 B1 release、A3 view 全部文件、样本分区、Teacher cohort manifests、全量 RGB/标签预检；训练产物带两个 manifest SHA 并保持 `PENDING_A3_FP32_GATE`。**目前只验证了正式门禁，尚未执行正式多轮训练，也未批准 FP32 晋级。**正式训练基线命令：

```bash
python -m challenge.distillation.train \
  --config challenge/distillation/d2_v1_1_formal_config.yaml
```

该命令必须等本轮代码完成审查并提交为干净版本后执行。混合 Teacher cohort 的独立 B2 评测与晋级证据契约仍待确认，不能用既有单 Teacher 晋级口径直接放行。

## 之后如何分工

所有实验使用同一份固定 Train/Val 和同一个派生视图 manifest，不要按人随机分拆样本后各报准确率。可并行分配损失权重、采样/类别平衡、模型容量或优化器实验；每个实验单独配置、随机种子、输出目录，提交代码 SHA、B1 release manifest SHA、A3 view manifest SHA、训练日志、各 Head Val 指标、安全关键召回、难例分类和 checkpoint SHA。Reserved 候选仅供 B1/B2 保管，不用于训练、调参或选 checkpoint。

第一轮实验建议固定 A1 Student 结构、数据视图和优化器，只比较基线 loss 与安全类加权/类平衡；第二轮依据**同一 Val** 的各 Head 和安全切片确定优先修复项，不能因个别切片只有 1 条就宣布提升。每个候选先通过数据签名、全量预检、训练可复现及 B2 离线评测，达到条件后才能申报 `student_fp32_best`。正式入口现已实现但尚未执行；它只生成待审 Candidate，不自行判定精度门槛通过。
