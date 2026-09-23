# 查表捷径探针（B3 独立复现）

日期：2026-09-21。执行者：B3。产出：`shortcut_probe.json`。

## 目的

A3 的 `challenge/distillation/shortcut_probe.py` 报告 D2 Val 存在模板泄漏。B3 的职责是
**独立验证**，因此这份结论由 B3 用自己的实现从文件本身重新推导，而不是引用 A3 的结论。

## 命令

```powershell
py -3.12 -m challenge.hil.cli leakage-probe `
  --train challenge/dataset/releases/d2_v1_1/train.jsonl `
  --validation challenge/hil/frozen/d2_v1_1_val/cases.jsonl `
  --out challenge/hil/evidence/shortcut_probe_20260921/shortcut_probe.json
```

## 输入身份

| 文件 | SHA256 |
|---|---|
| `challenge/dataset/releases/d2_v1_1/train.jsonl`（2513 例） | `58ecab3bd48fedca82f7f399d2c6c39b3762c759669a1c1e24d01bad0cc11caf` |
| `challenge/hil/frozen/d2_v1_1_val/cases.jsonl`（539 例） | `42eec9c49162cb645930bd729f85a2c5545943667b59c5a5171d64affe55182f` |

## 结果（不含模型、不看 RGB）

| 指标 | 值 |
|---|---|
| 指令文本出现在 Train 中的 Val 用例 | **539 / 539（100%）** |
| `scenario_id` 出现在 Train 中的 Val 用例 | **539 / 539（100%）** |
| `(scenario_id, source_text)` 查表键命中 | **539 / 539（100%）** |
| 查表**恰好复现本例 Teacher 计划** | **505 / 539（93.69%）** |
| 查表键冲突（同键多个 Teacher 计划） | 34 |
| Val 内不同指令文本数 | **67**（539 例 → 每条指令平均 8.04 例） |
| Train 内不同指令文本数 | 88 |

判定字段 `verdict = LOOKUP_SHORTCUT_PRESENT`。

## 与 A3 结果的交叉核对

| 来源 | 用例数 | 指令文本重叠 | 查表复现 Teacher |
|---|---|---|---|
| A3 `shortcut_probe.py` | 489 | 489/489（100%） | 477/489（97.55%） |
| B3 本探针（冻结 Val） | 539 | 539/539（100%） | 505/539（93.69%） |

定性结论一致（Val 与 Train 不是模板/场景独立划分，存在无需 RGB 的查表捷径）。查表复现率
的差异（97.55% vs 93.69%）来自样本集合与查表键定义不同：A3 只用指令文本一类键，B3 用
`(scenario_id, source_text)`，并区分"键命中"与"复现 Teacher"。两个数字都保留，不合并。

## 限制与用途

- 这是**输入集质量事实**，不是 B3 对泄漏政策的判定；阈值与处置归 B2。
- 它不评价任何 Student 模型，也**不能**推出"某个 Student 靠查表过关"。
- 它限制的是**解读方式**：在 §7 的 Variant/Unseen 结论里，凡是落在被复用指令上的用例，
  行为匹配率都不能当作独立指令上的泛化证据；这已写入运行报告 §7.1 的
  `instruction_text_reused_groups` 提示。
- 冻结快照未做任何修改；本探针只读输入。
