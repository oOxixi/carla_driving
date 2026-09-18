# 入库说明：`b3_hil/` → `challenge/hil/`（历史记录）

> 本文件记录入库过程，**入库动作已完成**，因此以下内容是历史记录而非待办。
> 当前实际状态以 `README.md` 为准。

本工作区最初独立开发在仓库外（避免与 A 组代码互相干扰），后来按下表迁入仓库，
代码本身没有改写逻辑，只改了模块路径。

## 1. 目录映射

```text
D:\nana\b3_hil\                     →  challenge/hil/
├── b3_hil/                         →  challenge/hil/            （包内容上移一层）
├── latency_schema.md               →  challenge/hil/
├── hardware_metrics_schema.md      →  challenge/hil/
├── a4_runtime_contract.md          →  challenge/hil/
├── hard_cases_handoff.md           →  challenge/hil/
├── requirements.txt                →  challenge/hil/
└── schemas/                        →  challenge/hil/schemas/
```

以下内容**不入库**（属于本地运行产物，仓库已把 `artifacts/` 排除在 Git 外）。
实际入库时只取了清单里的一小部分策展证据放进 `challenge/hil/evidence/`：

```text
runs/            全部运行历史（含被取代与作废的运行）→ 留在仓库外的工作区
  └─ 每次只取 1 次主测量 + 1 次长稳 →  challenge/hil/evidence/<日期>/
     （当前为 x86_prevalidation_20260918；旧批次在产物或代码变更后已移出仓库）
contract_checks/ 契约检查报告 → 未入库
.pytest_cache/
__pycache__/
```

`frozen/` **已入库**：早期 `smoke_v0_snapshot`（30 例）与当前 `d2_v1_1_val`
（539 例，B1 D2 v1.1 的 val 划分），都是复现实验所需的输入基线，体积可接受
（合计约 4.9 MB）。

## 2. 迁移时需要改的地方

| 位置 | 改动 |
|---|---|
| 包目录名 | `b3_hil/` → `hil/`，导入路径从 `b3_hil.xxx` 变为 `challenge.hil.xxx` |
| 包内导入 | 全部是相对导入（`from .stages import ...`），**不需要改** |
| 测试导入 | 同样是相对导入（`from ..stages import ...`），**不需要改** |
| 命令行 | `python -m b3_hil.cli` → `python -m challenge.hil.cli` |
| 文档示例 | 把示例命令里的 `b3_hil` 换成 `challenge.hil` |
| `challenge/hil/__init__.py` | 已存在（即现在的 `b3_hil/b3_hil/__init__.py`） |

没有任何对 A 组文件的修改：`challenge/student/`、`challenge/planner/`、
`runtime/` 均保持原样，B3 只 import。

## 3. 入库后的自检

```powershell
py -3.12 -m pytest -q challenge/hil/tests
py -3.12 -m challenge.hil.cli selftest
py -3.12 -m challenge.hil.cli schema --out challenge/hil/schemas
```

期望：测试全绿（当前 52 项），`selftest` 返回 `PASS`。

## 4. 提交前检查

- [ ] `challenge/hil/` 下不含 `__pycache__` 与运行产物
- [ ] `requirements.txt` 与 `challenge/requirements.txt` 无冲突项
- [ ] `latency_schema.md` 与 `hardware_metrics_schema.md` 中"待 A4/B2 确认"的
      标注保持原样（未确认前不得删）
- [ ] 报告模板里的 `X86_PRE_VALIDATED` / `J6P_PENDING` 守卫逻辑未被绕过
- [ ] 没有把 `runs/` 里的样本数据当作仓库文件提交
