# 远端分支归并记录（2026-09-07）

## 主线选择

新的 `main` 以 `scene_organized` 为基线。该分支是旧 `main` 的后代，已完整包含 `scene`
的正式三场景、2B 全链、长路线控制、成员2场景泛化和成员1路线泛化，同时已经删除历史
delivery、副本实现和大批运行产物。

随后吸收以下仍然独有且可验证的内容：

- `generalization`：速度、曲率、Actor 类型和传感器状态驱动的控制/安全策略；
- `carla_driving_rstar`：成员4 S3 应急证据链、正式场景闭环稳定修复、Linux CARLA
  `memoryview` 图像兼容和转弯计划超时修复；
- `new` / `verify_new_fix`：组合指令进入 Qwen 慢路径、相对速度语义解析及对应测试。

## 全部分支结论

| 远端分支 | 处理 |
|---|---|
| `main` | 作为共同历史保留，并由本次整理后的版本更新 |
| `scene` | 已由 `scene_organized` 完整包含 |
| `scene_organized` | 作为最新场景与路线基线完整吸收 |
| `generalization` | 完整合并，冲突按“路线新逻辑 + 参数化策略”组合解决 |
| `carla_driving_rstar` | 吸收独有 S3、稳定性和 Linux 运行修复；成员2旧版生成逻辑由更新的 `9a4747d` 替代 |
| `new` | 吸收两个 NLU 源码提交，不重复导入生成数据 |
| `verify_new_fix` | 源码已由 `new` 吸收；仅改变冷启动阈值的测试和过期交接文档不进入主线 |
| `8.9` | 不合并旧 runner/可视化副本和约 30 MB 录屏；当前 `tools/live_carla_viewer.py` 是统一实时画面入口 |
| `8.4-xky-3B` | 不合并 3B 运行时、权重结果和旧 runner；当前正式模型限定 2B |
| `feat/group1-task3-data-split` | 不提交约 30 万行可再生 split/审计输出；生成工具和结果仍保留在原分支历史 |
| `7.25`、`without-Qwen`、`without-modification` | 均为当前 `main` 的祖先，已有价值实现已在共同历史中 |
| `feat/A-runtime-closure-0723`、`feat/day23-qwen-finalization` | 均已被当前运行主链覆盖 |
| `team2A` | 已由旧 `main` 的整合历史包含 |

## 未回灌的数据

以下内容不是当前运行源码，因此只保留在原分支或 Git 历史：录屏视频、逐帧 JSONL、
临时 benchmark、日期命名 delivery、3B/7B 结果、模型下载物、重复数据 split，以及没有
训练记录和独立评测的备用 LoRA。当前仓库只保留生产 LoRA、6192 条冻结语言回归集、
小型可复现样本和生成/审计工具。
