# 挑战赛道全员预提交台账（2026-10-07）

## 结论

本轮审计已覆盖远端 `challenge` 到 `197bc045`，并在 evidence merge `3ebd0682` 上完成
A2 robust v3 候选链路和分成员打包。A3 已发布新权重，B3 已补充 v3 仿真、OpenExplorer
预编译、FLOPs 复算和多模态消融；但没有新增 B2/A3 正式 Gate，也没有 J6P 板端结果。
当前适合做**预提交盘点与分成员收件**，不适合建立或命名 `final_submission/`。

本台账覆盖 A1、A2、A3、A4、B1、B2、B3、B4；机读版本见
`PRE_SUBMISSION_INVENTORY_20261007.json`。

## 当前最关键的新发现

### 1. robust v3 已到位，但 B2 readiness 仍有 7 项

使用仓库现有 B2 readiness 对
`a3_b1_closeout_robust_fp32_candidate_v3` 实跑，结果仍为 `BLOCKED`：

1. Independent Validation benchmark 未冻结；
2. case manifest 路径为空；
3. B2 formal policy 未冻结；
4. policy version 缺失；
5. slice minimum denominators 缺失；
6. multi-run merge rule 缺失；
7. B2 config 仍绑定旧 dataset version
   `b1_d2_v1_1_plus_d3_wave1_a3_strict_positive_v1`，与 robust v3 的
   `b1_governed_closeout_v1_a3_strict_positive_v1` 不一致。

第 7 项中的候选已更新为 robust v3，但 dataset version 仍是同一个 governed closeout
identity，因此结论不变。B2 必须更新并冻结配置、policy 和独立验证身份，同时明确如何处理
B1 已证明无法恢复的历史 template lineage。

### 2. A2 已完成 robust v3 候选量化

A2 已完成 300 样本导出一致性、Full INT8、25/25 敏感层、Mixed Top-3 和 1200 个
OpenExplorer NPY。Full INT8 SHA 为 `275dce5c...6c3`，Mixed SHA 为
`9a08a03c...32d3`；16 项量化测试全部通过。Mixed 改善三个离散输出头，但速度头 MAE
仍为 `0.207643 m/s`，所以不能直接定为最终模型。

### 3. B3 新证据既有进展，也暴露提交风险

- targeted-gap 行为匹配由 `0.9192` 升到 `1.0000`；
- `TURN_LEFT` 在 turn-gap 27/27、Gap300 108/108 仍失败；
- OpenExplorer 预检为 59/59 节点上 BPU、0 fallback，但只是 `BPU_ESTIMATED`；
- FLOPs 复算一致，但 Teacher 分母定义仍需团队冻结；
- 零值消融显示 state 主导，rgb/text/targets 均未引起 behavior argmax 翻转，存在
  “多模态融合有效性”评分风险；
- B3 使用的 FP32 ONNX SHA 为 `b76b5a32...08e5`，A2 本轮为
  `681a5d4b...4286`。两者虽绑定同一权重，字节身份不同，Final 前必须统一 exact ONNX。

## 全员收件状态

| 角色 | 当前可收材料 | 状态 | 最终提交前仍缺 |
|---|---|---|---|
| A1 | 结构、Params、FLOPs、接口文档；B3 已复算一致 | 可用但有口径限制 | 团队冻结 Teacher exact FLOPs/分母口径 |
| B1 | closeout、Calibration、Independent Validation identity、恢复证明 | 已有正式数据治理证据 | 配合 B2解决 template identity policy |
| A3 | robust v3 权重 `7f379c78...e805` 及训练证据 | Candidate | exact weights 的 B2 decision 与 A3 正式签发 |
| B2 | 评测代码与 Gate package 工具 | BLOCKED | 修正数据版本、冻结 case manifest/policy、运行并签发 |
| A2 | v3 FP32 ONNX、Full INT8、Mixed Top-3、OpenExplorer 输入和三份新包 | `DIAGNOSTIC_ONLY` | FP32 Gate 后正式重导出；随后取得 INT8 Gate |
| A4 | 初始文档、A2 预 Gate 大包、B3 v3 预编译证据 | PRE-GATE | 统一 exact ONNX；正式编译、fallback、Runtime、J6P evidence |
| B3 | 官方 X86 时延/长稳、v3 850 例数值仿真、FLOPs/消融 | 有诊断实测但非 Final RC/J6P | 对最终同一 RC 重跑 X86/J6P并核验 BPU 指标 |
| B4 | 规范文档 | PRE-FREEZE | Release Manifest、Docker、干净复现、最终包/报告/视频 |

## 现在可以整理、但不能混成 Final 的文件

### Git 内材料

- `challenge/` 下全部代码、配置、正式治理 manifest 和角色报告；
- `submission/challenge/` 本预提交台账；
- A2 v3 报告 `challenge/quantization/A2_ROBUST_CANDIDATE_V3_RESULT_20261007.md`；
- B3 v3 证据 `challenge/hil/evidence/a3_v3_simulation_20261007/`；
- B3 原始/派生证据必须保留原路径和 claim scope；
- A1 FLOPs 必须同时保留 counting convention 与 Teacher bound scope。

### Git 外大文件

- `.pt`、`.onnx`、`.hbm`、Docker archive、视频和大量 `.npy`；
- 使用内容哈希命名或单独台账，不通过改名表达 Gate；
- A2 当前三份外置包及 SHA 已登记在机读 inventory；
- `PRE_GATE_ONLY` 包只能进入团队 artifact storage，不能进入最终模型目录。

### 本轮可直接发给成员的 A2 外置包

本机目录：`artifacts/a2/handoff_20261007_3ebd0682/`。三份 ZIP 均已通过 delivery SHA、
ZIP CRC；A4 解包后独立校验为 1221/1221 文件匹配、0 error、0 warning。

| 接收方 | 文件 | 大小 | SHA256 | 用途 |
|---|---|---:|---|---|
| A3 | `A2_to_A3_gate_feedback_3ebd0682.zip` | 36,120 B | `03cac9f9...346a` | v3 量化反馈和 Gate 身份 |
| B2 | `A2_to_B2_evaluation_3ebd0682.zip` | 215,249,423 B | `95e05330...a59f` | exact weights、FP32/INT8 和治理证据 |
| A4 | `PRE_GATE_ONLY_A2_to_A4_openexplorer_3ebd0682.zip` | 153,934,913 B | `543a2ee2...3918` | 预编译、算子映射、fallback 与估算；非正式输入 |

旧 `handoff_20261006_3c10b121` 三包已被本轮 robust v3 包取代，只保留历史追溯，不能再作为
当前输入发送。

### 禁止收进 Final

- 旧候选和失败候选的大权重；
- `__pycache__`、`.pytest_cache`、本机绝对路径、临时日志和缓存；
- 随机初始化的 `challenge/student_v0_fp32.onnx` 作为最终模型；
- X86 数据冒充 J6P，BPU 估算冒充实测；
- 未冻结 Gate 的手工改名文件。

## 推荐收件顺序

1. **先收 B2**：冻结后的 config/policy、case identity、teacher/student raw predictions、Gate
   decision 及全部 SHA；同时收 A1/团队确认后的 Teacher FLOPs 分母口径；
2. **再收 A3/A2**：同一 weights SHA 的正式 FP32 manifest，并冻结唯一 FP32 ONNX SHA、
   INT8 SHA 与量化报告；
3. **再收 A4/B3**：只接受绑定上述 exact ONNX/INT8 的 compiled artifact、runtime、
   operator/fallback、X86/J6P 原始指标；
4. **最后收 B4 人工材料**：技术报告、复现说明、演示视频、Docker、最终 README；
5. 所有身份一致后才复制到只读 staging，生成 `RELEASE_MANIFEST.json`、文件级 SHA、archive
   外部 SHA，并在新目录解压复验。

## 你目前还能推进什么

- 先把本轮 A3/B2/A4 三包分别交付，并要求接收方回传“文件名 + SHA256 + 使用结论”；
- 继续按机读 inventory 收全员材料，重点催 B2 关闭 7 项 blocker、催 A1/团队冻结 FLOPs 分母；
- 要求 A4/B3 先解决 `681a5d4b...` 与 `b76b5a32...` 的 ONNX 身份差异，再做 Final RC；
- A2 技术侧暂无新的**正式**实验可跑：相同权重、相同 Calibration 的重复量化不会关闭 Gate；
- 可以继续准备目录白名单、外部大文件 SHA 台账和报告引用关系，但不要复制 Candidate 到 Final；
- B2/A3 对 exact weights 签发后，A2 立即进入正式 ONNX → INT8 → B2 INT8 Gate 链路。
