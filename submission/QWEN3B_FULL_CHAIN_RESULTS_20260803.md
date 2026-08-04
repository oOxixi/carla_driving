# Qwen2.5-VL-3B 数据修复与真实全链结果

日期：2026-08-03
范围：服务器本地 `carla-driving-3B`，未提交或推送 GitHub。

## 结论

已修复旧采集器在无相邻车道时，把 `far_ahead` 行人错误描述成“右侧相邻车道行人”的问题。新建的 v3 数据集保留旧证据不变，并记录了 2 条源记录迁移、16 条派生记录受影响。正式 `cases_v2.jsonl` 共 320 条，目标标签一致性为 280/280，冲突为 0。

Qwen 单模块重新实测 320/320 全部通过。真实全链 `合成TTS音频 -> SenseVoice/NLU -> RGB+CARLA LiDAR摘要+车辆状态 -> Qwen3B -> 严格目标绑定 -> D安全仲裁 -> 最终控制` 也达到 320/320 READY，完整契约准确率 100%。

当前完整链路 P95 为 264.07 ms，达到 150--500 ms 部分得分区间，但未达到比赛 150 ms 满分档。

## 数据完整性

| 指标 | 结果 |
|---|---:|
| 总样本 | 320 |
| 可回答目标样本 | 280 |
| 目标缺失安全故障样本 | 40 |
| 目标标签一致性 | 280/280 = 100% |
| 标签冲突 | 0 |
| RGB 文件 | 320 |
| LiDAR 文件 | 20 |
| 合成音频文件 | 10 |
| train / val / test | 208 / 80 / 32 |
| 跨 split 场景泄漏 | 0 |
| 文件/Schema校验错误 | 0 |

音频为 `zh-CN-XiaoxiaoNeural` 合成音频，只用于真实ASR回归，不可作为真人方言或50 dB噪声证据。

## Qwen 单模块320条重跑

| 指标 | 结果 | 门槛 | 判定 |
|---|---:|---:|---|
| strict parse | 100% | 100% | 通过 |
| action accuracy | 100% | >=98% | 通过 |
| target association | 100% | >=98% | 通过 |
| all-contract accuracy | 100% | >=98% | 通过 |
| mean | 207.99 ms | 记录 | - |
| P95 | 267.50 ms | <=300 ms模型门禁 | 通过 |
| P99 | 275.68 ms | 记录 | - |
| max | 1525.80 ms | 记录冷启动长尾 | - |

## 真实全链320条结果

| 指标 | 结果 | 门槛 | 判定 |
|---|---:|---:|---|
| READY | 320/320 = 100% | 100% | 通过 |
| ASR exact accuracy | 100% | >=95%基础线 | 通过 |
| voice command valid rate | 100% | >=95% | 通过 |
| answerable semantic accuracy | 100% | >=98% | 通过 |
| answerable joint accuracy | 100% | >=98% | 通过 |
| deterministic target association | 100% | >=98% | 通过 |
| missing-target fail-closed | 40/40 = 100% | 100% | 通过 |
| full-chain contract accuracy | 320/320 = 100% | >=98% | 通过 |

模型按当前安全架构只生成 `A/B/C/D/E` 动作码，不直接生成目标ID，因此报告中的 `raw_qwen_target_association_accuracy=0` 是接口设计结果，不是目标关联失败。目标ID由语音语义和结构化感知确定性绑定，280/280正确，并全部经过严格边界复核。

### 延迟

| 阶段 | mean | P50 | P95 | P99 | max |
|---|---:|---:|---:|---:|---:|
| SenseVoice + NLU | 115.78 ms | 109.12 ms | 150.88 ms | 169.43 ms | 220.19 ms |
| Qwen3B + 图像处理/边界 | 108.68 ms | 107.02 ms | 119.75 ms | 124.72 ms | 634.25 ms |
| Qwen后控制与安全仲裁 | 0.24 ms | 0.21 ms | 0.41 ms | 0.54 ms | 0.76 ms |
| 音频到最终控制 | 224.70 ms | 217.46 ms | 264.07 ms | 309.68 ms | 759.29 ms |

比赛端到端150 ms满分档当前未通过；P95处于150--500 ms部分得分档。模型服务本身通过300 ms早停门禁。

## 环境与限制

- GPU 0：RTX 3090 24GB；Qwen2.5-VL-3B BF16/vLLM/CUDA 13.0。
- 模型 revision：`66285546d2b821cf421d4f5eb2576359d3770cd3`。
- SenseVoice真实推理启用；条件式 Faster-Whisper 校验器未启用，因为服务器无法连接其模型下载地址。不得宣称双ASR验证已完成。
- 本报告是离线四模态决策/控制全链；每条记录没有单独驱动物理CARLA actor，正式三场景物理闭环证据需另行提交。
- 尚未完成3B路线30分钟连续稳定性测试。

## 证据

- `artifacts/B_role_validation/qwen25vl_3b_frozen320_label_integrity_v3.json`
- `artifacts/B_role_validation/qwen25vl_3b_bf16_3090_frozen320_v5_repaired.json`
- `artifacts/B_role_validation/qwen25vl_3b_bf16_3090_frozen320_v5_repaired.log`
- `artifacts/four_modal_0803_3b/dataset_validation_v3.json`
- `artifacts/four_modal_0803_3b/full_chain_report_v3_final.json`
- `artifacts/four_modal_0803_3b/full_chain_run_v3_final.log`
- `artifacts/four_modal_0803_3b/stress_set_v3/dataset_report.json`

定向代码回归：9 passed。
