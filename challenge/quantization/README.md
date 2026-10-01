# A2 INT8 量化执行入口

当前代码可完成：冻结 Calibration v1 的治理/张量合同校验、从 B1 D2 Train 生成开发
Calibration、按外置 `quant_config.yaml` 执行 ONNX Runtime QDQ PTQ、生成完整 INT8
身份清单、比较十个 Head 的 FP32/INT8 原始输出、逐节点恢复 FP32 的敏感层受控实验，
以及生成可交给 OpenExplorer 3.9.1 的四输入 NPY、Student J6P YAML 和身份清单。

当前正式签发仍是 **BLOCKED**：B1 已发布 `b1_closeout_v1`，最新 governed 规模是
Train=6037 / Dev=1158，Calibration v1 为300样本，Independent Validation v1 为240样本。
现有 A3 FP32 Candidate v1 仍绑定旧的5826/1104训练视图，状态为
`PENDING_A3_FP32_GATE`，也没有绑定最新 B1 governed release，因此只能继续作为诊断候选。
B2 尚未返回新 exact weights 的独立 Validation 和 INT8 Gate decision。A2 已完成旧候选的真实 ONNX、Full INT8、
300样本漂移、25节点敏感性、Top-3 Mixed Precision和OpenExplorer输入包预演。OpenExplorer
已锁定为3.9.1、J6P march已锁定为`nash-p`，但官方镜像验证和板端实测仍待A4/B3。候选产物强制标为
`SMOKE_ONLY`、`A3_CANDIDATE_PRE_PTQ` 或 `A2_DEVELOPMENT_CALIBRATION_CANDIDATE`，不能用于申报成绩。

## 0. 校验 B1 closeout 与 A3 上游候选

任何正式导出、PTQ或OpenExplorer交接前，先执行：

```powershell
python -m challenge.quantization.cli validate-upstream `
  --repo . `
  --weights challenge/distillation/releases/a3_final_fp32_candidate_v1/student_v0_fp32_candidate.pt `
  --weights-manifest challenge/distillation/releases/a3_final_fp32_candidate_v1/handoff_manifest.json `
  --output artifacts/a2/a3_upstream_intake.json
```

该命令逐项校验B1 `SHA256SUMS`、closeout状态、governed counts、正式Calibration绑定、
Independent Validation隔离策略、A3训练规模、governed release绑定、权重SHA256与FP32 Gate。
状态为`BLOCKED`时退出码为2，报告仍会落盘供协作。Independent Validation的标签严格归B2，
A2不得用它做校准、调参、敏感层选择或误差驱动迭代。

当前候选预期返回四个阻塞项：没有声明最新governed源计数6037/1158、缺少最新B1
governed release SHA256绑定、`PENDING_A3_FP32_GATE`。现有5826/1104是旧A3视图实际送入
optimizer的strict-positive计数，不与B1原始governed计数混为一谈。这不是工具失败，而是
正确的fail-closed结果。

## A3 候选权重预演

收到 `PENDING_A3_FP32_GATE` 的纯 state_dict 和候选 manifest 后，可显式导出候选 ONNX：

```powershell
python -m challenge.export.export_onnx `
  --repo . `
  --output artifacts/a2/a3_final_fp32_candidate_v1/student_v0_fp32_candidate.onnx `
  --weights challenge/distillation/releases/a3_final_fp32_candidate_v1/student_v0_fp32_candidate.pt `
  --weights-manifest challenge/distillation/releases/a3_final_fp32_candidate_v1/handoff_manifest.json `
  --allow-pending-candidate
```

该开关仍校验 model/config/权重 SHA256，并在 ONNX 中保留
`weights_status=PENDING_A3_FP32_GATE`和`a2_upstream_readiness=BLOCKED`，不会生成正式 Gate
标记。若权重manifest宣称`A3_FP32_GATE_PASSED`但上游治理审计仍有任何阻塞项，导出会直接
拒绝。导出后可用
`export-consistency` 在真实样本上比较 PyTorch 与 ONNX 的十个原始 Head。
候选 ONNX 执行 PTQ 和 OpenExplorer 输入准备时使用 `--allow-candidate`；
`--allow-smoke` 只用于随机初始化等普通工具链冒烟，二者不会混淆标记。

Windows 上的 ONNX Runtime 1.30 在本机含中文的仓库路径生成 `-inferred.onnx` 时会破坏
路径编码。实际 PTQ 应从不解析回中文目标的 ASCII 工作路径或容器内运行；代码会保留
调用方提供的 ASCII junction 路径。

## 1. 校验唯一正式 Calibration v1

```powershell
python -m challenge.quantization.cli validate-calibration-v1 `
  --repo . `
  --check-tensors
```

该命令复用B1发布校验器，检查300样本/300组、与Train/Dev零重叠、RGB与发布哈希，同时
验证`b1_closeout_v1`的SHA256台账、正式Calibration身份和独立验证隔离策略，并把
全部样本经过正式 `StudentPreprocessor`，核验四输入Shape、float32和有限值。正式PTQ只
接受 `challenge/dataset/releases/calibration_v1`；复制、改名或手写状态都会被拒绝。

## 2. 生成 400 条开发校准集

```powershell
python -m challenge.quantization.cli build-calibration `
  --source challenge/dataset/releases/d2_v1_1/train.jsonl `
  --out artifacts/a2/dev_calibration_400 `
  --count 400
```

选择过程只读取 Train，拒绝 `test/reserved/benchmark/official_like` 路径；逐张检查 RGB
存在性及 SHA256，并按样本类别、风险等级和首个行为确定性分层抽取。

## 3. 跑配置化开发 PTQ 冒烟

```powershell
python -m challenge.quantization.cli ptq `
  --source-onnx challenge/student_v0_fp32.onnx `
  --calibration-jsonl artifacts/a2/dev_calibration_400/calibration.jsonl `
  --calibration-manifest artifacts/a2/dev_calibration_400/calibration_manifest.json `
  --quant-config challenge/quantization/config/ptq_int8_v1.yaml `
  --output artifacts/a2/ort_qdq_smoke/student_int8.onnx `
  --allow-smoke
```

这里的 `--allow-smoke` 是显式安全阀，因为当前 ONNX 是随机初始化。去掉该参数时工具会
拒绝非 `A3_FP32_GATE_PASSED` 模型。ONNX Runtime 产物仅验证 A2 流程，不代表
OpenExplorer 或 J6P 可用。

输出目录同时包含 `source_fp32_manifest.json`、冻结配置副本、Calibration manifest副本、
`int8_structure.json`、`int8_manifest.json` 和 `commands.txt`。正式manifest初始状态只能是
`PENDING_B2_INT8_GATE`，A2不能自行签PASS。

## 4. 生成逐 Head 漂移报告

```powershell
python -m challenge.quantization.cli drift `
  --baseline-onnx challenge/student_v0_fp32.onnx `
  --candidate-onnx artifacts/a2/ort_qdq_smoke/student_int8.onnx `
  --jsonl artifacts/a2/dev_calibration_400/calibration.jsonl `
  --output artifacts/a2/ort_qdq_smoke/raw_output_drift.json `
  --limit 100
```

命令生成 `raw_output_drift.json`、`quant_error_report.json` 和
`head_sensitivity_preview.md`。报告包含每个Head的mean/P95/P99/max absolute error及离散
Head的argmax一致率。这只是B2 Gate前的诊断，不能替代真实标签精度评测。

## 5. 运行逐节点敏感性实验

```powershell
python -m challenge.quantization.cli sensitive-layers `
  --source-onnx <FINAL_FP32_ONNX> `
  --calibration-jsonl challenge/dataset/releases/calibration_v1/calibration.jsonl `
  --calibration-manifest challenge/dataset/releases/calibration_v1/calibration_manifest.json `
  --quant-config challenge/quantization/config/ptq_int8_v1.yaml `
  --output artifacts/a2/<quantization_id>/sensitivity
```

工具先生成Full INT8 baseline，再每次只排除一个命名Conv/Gemm/MatMul节点，使其恢复FP32，
比较十个Head并输出 `sensitive_layer_report.json` 和 `sensitive_layers.md`。只有B2精度通过且
A4确认部署代价可接受的节点，才可进入Mixed Precision白名单。

可用可重复的 `--exclude-node <ONNX节点名>` 生成受控 Mixed Precision 候选。该参数会进入
`quantization_id`、INT8 manifest和ONNX元数据，避免不同白名单的产物身份混淆。真实
Final FP32 Candidate v1 的完整预演结果见
`A2_FINAL_CANDIDATE_V1_RESULT_20260930.md`。

## 6. 准备 OpenExplorer 3.9.1 输入包

```powershell
python -m challenge.quantization.cli prepare-openexplorer `
  --source-onnx challenge/student_v0_fp32.onnx `
  --calibration-jsonl artifacts/a2/dev_calibration_400/calibration.jsonl `
  --calibration-manifest artifacts/a2/dev_calibration_400/calibration_manifest.json `
  --output artifacts/a2/openexplorer_smoke_oe391 `
  --allow-smoke
```

输出包括四个严格对齐的 NPY 目录、`student_j6p_oe391.yaml` 和
`openexplorer_input_manifest.json`。YAML 固定四输入名称/Shape、float32 featuremap、DDR
输入、`march=nash-p`。正式模式会拒绝非 Gate 权重和非正式 Calibration；`--allow-smoke`
只允许验证工具链。容器内执行：

```bash
hb_compile --model <FP32 ONNX> --march nash-p
cd <OpenExplorer输入包>
hb_compile -c student_j6p_oe391.yaml
```

正式 J6P 流程由 `hb_compile` 从 FP32 ONNX 完成校准、量化和编译。ORT QDQ产物只用于
提前分析量化漂移，不作为 OpenExplorer 的正式输入。

## 正式运行前必须替换

1. A3/B2 交付通过 Gate 的 FP32 权重、权重 manifest 和由该权重导出的 ONNX；
2. 使用已冻结的300条Calibration v1，不得另选Calibration；
3. A4/B3 在官方 OpenExplorer 3.9.1 镜像内验证 Student YAML，并返回算子/CPU回退报告；
4. B2 固定INT8逐Head、safety-critical和累计性能衰减政策，并对同一INT8字节签发decision。

B2 PASS到位后，用 `bind-b2-result` 将包含 `quantization_id`、INT8 SHA、benchmark SHA和
policy SHA的decision绑定进 `int8_manifest.json`。缺少任一身份字段都会失败，A2不能用
手工改状态代替B2签发。
