# 挑战赛道全员预提交台账（2026-10-07）

## 结论

远端 `challenge` 最新提交为 `254e84ab`，没有新的 A3/B2/A4 正式交付。当前适合做
**预提交盘点**，不适合建立或命名 `final_submission/`。A2 候选链路已经完成，正式链路仍由
B2/A3 Gate 阻塞。

本台账覆盖 A1、A2、A3、A4、B1、B2、B3、B4；机读版本见
`PRE_SUBMISSION_INVENTORY_20261007.json`。

## 当前最关键的新发现

使用仓库现有 B2 readiness 对最新 A3 v2 package 实跑，结果为 `BLOCKED`，共有 7 项：

1. Independent Validation benchmark 未冻结；
2. case manifest 路径为空；
3. B2 formal policy 未冻结；
4. policy version 缺失；
5. slice minimum denominators 缺失；
6. multi-run merge rule 缺失；
7. B2 config 仍绑定旧 dataset version
   `b1_d2_v1_1_plus_d3_wave1_a3_strict_positive_v1`，与 A3 v2 的
   `b1_governed_closeout_v1_a3_strict_positive_v1` 不一致。

因此目前不是“A2 再跑一次量化”能解决的问题。B2 必须先更新并冻结自己的配置、policy 和
独立验证身份，同时处理 B1 已证明无法恢复的历史 template lineage。

## 全员收件状态

| 角色 | 当前可收材料 | 状态 | 最终提交前仍缺 |
|---|---|---|---|
| A1 | 结构、Params、FLOPs、接口文档 | 可用但有口径限制 | Teacher exact FLOPs/分母口径最终确认 |
| B1 | closeout、Calibration、Independent Validation identity、恢复证明 | 已有正式数据治理证据 | 配合 B2解决 template identity policy |
| A3 | 最新 v2 权重及训练证据 | Candidate | exact weights 的 B2 decision 与 A3 正式签发 |
| B2 | 评测代码与 Gate package 工具 | BLOCKED | 修正数据版本、冻结 case manifest/policy、运行并签发 |
| A2 | FP32 ONNX、Full INT8、Mixed Top-3、OpenExplorer 输入 | `DIAGNOSTIC_ONLY` | FP32 Gate 后正式重导出；随后取得 INT8 Gate |
| A4 | X86 runtime、初始 operator 文档、预 Gate 大包 | BLOCKED | 正式编译、fallback、compiled artifact、J6P runtime |
| B3 | 官方 X86 镜像内时延与 30 分钟长稳 | 有实测但非 Final RC/J6P | 对最终同一 RC 重跑 X86/J6P并核验 BPU 指标 |
| B4 | 规范文档 | PRE-FREEZE | Release Manifest、Docker、干净复现、最终包/报告/视频 |

## 现在可以整理、但不能混成 Final 的文件

### Git 内材料

- `challenge/` 下全部代码、配置、正式治理 manifest 和角色报告；
- `submission/challenge/` 本预提交台账；
- B3 原始/派生证据必须保留原路径和 claim scope；
- A1 FLOPs 必须同时保留 counting convention 与 Teacher bound scope。

### Git 外大文件

- `.pt`、`.onnx`、`.hbm`、Docker archive、视频和大量 `.npy`；
- 使用内容哈希命名或单独台账，不通过改名表达 Gate；
- A2 当前三份外置包及 SHA 已登记在机读 inventory；
- `PRE_GATE_ONLY` 包只能进入团队 artifact storage，不能进入最终模型目录。

### 禁止收进 Final

- 旧候选和失败候选的大权重；
- `__pycache__`、`.pytest_cache`、本机绝对路径、临时日志和缓存；
- 随机初始化的 `challenge/student_v0_fp32.onnx` 作为最终模型；
- X86 数据冒充 J6P，BPU 估算冒充实测；
- 未冻结 Gate 的手工改名文件。

## 推荐收件顺序

1. **先收 B2**：冻结后的 config/policy、case identity、teacher/student raw predictions、Gate
   decision 及全部 SHA；
2. **再收 A3/A2**：同一 weights SHA 的正式 FP32 manifest、正式 ONNX、INT8 与量化报告；
3. **再收 A4/B3**：compiled artifact、runtime、operator/fallback、X86/J6P 原始指标；
4. **最后收 B4 人工材料**：技术报告、复现说明、演示视频、Docker、最终 README；
5. 所有身份一致后才复制到只读 staging，生成 `RELEASE_MANIFEST.json`、文件级 SHA、archive
   外部 SHA，并在新目录解压复验。

## 你目前还能推进什么

- 可以继续维护这份全员台账、收集外置大文件 SHA，并催 B2按 7 项 blocker 逐项关闭；
- 可以先设计最终目录白名单和报告引用关系，但不要复制 Candidate 到 Final；
- A2 技术侧暂无新的正式实验可跑：相同权重、相同 Calibration 的重复量化不会关闭任何 Gate；
- 一旦 B2/A3 对 exact weights 有新提交，A2 即可进入正式 ONNX → INT8 → B2 INT8 Gate 链路。
