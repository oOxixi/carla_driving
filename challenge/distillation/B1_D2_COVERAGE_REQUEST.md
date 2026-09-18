# 给 B1 的 D2 v1.1 后续补采请求（A3 标签覆盖审计）

审计基线：B1 签发包 `challenge/dataset/releases/d2_v1_1/`；A3 派生视图
`b1_d2_v1_1_a3_strict_positive_v1`。报告由
`python -m challenge.distillation.audit_d2_view` 生成，存放在
`artifacts/a3_d2_prep/label_coverage.json`。本文件是下游需求，不改 B1
签发的 Train/Val/Reserved，也不代替 B1 的采集和划分决定。

## 已核实的缺口

| 切片 | A3 Train | A3 Val | 请求 |
| --- | ---: | ---: | --- |
| 严格正样本总量 | 2332 | 489 | 合计 2821，距 D2 建议下限 3000 至少差 179 条新的有效正样本 |
| 安全关键 | 142 | 34 | 增加独立 group 的 Val，尤其是紧急/行人类；由 B2 决定最终评测所需分母 |
| `safety_D` × 安全关键 | 10 | 1 | Val 唯一一条为 `SUP_A08_fast_pedestrian`；优先补不同 scenario/route/seed，不可复制这一条 |
| `Town03_Opt` | 1 | 0 | 若该地图是目标部署范围，需要独立 Val group；当前不能声称地图泛化 |
| 3 步 / 4 步 Teacher plan | 0 / 0 | 0 / 0 | 先确认 Teacher 与闭环是否能产生真实有效计划；不可把 1–2 步硬拆或填充当监督 |
| `YIELD` / `PULL_OVER` / `HOLD` Behavior | 各 0 | 各 0 | 先确认三者是可训练的正常决策还是安全回退/保留类别，再决定是否补真实样本 |
| 相对 Train 未见的指令文本 / scenario ID | — | 0 / 0 | 当前 Val 489/489 的精确指令文本与 scenario ID 都已出现在 Train；下一发布需给 B2 留真正的未见模板/场景组 |

上述切片可能重叠，不能将各行需求简单相加。建议将 30 条作为**初步统计观察的最低切片量**，不是比赛规定的通过线，也不足以证明高准确率；B2 应给出独立评测所需分母和置信区间。补采总量必须以新发布经 A3 严格规则保留的正样本计算，不能只按原始 Teacher 请求数计算。

## B1 交付要求

1. 继续使用正式 pinned `Qwen/Qwen3.5-2B`、revision `15852e8c16360a2fea060d615a32b45270f8a8fc` 和已核对的模型 fingerprint；实际 RGB、ModelRequest V1、ManeuverPlan V2、闭环质量与目标指针均要完整。
2. 新样本优先覆盖上表薄弱切片，但只接收真实 Teacher 输出及可追溯闭环，不能复制、改标签、改终态或人工拼接计划来补数字。失败运行/安全覆盖仍单独保存为 hard cases，不进入普通正确规划监督。
3. 用新的 release 版本签发 JSONL、RGB、图像/文件哈希、provenance 和 group-aware Train/Val 划分；`d2_v1_1` 保持不可变。新 Val 的 scenario family、map、route hash、seed 与 Train 隔离；Reserved/Frozen Test 不交 A3 调参。
   当前 group-aware 划分只隔离 route/seed，尚未隔离**指令文本模板与 scenario ID**。请另标记一个由 B2 保管的 template/scenario-disjoint 评测组；不要通过将现有 Val 的同模板样本重新命名来制造“未见”。若从现有数据重划，必须发布新版本、重新审计 RGB/哈希和 group overlap，且不能把已用于 A3 调参的样本宣称为盲测。
4. 附每个薄弱切片的原始采样数、严格正样本保留数、排除原因、Train/Val 数和 group 数。若某标签或 3–4 步计划在当前 Teacher/场景契约下不可自然获得，请明确记录“未覆盖/不可采”，交 A1/B2 共同决定模型能力边界，不以伪标签替代。

## A3 收到新 release 后的验收

先验证 B1 新 release 签名、RGB 和 split，再派生 A3 正样本视图、运行完整 preflight 与覆盖审计。比较新旧版本的每个切片及来源，不跨版本混报准确率；之后再冻结 Train/Val manifest 开展并行 loss/采样实验。B2 的独立测试集仍不参与 A3 选择权重。
