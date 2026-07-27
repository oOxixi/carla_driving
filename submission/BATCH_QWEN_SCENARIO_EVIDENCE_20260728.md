# Qwen 批测与三场景重复实跑（2026-07-28）

## 运行环境

- 服务器：`tiaozhansai`
- GPU：NVIDIA GeForce RTX 3090 24 GB，仅使用 GPU 0
- 模型：本地 `Qwen2.5-VL-7B-Instruct`
- CARLA：0.9.16，`Carla/Maps/Town03_Opt`
- 场景模式：真实 CARLA RGB/LiDAR 传感器，`sensor-profile=low`

本报告是本地冻结代理集和 CARLA 代表场景结果，不是主办方隐藏测试集结果。

## Qwen 冻结代理集

测试集：`datasets/qwen_proxy_v1/cases.jsonl`

- 样本：20 条；
- 覆盖：定速、停车、紧急停车、减速、起步、红灯冲突、前车 TTC、歧义目标和视觉无效；
- 图像：复用一张真实 Town03 RGB 帧；
- 上下文：冻结的代理场景标注；
- 模型在一次加载后连续推理，避免把模型加载时间计入每条生成延迟。

### 迭代结果

| 轮次 | 严格解析率 | 动作准确率 | 确认准确率 | 速度参数准确率 | 全合同准确率 |
|---|---:|---:|---:|---:|---:|
| round 1 | 95% | 90% | 50% | 90% | 45% |
| round 2 | 55% | 55% | 55% | 55% | 55% |
| round 3 | 100% | 100% | 100% | 100% | 100% |

前两轮失败均保留。主要问题和修复：

1. 中文 km/h 到 m/s 换算不稳定：在提示词加入确定性换算规则和基准值；
2. 明确停车、红灯安全停车被错误要求确认：明确安全停车无需确认，歧义/输入无效才确认；
3. Qwen 为 STOP/EMERGENCY_STOP 附带 `target_speed_mps=0`：边界仅允许并丢弃这一种安全等价冗余，非零速度仍拒绝。

round 3 生成延迟：

- mean：2384.975 ms
- P95：2889.691 ms
- P99：3938.786 ms
- max：4201.060 ms

限制：当前冻结输出 schema 不包含 `target_track_id`，并且本批复用了同一张 RGB 图像，因此目标关联准确率记为 `null`，不能用本结果声称视觉目标关联已达标。

证据：

- `artifacts/qwen_batch_0727/report_round1.json`
- `artifacts/qwen_batch_0727/report_round2.json`
- `artifacts/qwen_batch_0727/report_round3.json`
- 同目录保存三轮逐条控制台日志。

## 三场景重复实跑

运行矩阵：3 个场景 × 5 个 seed × 每 seed 4 次，共 60 次。

seed 扰动保持场景语义不变：

- S01/D03：固定拓扑筛选后的安全路线，沿路线改变 0/2/4/6/8 m 起点；
- D08：固定有效真实交通灯，初始停止线距离在基准值附近按 0.5 m 间隔变化。

| 场景 | 运行 | 成功 | 成功率 | 碰撞 | 闯红灯 | 关键指标 | 传感器→控制平均 | 观测最大 |
|---|---:|---:|---:|---:|---:|---|---:|---:|
| S01 定速 | 20 | 20 | 100% | 0 | 0 | 目标速度全部通过 | 1.170 ms | 5.966 ms |
| D03 前车制动 | 20 | 20 | 100% | 0 | 0 | 全批最小车距 4.852 m | 1.128 ms | 4.408 ms |
| D08 红灯冲突 | 20 | 20 | 100% | 0 | 0 | 全部在红灯前安全停车 | 0.787 ms | 6.773 ms |

最终证据：

- `artifacts/scenario_matrix_0727_final/scenario_matrix_report.json`
- 60 份逐次 `.summary.json`
- `artifacts/scenario_matrix_0727_final/evidence_manifest.sha256`
- 本机复核 64 个清单文件，SHA-256 失败数为 0。

开发阶段曾错误地把 seed 直接映射到任意 CARLA 出生点，导致 S01 seed 1 因道路前方障碍而停车并得 20/25。该失败证据保存在 `artifacts/scenario_matrix_0727_calibration/`，未删除，也未计入修正后的正式矩阵。

## 回归

- 完整自动化：384 passed，1 skipped；
- 被跳过项为需要显式在线 CARLA 的 smoke；
- 单独设置 `CARLA_SMOKE=1` 后：1 passed。

## 仍未由本批证明

- 多张、多目标真实 RGB 的目标关联准确率；
- Qwen 在不同天气、光照和摄像机画面上的视觉泛化；
- 30 分钟持续运行中的 FPS、掉帧、GPU 显存和恢复统计；
- 主办方隐藏测试集成绩。
