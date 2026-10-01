# B1 closeout 期发布与冻结校准的独立复核（2026-10-02）

> 复核对象是**他人的交付**，不是 B3 自己的测量结果：结论只有"文件与声明是否自洽"，
> 不涉及精度、性能或达标。

## 1. 五个 release 全部 PASS（B1 的形态在持续演化）

`00_all_releases.log`：B3 的发布校验器对 closeout 期的 5 个 release 逐个独立复核，
结果全部 **PASS**，但它必须处理三种通行证与两种完整性来源：

| release | 通行证 | 完整性来源 | 规模 |
|---|---|---|---|
| `d3_wave2_safe_short_v1` | `B1_SIGNED_PASS`（signed） | lock 文件 | 11 文件 / 374 图 / 318+56 行 |
| `d3_targeted_gap_strict_v1` | `B1_SIGNED_PASS`（signed） | lock 文件 | 672 文件 / 660 图 / 561+99 行 |
| `d3_turn_gap_60_strict_v1` | `B1_CONTENT_BOUND_PASS`（payload binding） | lock 文件 | 211 文件 / 200 图 / 171+29 行 |
| `d3_gap300_strict_v1` | `B1_CONTENT_BOUND_PASS`（**扁平声明**） | lock 文件 | 832 文件 / 820 图 / 697+123 行 |
| `b1_ms34_supplement_v1` | `B1_CONTENT_BOUND_PASS`（payload binding） | **`release_manifest.json:files`** | 9 文件 / 35 图 / 30+4+1 行 |

校验器因此做了两处泛化（都因为"跨 release 跑"才暴露）：

1. **ms34 没有 `b1_release_lock.sha256`**：原实现直接 `FileNotFoundError` 崩溃。
   现在改为按可用来源校验（lock → `release_manifest.json` 的 `files` 映射 → 都没有则报失败），
   并在输出里显式打印 `integrity: source=...`。
2. **gap300 的 content-bound 是扁平声明**（`attestation_type = CONTENT_BOUND_UNSIGNED` +
   `release_manifest_sha256`，没有 payload binding）。原实现把它当成"binding 不可读"而 FAIL。
   现在区分两种子形态：`payload_binding`（可复算 canonical JSON 摘要）与 `flat_attestation`
   （只声明清单摘要，明确记录"没有 payload binding，保证等级更低"）。

## 2. 冻结校准 `calibration_v1`：PASS，且与所有 val 划分零重叠

A2 正式 PTQ 必须用这份冻结校准，所以 B3 独立核验了它（`verify_calibration_package.py`）：

| 检查 | 结果 |
|---|---|
| 声明哈希 | **7/7 匹配**（`hashes.sha256`） |
| 样本数 | **300 例**（`calibration.jsonl`；manifest 未用我们识别的计数字段声明，报告为 `None`） |
| 与 6 个 val 划分的重叠 | **全部 0**：d2_v1_1 539 / d3_wave2 56 / targeted-gap 99 / turn-gap 29 / gap300 123 / ms34 4（合计 850 例 val） |
| 结论 | **PASS** |

**这条"校准与验证零重叠"是 B3 能为 A2 的正式 PTQ 提供的最直接保障**：只要 A2 用这份校准，
量化结果就不会因为校准集里混进了验证样本而被质疑。

（附带说明：`calibration_v1` 没有 PASS/lock 文件，只有 `hashes.sha256` + manifest，
所以它走的是一条独立于发布校验器的检查路径。）

## 文件

| 文件 | 内容 |
|---|---|
| `00_all_releases.log` | 5 个 release 的逐项复核输出（通行证形态、完整性来源、文件/图/行数、结论） |
| `01_calibration_v1_check.log` / `02_calibration_v1_check.json` | 冻结校准的独立核验（哈希、样本数、与 6 个 val 划分的重叠） |
