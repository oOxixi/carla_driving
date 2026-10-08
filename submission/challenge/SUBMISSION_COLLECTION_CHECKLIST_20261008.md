# 挑战赛道最终收件清单（2026-10-08）

## 候选与 Gate

- [x] 冻结 V3 为当前唯一候选，权重 SHA `7f379c78...6e805`
- [x] 锁定 A2 FP32 ONNX SHA `681a5d4b...b4286`
- [x] 完成 240/240 条一次性回放并锁定 raw predictions SHA
- [x] 如实冻结本轮阈值投影为 `FAIL`
- [x] 实现 Adapter V3.1 固定语义合同，并保留路口/车道/安全间隙 fail-closed 门禁
- [x] V3.1 FP32 在旧 240 条上完成回归投影：238/240 完整计划、28/28 安全召回，`PASS`
- [x] Full INT8 与 Mixed Top-3 完成同口径诊断：均与 FP32 核心字段 240/240 一致
- [ ] B1/B2 提供新的 template-valid、未暴露独立基准
- [ ] B2 冻结 formal policy，独立评估 exact weights+ONNX+Adapter V3.1 并签发 FP32 decision
- [ ] 正式 FP32 PASS 后由 A2 将首选 Mixed Top-3（Full 为备选）重签正式 INT8 manifest
- [ ] B2 在同一冻结基准上签发 INT8 decision

## 可计入预提交的仓内证据

- [x] A1 正式结构、接口、Student/Teacher FLOPs 复算包
- [x] B1 closeout、Calibration v1、Independent Validation v1 与泄漏检查
- [x] A3 robust v3 训练证据和 handoff manifest
- [x] A2 量化代码、配置、报告和外置包哈希
- [x] B3 83 场景闭环、850 例衰减、BPU 估算、FLOPs 交叉核对
- [x] B3 本机 Teacher 完整计划路线 A 否证（42.3–58.2 s/次、严格解析 0/4）
- [x] V3 240 条 role-exception 诊断总结与外置 raw predictions 哈希
- [x] V3 `null/CURRENT` 字段语义归一化并行诊断（lane 89.31%、sequence 86.67%，仍 FAIL）
- [x] Adapter V3.1 实际回放与 Full/Mixed INT8 三方诊断（旧集投影 PASS，明确非正式 Gate）
- [x] 重建 A3/B2/A4 三份 V3.1 交接 ZIP；CRC 与逐成员 SHA256 全部 PASS
- [x] 生成 V3.1 全赛道小型证据包与源码/Runtime 预览包；CRC 与逐文件 SHA256 全部 PASS

## 必须继续收集的原件

- [ ] B2 正式 benchmark/policy manifest、Teacher/Student raw predictions、Gate decision package
- [ ] A3/B2 对 exact V3 weights、FP32 ONNX、Adapter commit 的复合候选签发正式 manifest
- [ ] A2 同一候选正式 FP32 ONNX、INT8 ONNX、`int8_manifest.json`、量化误差报告
- [ ] A4 与 A2 exact SHA 一致的 `.bc/.hbm`、YAML、operator mapping、fallback report、Runtime
- [ ] B3 Final RC X86 与 J6P latency/memory/stability/utilization 原始证据
- [ ] Bench2Drive 复现工程或记录
- [ ] 真实语音完整链路工程包、日志和演示录制
- [ ] 如要求消除跨机器注脚：同机 Teacher/Student 正式复现（必须声明选择式与完整计划式口径差异）
- [ ] Student/J6P Docker archive 及 SHA256
- [ ] 技术报告 PDF、演示视频、许可文件和完整 README
- [ ] 干净 checkout 复现报告与新目录解压复验记录

## 收件强制字段

每个原件必须登记：负责人、相对路径、字节数、SHA256、完整 Git SHA、模型/数据/
配置/Runtime 身份、环境指纹、生成命令、claim scope 和原始结果路径。下列情况
一律不收进 Final：

- Candidate 改名冒充 Gate PASS；
- BPU 估算冒充 J6P 实测；
- X86 结果冒充板端结果；
- 哈希与 active RC 不一致；
- 缺 SHA/缺 manifest/缺来源；
- 包含训练数据、Independent Validation 标签、缓存、旧候选、本机绝对路径或临时日志。

## Final 晋级判定

仅当上述所有未完成项全部关闭，且 FP32→INT8→A4/B3→B4 全链路绑定同一
RC 身份时，才允许生成 `RELEASE_MANIFEST.json`、`FINAL_SUBMISSION/` 和最终归档包。
