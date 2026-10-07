# A2 robust FP32 candidate v3 量化诊断结果（2026-10-07）

## 结论

A2 已对 A3 的 `a3_b1_closeout_robust_fp32_candidate_v3` 完成候选阶段全链路：
上游身份审计、真实权重 FP32 ONNX 导出、300 样本 PyTorch/ONNX 一致性、冻结
Calibration v1 Full INT8、25 个节点敏感性扫描、Top-3 Mixed Precision，以及
OpenExplorer 3.9.1 四输入包准备。

该链路仍是 `PENDING_A3_FP32_GATE` / `DIAGNOSTIC_ONLY`，不是
`A3_FP32_GATE_PASSED`、`A2_INT8_GATE_PASSED`、J6P 编译通过或板端实测结论。
B2 readiness 对该 robust v3 实跑仍有 7 个 blocker，因此这些候选文件不能改名为 Final。

## 身份与治理边界

| 项目 | 值 |
|---|---|
| A2 workflow Git SHA | `11823750b530f0bfebe22427113f2034d306d3b2` |
| A3 training Git SHA | `18a95de9702fe7baa5e89aa74a93dcd86d88d537` |
| model / config | `student-v0-r3-fp32` / `student-v0-r3-structure-20260911` |
| dataset view | `b1_governed_closeout_v1_a3_strict_positive_v1` |
| governed source counts | Train `6037` / Dev `1158` |
| optimizer view counts | Train `5856` / Validation `1108` |
| FP32 weights SHA256 | `7f379c78c170228713e3d91b8e2eabd04172010ae0ed0b8cf71afe291fe6e805` |
| A3 handoff manifest file SHA256 | `4c42406320a99150946b1ff0fde506ad6f6a4ac4fe3b484d20dbf944262f1f63` |
| B1 governed release SHA256 | `07d3a82502005646d8f29d0c493fa8a5b0270a5194fd5c802a04b4870ba7d37d` |
| Calibration manifest published SHA256 | `659c5e8210ee95cf835be685da1deb55bc1990874ba3e120955d6bdf392d8059` |

上游审计的唯一 A2 blocker 是
`A3_FP32_GATE_NOT_PASSED:PENDING_A3_FP32_GATE`。A2 只使用冻结 Calibration v1；
B1 的 240 条 Independent Validation 标签没有用于校准、敏感层排序或误差驱动迭代。

## FP32 ONNX 导出一致性

| 项目 | 值 |
|---|---|
| A2 FP32 ONNX SHA256 | `681a5d4bf16ba61741ef0e559649c43c041de649eef3e8e6f0b6285beaab4286` |
| 文件大小 | `92,041,414` bytes |
| 样本数 | `300`（完整 Calibration v1） |
| 容差 | `atol=1e-4`、`rtol=1e-4` |
| 结果 | `PASS`，十个 Head 全部通过 |
| 全局最大绝对误差 | `1.33514404296875e-05` |

因此下述 FP32/INT8 差异来自量化候选，不是错误权重或 PyTorch/ONNX 导出不一致。

## Full INT8

| 项目 | 值 |
|---|---|
| quantization id | `a2-ptq-081fc9e26074a181` |
| status / gate | `A3_CANDIDATE_PRE_PTQ` / `NOT_FORMAL` |
| INT8 SHA256 | `275dce5c426fff85a0375eb286fc67febac8d835c1e36fe15b0fbd707cf836c3` |
| 文件大小 | `23,273,686` bytes |
| 相对 FP32 体积减少 | `74.7139%` |
| QuantizeLinear / DequantizeLinear | `57 / 107` |

量化策略为 QDQ、QInt8 对称激活、QInt8 对称逐通道权重、MinMax，使用全部
300 条冻结 Calibration v1。

### 300 样本逐 Head 漂移

| Head | Mean absolute error | P95 | Max | Argmax agreement |
|---|---:|---:|---:|---:|
| plan length | `0.047847` | `0.112080` | `0.204066` | `1.0000` |
| behavior | `0.046854` | `0.107954` | `0.185177` | `0.9983` |
| target pointer | `0.055094` | `0.126084` | `0.249572` | `1.0000` |
| target lane | `0.046399` | `0.105966` | `0.216833` | `1.0000` |
| target speed | `0.207643 m/s` | `0.606748 m/s` | `1.171743 m/s` | N/A |
| completion | `0.042732` | `0.102262` | `0.215443` | `0.9925` |
| on failure | `0.054875` | `0.128095` | `0.268919` | `1.0000` |

离散头在原始输出层面较稳定，但速度头漂移明显高于上一版候选，不能直接把 Full INT8
定为最终模型。该表不使用真实标签，不能替代 B2 精度 Gate。

## 敏感层与 Top-3 Mixed Precision

25/25 个命名节点实验完成。本次 v3 独立得到的前四名为：

| 排名 | 节点 | 诊断改善分 |
|---:|---|---:|
| 1 | `/model/target_pointer_head/Gemm` | `0.107354` |
| 2 | `/model/behavior_head/Gemm` | `0.106645` |
| 3 | `/model/target_lane_head/Gemm` | `0.091940` |
| 4 | `/model/state_encoder/layers/layers.2/Gemm` | `0.010711` |

前三名与第四名存在明显断层，因此生成只保留这三个输出层为 FP32 的 Mixed Top-3：

| 项目 | 值 |
|---|---|
| quantization id | `a2-ptq-300ccd212fa728a9` |
| INT8 SHA256 | `9a08a03c42a9ea59ead664d168254cd3685d73d176d5ab53507bd4a4467132d3` |
| 文件大小 | `23,622,853` bytes |
| 相对 Full INT8 增加 | `1.5003%` |
| 相对 FP32 体积减少 | `74.3345%` |
| QuantizeLinear / DequantizeLinear | `51 / 95` |

| Head | Full INT8 MAE | Mixed MAE | Full argmax | Mixed argmax |
|---|---:|---:|---:|---:|
| behavior | `0.046854` | `0.026867` | `0.9983` | `1.0000` |
| target pointer | `0.055094` | `0.031436` | `1.0000` | `1.0000` |
| target lane | `0.046399` | `0.029335` | `1.0000` | `1.0000` |
| target speed | `0.207643` | `0.207643` | N/A | N/A |

Mixed Top-3 改善三个离散输出头，但没有改善速度头。最终采用 Full INT8 还是 Mixed，必须由
B2 在同一冻结基准上比较精度，并由 A4 比较部署代价。

## OpenExplorer 交接输入

- 状态：`A3_CANDIDATE_OPENEXPLORER_INPUT_READY`，`formal_release=false`；
- OpenExplorer `3.9.1`，march `nash-p`；
- 300 组四输入，共 1200 个 NPY；
- input manifest SHA256：
  `a924721f03afdef3ab3ea44f12f13212e1949f080073662b72fe41deb2020534`；
- YAML SHA256：
  `299adaa788c8e9fc828d0ac091a91858a5bb3842be22eaa0b6175f89816c4f4f`。

OpenExplorer 正式编译、operator mapping、CPU fallback、BPU estimate 和 J6P 板端实测仍分别
属于 A4/B3；A2 的 ORT QDQ 模型不是 `hb_compile` 的正式输入。

## 与 B3 最新 v3 证据的交叉核对

B3 在提交 `197bc045` 前后补充了 robust v3 仿真、OpenExplorer 预编译、FLOPs 复算和
多模态消融。它提供了重要但仍是诊断性质的全赛道证据：

- 自建留出队列上 targeted-gap 从 `0.9192` 提升到 `1.0000`；Gap300、turn-gap 和
  ms34 与 v2 持平；`TURN_LEFT` 在 turn-gap `27/27`、Gap300 `108/108` 仍失败；
- 官方工具链预检为 59/59 节点落在 BPU、0 CPU fallback，最小内存约 `24.19 MB`；
  这是 `BPU_ESTIMATED`，不是 J6P 板端实测；
- 六个队列 850 例的 FP32 与编译产物对照中，十头最低余弦为 `0.999134`，低于
  `0.99` 的观测为 0；
- FLOPs 七个关键字段与仓库报告逐项一致，但使用同一工具复算只证明可复现，Teacher
  分母定义仍需团队确认；
- 150 例零值消融显示计划主要由 `state` 主导；置零 rgb/text/targets 没有引起 behavior
  argmax 翻转，存在“多模态融合有效性”评分风险；异常输入套件为 9/10，空文本没有
  fail-closed。

B3 该轮记录的 FP32 ONNX SHA256 为
`b76b5a32dfde16d52b34ad553bce9e899eaf4220142a8ddd6e9b4aea4fc808e5`，与 A2 本轮
`681a5d4b...4286` 的字节 SHA 不同，尽管两者都声明来自同一权重 SHA。正式 RC 必须选择
唯一 ONNX 字节并让 A4/B3 对该 exact SHA 重跑或补充等价性证明；现阶段不能把 B3 结果
直接写成 A2 ONNX 的 exact-artifact Gate。

## B2 readiness 与剩余 Gate

robust v3 的 readiness 仍为 `BLOCKED`，共有 7 项：Independent Validation benchmark
未冻结、case manifest 缺失、formal policy 未冻结、policy version 缺失、slice 最小分母
缺失、multi-run merge rule 缺失，以及 B2 config dataset version 与本候选不一致。

下一步顺序必须是：

1. B2 修正并冻结独立验证身份和 policy，对权重
   `7f379c78...e805` 签发 decision；
2. A3 只在同一权重获得 PASS 后签发 `A3_FP32_GATE_PASSED`；
3. A2 对正式 FP32 ONNX 重走量化并交 B2 执行 INT8 Gate；
4. A4 对唯一 ONNX/INT8 SHA 生成正式编译、operator/fallback 和 Runtime；
5. B3 对同一 RC 做 X86/J6P 核验，B4 最后冻结 Release Manifest 和提交包。

## 验证与本机产物

- A2 量化测试：`16 passed in 9.87s`；
- 导出一致性：300/300，`PASS`；
- 敏感层：25/25 完成；
- OpenExplorer 输入：四输入各 300 个 NPY；
- 本机目录：`artifacts/a2/a3_robust_fp32_candidate_v3_11823750/`；
- 敏感层报告 SHA256：
  `c8e62223fdb14d78ffb128e08bbff589d4862e7b38678ef55ebba3288ea8c11c`。

### 分成员交接包

打包 evidence Git SHA 为 `3ebd0682fa70b46f1a679ecaeca808bb23f4ee7c`，本机目录为
`artifacts/a2/handoff_20261007_3ebd0682/`：

| 接收方 | 压缩包 | 大小 | SHA256 |
|---|---|---:|---|
| A3 | `A2_to_A3_gate_feedback_3ebd0682.zip` | `36,120` bytes | `03cac9f945bf5dc4169f768467d09b7024ed5ee4ce3f4904df18082e954e346a` |
| B2 | `A2_to_B2_evaluation_3ebd0682.zip` | `215,249,423` bytes | `95e0533092eccdfaa0ece830a92b33691a5fd010f5982d71e0d043e1ecf0a59f` |
| A4 | `PRE_GATE_ONLY_A2_to_A4_openexplorer_3ebd0682.zip` | `153,934,913` bytes | `543a2ee2ed93d1252230af5d99e2d7524514da0785ece4531a715196ce633918` |

三份 delivery SHA 和 ZIP CRC 全部通过。A4 包经 B3 独立校验器复核：1221/1221 文件
匹配、四输入各 300 个 NPY、两份 INT8 均与 manifest 匹配并绑定 robust v3，0 error、
0 warning，状态 `PASS`。这里的 `PASS` 只表示包自洽，不表示模型 Gate 或板端通过。

Windows 本机的 ONNX Runtime/pytest 需经 ASCII 映射路径运行；这是路径编码兼容问题，不是
模型测试失败。大模型、NPY 和交接 ZIP 继续保存在 `artifacts/`，不进入 Git。
