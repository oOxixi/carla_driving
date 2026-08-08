# 数据集证据状态

审计日期：2026-08-08。本文只记录仓库中能够通过文件和哈希复核的事实，不把 Schema 示例、合成语音或缺少媒体的清单表述为正式数据集成绩。

## 当前结论

| 数据 | 仓库现状 | 可用于什么 | 当前不能证明什么 |
| --- | --- | --- | --- |
| CARLA 四模态压力集 | `artifacts/four_modal_0728/stress_set/cases_v2.jsonl` 有 320 条记录，来自 20 个 CARLA 0.9.16 `Town03_Opt` 源场景；320 个 RGB 和 20 个 LiDAR 文件存在且哈希匹配；源场景没有跨 train/val/test 泄漏 | RGB、LiDAR、车辆状态和决策契约回归 | 清单引用的 10 个音频文件未随数据集保存，验证器因此报告 320 条缺失音频；当前不能称为完整、可独立复现的四模态数据集 |
| 中文语音样本 | `voice_group/test_samples/manifest.json` 有 250 条，普通话、东北话、陕西话、粤语、台湾国语各 50 条；250 个 MP3 均存在 | 真实音频文件输入的 ASR/NLU 回归 | 音频由 Edge TTS 合成，不代表真实方言说话人或 50 dBA 噪声条件；标准文本单元测试不等于 ASR 准确率 |
| CARLA 语言基准 | `CARLA-Language-Benchmark` 有 6192 条冻结的指令/场景约束记录，SHA-256 为 `1bac08b5d389238db3e4f9cb171f390b06d0c81c3a58d54e1422edd7c1cd0f4a`，结构审计为 0 错误 | 语言覆盖、动作 Schema 和安全策略回归 | 它没有逐条 RGB、LiDAR、音频或物理闭环结果，不能当作 6192 个 CARLA 闭环场景 |
| 多模态 v1 | `datasets/multimodal_v1` 只有 Schema、数据卡模板和一条格式示例 | 统一 CARLA、NuScenes、Waymo 适配输出格式 | 示例媒体路径、哈希、模型版本和指标均为占位内容，明确设置为不可训练、不可计分 |
| NuScenes | 未发现实际样本、适配后记录、下载 revision、许可证清单或媒体哈希 | 暂无 | 不能声称已使用或验证 NuScenes 数据 |
| Waymo | 未发现实际样本、适配后记录、下载 revision、许可证清单或媒体哈希 | 暂无 | 不能声称已使用或验证 Waymo 数据 |

## 同源性证据

- CARLA 压力集按 `source_scene_id` 分组切分：train 208 条（13 个源场景）、val 80 条（5 个源场景）、test 32 条（2 个源场景），未发现同一源场景跨 split。
- 这些记录的图像、点云、车辆状态和标注来自同一 CARLA 源场景；曝光、模糊和遮挡是由源 RGB 确定性生成的派生版本，记录中保留源图和输出图哈希。
- 目前没有“训练数据记录 ↔ 83 个正式验收场景”的冻结映射，也没有证明 83 场景在调参后仍是独立测试集。因此只能证明压力集内部的分组切分，不能宣称全部验收场景满足训练/测试防泄漏。
- NuScenes/Waymo 尚未接入，因而不存在它们与 CARLA 场景的同源映射证据。

## 可复核命令

```powershell
# 6192 条语言记录：结构审计应为 0 错误
python CARLA-Language-Benchmark/tools/audit_global_benchmark_v1.py `
  CARLA-Language-Benchmark/datasets/final_benchmark/CARLA_language_benchmark_v1_normalized.json

# 250 条语音清单：文本意图/槽位回归
python -m pytest -q voice_group/tests/test_manifest_regression.py

# CARLA 四模态资产：当前预期失败，唯一已知原因是 10 个音频文件缺失
python tools/validate_four_modal_dataset.py `
  artifacts/four_modal_0728/stress_set `
  --output artifacts/four_modal_0728/stress_set/validation_report.json

# 这里只验证格式示例；不代表真实数据文件存在
python tools/validate_multimodal_dataset.py `
  datasets/multimodal_v1/examples/sample.jsonl
```

## 提交前必须补齐

1. 恢复四模态清单所引用的 10 个原始 MP3，并通过完整哈希验证；不能用不同音频替换后继续沿用旧哈希。
2. 冻结最终 CARLA 数据卡，记录采集配置、Git commit、CARLA 版本、许可证、train/val/test 场景 ID、媒体 SHA-256 和质量报告。
3. 冻结 83 个验收场景；之后不得根据 test 失败逐场景修改测试标签或阈值。若需要继续开发，应另建 development split，最终只对冻结 test 做一次正式验收。
4. 若技术方案声称使用 NuScenes 或 Waymo，必须先保存合法取得的代表性子集、版本/下载方式、许可证、适配记录和哈希清单；在这些证据出现前，技术方案只能写“格式已预留，尚未接入”。
