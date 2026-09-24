# A2：A3 FP32 v3 候选预演结果

## 身份

- 状态：`PENDING_A3_FP32_GATE`，只能作为候选预演。
- 模型：`student-v0-r3-fp32`。
- 权重 SHA256：`1afb8ebd11e401d4d7e6181d244ed39438421183c5303f1ce4a4391cee8cc68c`。
- 数据集：`b1_d2_v1_1_plus_d3_wave1_a3_strict_positive_v1`。

## 已完成

1. 交接包 9 个内部文件 SHA256 全部通过。
2. 从真实 state_dict 导出固定 Shape、opset 17 FP32 ONNX。
3. 20 条真实样本上完成 PyTorch/ONNX 十 Head 一致性，状态 `PASS`，全局最大绝对误差 `9.5367431640625e-06`。
4. 使用 400 条开发 Calibration 完成 ONNX Runtime QDQ PTQ 预演，产物状态 `A3_CANDIDATE_PRE_PTQ`；57 个 QuantizeLinear、107 个 DequantizeLinear。
5. 在 100 条样本上完成 FP32/ORT-QDQ 原始输出漂移分析。离散 Head argmax 一致率：plan length 1.0000、behavior 0.9875、target pointer 0.9825、target lane 0.9650、completion 0.9875、failure 1.0000。速度 Head mean/max 绝对误差为 `0.214840/1.214098 m/s`。
6. 生成 OpenExplorer 3.9.1、`nash-p` 的 400 组四输入 NPY、YAML 和身份清单，状态 `A3_CANDIDATE_OPENEXPLORER_INPUT_READY`。

## 仍缺

1. B2 对完全相同权重 SHA256 的独立 Validation 结果，以及 A3 的 `A3_FP32_GATE_PASSED` 晋级文件。
2. B1/B2 签发的 300～500 条正式 Calibration release。当前 400 条来自 Train，只能开发使用。
3. A4/B3 在 OpenExplorer 3.9.1 官方 Docker 镜像内执行 `hb_compile --model ... --march nash-p` 与 YAML 编译，返回算子支持、CPU fallback 和编译产物。
4. J6P 板卡上的精度一致性、时延、内存和稳定性实测。
5. B2 明确 INT8 各 Head、safety-critical 与累计性能衰减阈值；当前漂移报告不能自行判定通过。

## 结论

本地可完成的候选前置工作已经完成。收到前两项后可对同一权重和正式 Calibration 重跑正式 PTQ；收到 OpenExplorer Docker 与板卡结果后才能关闭部署 Gate。
