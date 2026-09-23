# A3 D2+D3 累积数据准备结果

核对日期：2026-09-24。服务器代码提交：
`c47c638ea2f7eeeac8bd969e600e5fcdf1857483`。本页记录数据接入和有界训练链健康，
不记录正式模型准确率，也不代表 B2 独立 Validation 或 Frozen Test 通过。

## 固定身份

- 视图版本：`b1_d2_v1_1_plus_d3_wave1_a3_strict_positive_v1`
- D2 release SHA256：`cf153d2f536f9180241f02a9d644aca6da2a508beb785591399dbb75b847462f`
- D3 release SHA256：`dcd1bd1d0a34683e62e70a206760e691c0cd04b779f063d58a1fcf98837554bd`
- D3 B1 签名 SHA256：`10d9892551dbfe4e61377f9f835bd89d8043209f32a459ab92028ee1d93c7228`
- 源证据摘要：`6ec35d771df36b63864efd3c3e06f9a0ab2991bd53a60f44740cf19a0f7fe827`
- 累积视图 manifest SHA256：`e07112b52ae8ecf8dd944d562e30304478fc8c22ef9cb86f4585181281fc2ff9`
- Teacher：`Qwen/Qwen3.5-2B`，revision
  `15852e8c16360a2fea060d615a32b45270f8a8fc`，artifact fingerprint
  `4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa`

## 已通过门禁

| 门禁 | 结果 |
|---|---|
| D3 detached signature / lock / integrity / Teacher v4 | PASS |
| RGB 全量逐图检查 | D2 3592 + D3 2363，PASS |
| 累积严格正样本 | Train 4079 / Val 797，0 sample/group overlap |
| 排除审计 | 共 539；D3 hard negative 308 条未进入普通监督 |
| 全量 preflight | 4876/4876，0 error，0 warning |
| A1 四模态 packer | Train 4079/4079、Val 797/797，153 batches，0 error |
| 自动化回归 | 82 tests PASS；累积门禁/晋级/交接专项 42 tests PASS |
| CUDA integration smoke | 50 Train + 50 Val、2 updates，完成且状态为 `MOCK_ONLY` |
| 同 seed 重复性 | candidate 与 best-checkpoint 两次 SHA256 分别完全一致 |

重复 Smoke 的 candidate SHA256 为
`4344553d22a77f650ded976110e7cc2da578b89e2ad279b401758d42bf4a7cd8`，best checkpoint
SHA256 为 `e3518174223e461435acb6bda1e24e26ad6ecedc70a2d24bf472b9ec11d4eac2`。
这些文件只证明数据到 loss/backward/checkpoint 的链路稳定；不得交给 A2/A4/B3，也不得
改名为正式 FP32 权重。

## 数据分布事实

全量 preflight 的 Train 风险类别为 normal 3177、complex 676、safety-critical 226；
Validation 为 normal 571、complex 177、safety-critical 49。计划长度仍只有 1～2 步，
本次接入没有提供三步或四步监督。行为集合中仍缺少独立泛化评价所需的部分能力覆盖，
因此 D3 Val 只允许 development model selection。

## 下一步

1. 使用 `d2_d3_cumulative_formal_config.yaml` 运行正式多 epoch FP32 训练；不要复用 Smoke
   输出目录。
2. 比较 D2-only 基线与 D2+D3 的逐 Head、风险分层和 hard-case 指标；低收益或退化时先
   查分布与权重，不盲目增加 epoch。
3. 正式候选继续保持 `PENDING_A3_FP32_GATE`，交给 B2 的同一冻结独立 Validation 包做
   Teacher/Student 配对评价。
4. 在 B2 返回 hash-bound 证据前，不运行真实 promotion，也不宣称泛化通过。
