# A1 交接包独立复核（B3，2026-10-08）

对上游 `A1_正式模型与FLOPs交接_20261008`（提交 `ca5cb179`）的**独立复核**。
A1 的 README 与仓库内副本逐字节一致（9,909 B），因此以下结论针对的就是上游那一版。

## 复核结果

| 检查 | 命令 | 结果 |
|---|---|---|
| 包完整性 | `py -3.12 verify_manifest.py` | **PASS：201 个文件全部匹配** |
| FLOPs 选项表复算 | `py -3.12 -m challenge.export.flops_options --output ...` | **与发布文件逐字节一致**（sha256 `27e7e2da…`） |
| Student 算量复算 | `py -3.12 -m challenge.export.compute_flops --output ...` | 参数 23,006,581、FLOPs 498,640,896 —— 与发布值一致；唯一差异字段是 `source_git_sha`（复算发生在 B3 的 HEAD，属溯源字段） |
| Teacher 侧数值 | 由选项表读出 | conv/linear 892,929,605,632；扩展主算子 911,695,101,952；**整网精确总量记为 null**（不编造） |

## 四个候选口径（A1 提供，B3 复核）

| 候选原始模型 / 范围 | 分母 | 比值 | 若被认可的条件档位 |
|---|---:|---:|---|
| 固定 Teacher Qwen3.5-2B，Conv/Linear（267 prefill token / 64 视觉 token） | 892,929,605,632 | **0.0005584325** | ≤0.5 → **15 分档** |
| 同上 + 密集注意力 QK/AV + gated-delta 递推 | 911,695,101,952 | 0.0005469382 | ≤0.5 → 15 分档 |
| 同结构 FP32 学生（Conv/Linear） | 498,640,896 | 1.0 | >0.9 → 无档位分 |
| 同结构 FP32 学生（完整 forward 抽象算量） | 499,437,133 | 1.0 | >0.9 → 无档位分 |

**B3 的读法**：

* **数据侧已经齐了**：学生的 498,640,896 与我们此前独立复算的 `challenge/flops_report.json` 完全一致；
  教师分母已从"旧的 28 层通用下界"换成"固定 Teacher 的实配复算"；两者在同一模型内 Conv/Linear 口径下可比；
* **仍未决的是口径选择**（四个选项中选哪一个作为正式分母）——包内 `formal_ratio_pass` 仍为 `null`，
  A1 也明确写了"条件档位不等于评委已批准"；
* **重要提示**：初审整理包记录的候选模型是 **Qwen3.5-2B（与固定 Teacher 同 revision）**，
  因此"相对初赛模型"这一读法应落到**上表前两行**，而不是比值为 1.0 的两行。

## 由此更新的材料状态

`results_and_gaps.md` §0/§2.10 的 FLOPs 行已改为"数据齐、分母选项已由 A1 给出（0.000558，15 分档；另一口径 1.0）"，
等团队选定后再定稿数字。

## 复现

```powershell
cd A1_正式模型与FLOPs交接_20261008
py -3.12 verify_manifest.py
py -3.12 -m challenge.export.flops_options --output reproduced_flops_options.json
py -3.12 -m challenge.export.compute_flops  --output reproduced_student_flops.json
```
