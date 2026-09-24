# A2 INT8 量化执行入口

当前代码可完成四件事：从 B1 D2 Train 生成确定性的开发校准集、用 ONNX Runtime QDQ
跑通 INT8 PTQ 冒烟、生成十个 Head 的 FP32/INT8 原始输出漂移报告，以及生成可交给
OpenExplorer 3.9.1 的四输入 NPY、Student J6P YAML 和身份清单。

当前正式状态仍是 **BLOCKED**：仓库没有 `A3_FP32_GATE_PASSED` 权重/ONNX，也没有 B1/B2
签发的正式 Calibration。OpenExplorer 已锁定为 3.9.1、J6P march 已锁定为 `nash-p`，
但官方镜像需从 OE 下载页取得，板端实测仍缺 J6P。开发产物强制标为
`SMOKE_ONLY`、`A3_CANDIDATE_PRE_PTQ` 或 `A2_DEVELOPMENT_CALIBRATION_CANDIDATE`，不能用于申报成绩。

## A3 候选权重预演

收到 `PENDING_A3_FP32_GATE` 的纯 state_dict 和候选 manifest 后，可显式导出候选 ONNX：

```powershell
python -m challenge.export.export_onnx `
  --output artifacts/a2/a3_candidate_v3/student_v0_fp32_candidate.onnx `
  --weights <student_v0_fp32_candidate.pt> `
  --weights-manifest <student_v0_fp32_candidate.json> `
  --allow-pending-candidate
```

该开关仍校验 model/config/权重 SHA256，并在 ONNX 中保留
`weights_status=PENDING_A3_FP32_GATE`，不会生成正式 Gate 标记。导出后可用
`export-consistency` 在真实样本上比较 PyTorch 与 ONNX 的十个原始 Head。
候选 ONNX 执行 PTQ 和 OpenExplorer 输入准备时使用 `--allow-candidate`；
`--allow-smoke` 只用于随机初始化等普通工具链冒烟，二者不会混淆标记。

Windows 上的 ONNX Runtime 1.30 在本机含中文的仓库路径生成 `-inferred.onnx` 时会破坏
路径编码。实际 PTQ 应从不解析回中文目标的 ASCII 工作路径或容器内运行；代码会保留
调用方提供的 ASCII junction 路径。

## 1. 生成 400 条开发校准集

```powershell
python -m challenge.quantization.cli build-calibration `
  --source challenge/dataset/releases/d2_v1_1/train.jsonl `
  --out artifacts/a2/dev_calibration_400 `
  --count 400
```

选择过程只读取 Train，拒绝 `test/reserved/benchmark/official_like` 路径；逐张检查 RGB
存在性及 SHA256，并按样本类别、风险等级和首个行为确定性分层抽取。

## 2. 跑开发 PTQ 冒烟

```powershell
python -m challenge.quantization.cli ptq `
  --source-onnx challenge/student_v0_fp32.onnx `
  --calibration-jsonl artifacts/a2/dev_calibration_400/calibration.jsonl `
  --calibration-manifest artifacts/a2/dev_calibration_400/calibration_manifest.json `
  --output artifacts/a2/ort_qdq_smoke/student_int8.onnx `
  --allow-smoke
```

这里的 `--allow-smoke` 是显式安全阀，因为当前 ONNX 是随机初始化。去掉该参数时工具会
拒绝非 `A3_FP32_GATE_PASSED` 模型。ONNX Runtime 产物仅验证 A2 流程，不代表
OpenExplorer 或 J6P 可用。

## 3. 生成逐 Head 漂移报告

```powershell
python -m challenge.quantization.cli drift `
  --baseline-onnx challenge/student_v0_fp32.onnx `
  --candidate-onnx artifacts/a2/ort_qdq_smoke/student_int8.onnx `
  --jsonl artifacts/a2/dev_calibration_400/calibration.jsonl `
  --output artifacts/a2/ort_qdq_smoke/quant_error_report.json `
  --limit 100
```

报告包含每个 Head 的 mean/P95/P99/max absolute error，以及离散 Head 的 argmax
一致率。这只是敏感层分析和 B2 Gate 前的诊断，不能替代真实标签精度评测。

## 4. 准备 OpenExplorer 3.9.1 输入包

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
2. B1/B2 签发 300～500 条正式 Calibration release；
3. A4/B3 在官方 OpenExplorer 3.9.1 镜像内验证 Student YAML，并返回算子/CPU回退报告；
4. B2 固定 INT8 的逐 Head、safety-critical 和累计性能衰减政策。
