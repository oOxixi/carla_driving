# 挑战赛道全员提交收件清单（2026-10-07）

## 使用规则

本清单用于收件和 Final Freeze 前核对，不是 `final_submission/`。每个文件必须同时登记：

- 负责人、用途、相对路径、字节数、SHA256；
- 完整 Git SHA、模型/数据/配置/Runtime 身份；
- 状态与声明范围，例如 `CANDIDATE`、`DIAGNOSTIC_ONLY`、`X86_MEASURED`、
  `BPU_ESTIMATED`、`J6P_MEASURED`；
- 原始证据路径和生成命令；
- 被新版本取代时保留历史，但从 active RC 白名单移除。

缺 SHA、缺来源 manifest、状态靠改文件名得到、或者与 active RC 身份不一致的文件，一律不收
进 Final staging。

## 当前 active candidate 身份

| 项目 | 当前值 | 状态 |
|---|---|---|
| A3 release | `a3_b1_closeout_robust_fp32_candidate_v3` | Candidate |
| FP32 weights SHA | `7f379c78c170228713e3d91b8e2eabd04172010ae0ed0b8cf71afe291fe6e805` | `PENDING_A3_FP32_GATE` |
| dataset view | `b1_governed_closeout_v1_a3_strict_positive_v1` | B2 config 尚未对齐 |
| Calibration manifest SHA | `659c5e8210ee95cf835be685da1deb55bc1990874ba3e120955d6bdf392d8059` | Frozen |
| A2 FP32 ONNX SHA | `681a5d4bf16ba61741ef0e559649c43c041de649eef3e8e6f0b6285beaab4286` | Candidate |
| A2 Full INT8 SHA | `275dce5c426fff85a0375eb286fc67febac8d835c1e36fe15b0fbd707cf836c3` | `NOT_FORMAL` |
| A2 Mixed Top-3 SHA | `9a08a03c42a9ea59ead664d168254cd3685d73d176d5ab53507bd4a4467132d3` | `NOT_FORMAL` |

注意：B3 v3 仿真记录的 FP32 ONNX SHA 为 `b76b5a32...08e5`，与 A2 候选不是同一字节。
正式 RC 必须先统一 exact ONNX，不能把两条证据链直接拼接。

## 按成员收件

### A1：结构与 FLOPs

- [x] `challenge/model_structure.json`
- [x] `challenge/flops_report.json`
- [x] `challenge/A1_MODEL_INTERFACE.md`
- [x] B3 对七个关键 FLOPs 字段的可复现性复算
- [ ] A1/团队书面冻结 Teacher FLOPs 分母定义和 counting convention
- [ ] 若口径改变，重新生成带新 SHA 的正式报告，不覆盖历史文件

### B1：数据治理

- [x] governed release manifest 与 B1 closeout report
- [x] Calibration v1：300 samples / 300 groups，manifest 与 identity
- [x] Independent Validation v1 identity / case-set digest
- [x] legacy template lineage 不可恢复证明
- [ ] 与 B2 明确 template identity 缺失时的正式 policy 处置
- [ ] 禁止向 A2/A3 暴露 Independent Validation 标签用于调参

### A3：FP32 候选与签发

- [x] robust v3 `.pt`、训练配置、训练日志、训练总结、handoff manifest
- [x] 权重 SHA 与包内 identity 一致
- [ ] B2 对 exact weights 的独立 Gate decision
- [ ] A3 基于同一 SHA 签发或拒绝 `A3_FP32_GATE_PASSED`
- [ ] 最终报告需如实保留 `TURN_LEFT` 和多模态消融风险

### B2：Frozen Benchmark 与 Gate

- [ ] 把 benchmark config dataset version 对齐 governed closeout identity
- [ ] 冻结 Independent Validation case manifest
- [ ] 冻结 policy version、slice 最小分母和 multi-run merge rule
- [ ] 明确 legacy template identity 缺失处理
- [ ] 生成 Teacher/Student 原始 predictions、评价 summary、完整 run manifest
- [ ] 对 exact FP32 weights SHA 签 decision
- [ ] 在相同 Frozen Benchmark 上比较 Full INT8 与 Mixed Top-3，并签 INT8 decision

当前 7 项 blocker 未关闭前，不接受手工写出的 Gate PASS。

### A2：ONNX 与量化

- [x] robust v3 FP32 ONNX 与 300 样本导出一致性
- [x] Full INT8、25/25 敏感层、Mixed Top-3 漂移报告
- [x] OpenExplorer 3.9.1 YAML、300 组四输入、1200 NPY
- [x] A3/B2/A4 三份 SHA 锁定包，ZIP CRC 和独立包校验通过
- [ ] `A3_FP32_GATE_PASSED` 后对唯一正式 ONNX 重走正式链路
- [ ] B2 INT8 decision 到位后绑定 `A2_INT8_GATE_PASSED`

当前外置包目录：`artifacts/a2/handoff_20261007_3ebd0682/`。A4 包必须保留
`PRE_GATE_ONLY` 文件名。

### A4：OpenExplorer 与 Runtime

- [x] B3 已提供 robust v3 的工具链预检：59/59 BPU、0 CPU fallback
- [ ] 确认使用的 exact FP32 ONNX/INT8 SHA 与 Final RC 一致
- [ ] 官方 OpenExplorer 版本、容器 digest、march、完整命令和环境指纹
- [ ] compiled `.hbm`/`.bc` 及 SHA、operator mapping、fallback report
- [ ] BPU performance estimate 原始报告和口径
- [ ] 可运行 Runtime、runtime manifest、启动/停止/healthcheck 命令

预检是 `BPU_ESTIMATED`，不是 J6P 实测，也不能替代 A4 正式交付。

### B3：独立运行与硬件核验

- [x] 官方 X86 镜像 planner 时延与 30 分钟长稳
- [x] robust v3 自建留出行为复测、850 例数值仿真
- [x] FLOPs 复算、多模态消融、异常输入代理套件
- [ ] 对 A4 Final Runtime 和 exact RC 重跑 X86
- [ ] J6P latency、memory、stability、BPU 利用率/估算核验原始证据
- [ ] 明确 `X86_MEASURED`、`BPU_ESTIMATED` 与 `J6P_MEASURED`，不得混写

### B4：冻结、复现与提交

- [x] 预提交机读 inventory、全员台账和本收件清单
- [ ] 关闭全部上游 Gate 后登记唯一 RC
- [ ] 生成挑战赛道 `RELEASE_MANIFEST.json` 和文件级 `SHA256SUMS`
- [ ] 构建 Student/J6P Docker；现有基础赛道 Qwen Docker 不能替代
- [ ] 从干净 checkout 做独立复现并记录命令、退出码和差异
- [ ] 技术报告、演示视频、复现说明、许可文件和最终 README
- [ ] 在新目录解压最终 archive，再次核验路径、权限、SHA、PDF 和视频

## 建议暂存目录白名单

只有所有 Gate 完成后，B4 才在干净 checkout 中创建暂存目录。建议按以下类别收件，不能从
开发目录整包复制：

```text
challenge_submission_staging/
  README.md
  REPRODUCTION.md
  RELEASE_MANIFEST.json
  source/
  interfaces/
  data_manifests/
  models/fp32/
  models/int8/
  models/compiled_j6p/
  runtime/
  configs/
  evidence/b2/
  evidence/b3/
  docker/
  report/
  demo/
  licenses/
```

训练数据、Independent Validation 标签、缓存、旧候选模型、本机绝对路径、临时日志、
`__pycache__`、`.pytest_cache` 和未列入 manifest 的文件不得进入该目录。

## 收件完成判定

只有以下条件全部满足才允许把 staging 晋级为 Final：

- [ ] B2 FP32 Gate、A3 FP32 签发、B2 INT8 Gate 全部绑定同一权重/ONNX/INT8 identity；
- [ ] A4 compiled artifact 与 Runtime、B3 X86/J6P 证据绑定同一 RC；
- [ ] FLOPs 分母、多模态有效性、能力缺口和未测项在报告中有一致口径；
- [ ] Git 工作区干净，所有 Git 文件已推送且可从远端 exact commit 获取；
- [ ] 所有外置文件可按内容哈希取回，大小与 SHA 全部匹配；
- [ ] 干净环境复现通过；
- [ ] archive 外部 SHA 已生成，并在另一目录解压复验通过。
