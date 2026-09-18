# CARLA 链路覆盖 · 多轮重复 · 稳定性窗口（2026-09-18）

**可信范围**：`CARLA_CHAIN_ONLY_NO_STUDENT` —— 链路级验证，**不含 Student，也未接 Qwen**
（本轮 `qwen_status = DISABLED`，走场景自带命令）。

三个子批次共 **37 次场景运行，全部 `SUCCEEDED`**，用于证明 A/B/C/D 链路与安全仲裁在多场景、
多轮次、连续运行下都稳定。

## 三个子批次

| 子目录 | 内容 | 运行数 | 结果 |
|---|---|---:|---|
| `coverage/` | smoke 5 个 + `safety_D` 8 个，各 1 次 | 13 | **13/13 成功** |
| `multiround/` | S01、S04、D01，同配置各 3 轮 | 9 | **9/9 成功** |
| `stability/` | smoke 全套 5 个，各 3 轮，连续 7.1 分钟 | 15 | **15/15 成功** |

三轮合计：**0 碰撞、0 闯红灯、0 路线偏离**。

## coverage：13 个场景逐个结果

| 场景 | 运行 | 成功 | 碰撞 | 闯红灯 | 链路时延 avg (ms) | 该场景最差 max (ms) |
|---|---:|---:|---:|---:|---:|---:|
| S00_chain_start | 1 | 1 | 0 | 0 | 14.24 | 31 |
| S01_set_speed_20 | 1 | 1 | 0 | 0 | 14.29 | 47 |
| S02_slow_down | 1 | 1 | 0 | 0 | 13.16 | 31 |
| S03_stop | 1 | 1 | 0 | 0 | 13.24 | 16 |
| S04_emergency_stop | 1 | 1 | 0 | 0 | 13.44 | 16 |
| D01_red_light_stop | 1 | 1 | 0 | 0 | 12.34 | 31 |
| D02_pedestrian_crossing | 1 | 1 | 0 | 0 | 13.79 | 31 |
| D03_front_vehicle_brake | 1 | 1 | 0 | 0 | 13.79 | 32 |
| D04_lane_deviation | 1 | 1 | 0 | 0 | 15.55 | 32 |
| D05_invalid_control_nan | 1 | 1 | 0 | 0 | 13.28 | 16 |
| D06_throttle_brake_conflict | 1 | 1 | 0 | 0 | 14.28 | 32 |
| D07_low_ttc_emergency_brake | 1 | 1 | 0 | 0 | 14.87 | 32 |
| D08_command_conflict_red_light_continue | 1 | 1 | 0 | 0 | 12.75 | 31 |

其中 `safety_D` 的 8 个场景各自带硬性安全检查（`expected` 字段），覆盖：
红灯停车、行人横穿、前车急刹、车道偏离、NaN 控制、油门刹车冲突、低 TTC 急刹、
红灯与指令冲突时的安全优先——**全部通过**。

## multiround：同配置 ≥3 轮

| 场景 | 轮数 | 成功 | 平均链路时延 (ms) | p99 上界 (ms) | 最差 max (ms) |
|---|---:|---:|---:|---:|---:|
| S01_set_speed_20 | 3 | 3 | 13.99 | 16 | 32 |
| S04_emergency_stop | 3 | 3 | 14.06 | 31 | 32 |
| D01_red_light_stop | 3 | 3 | 13.09 | 31 | 31 |

## stability：连续 7.1 分钟窗口

| 场景 | 轮数 | 成功 | 平均链路时延 (ms) | 最差 max (ms) |
|---|---:|---:|---:|---:|
| S00_chain_start | 3 | 3 | 14.22 | 31 |
| S01_set_speed_20 | 3 | 3 | 14.06 | 32 |
| S02_slow_down | 3 | 3 | 13.82 | 32 |
| S03_stop | 3 | 3 | 13.56 | 32 |
| S04_emergency_stop | 3 | 3 | 13.56 | 32 |

15 次运行连续 7.1 分钟，成功率 100%，时延未见趋势性上升。

## 这些数字是什么口径

`sensor_to_control` = 传感器就绪 → 控制指令下发，**含 CARLA 仿真 tick、感知采集与
A/B/C/D 控制**，`qwen_*` 部分为空（未接模型）。**不是模型时延，也不是板端时延**。

## 能证明什么 / 不能证明什么

**能证明**

- A/B/C/D 链路在 13 个场景（含 8 个安全场景）下都能正确执行并判定通过；
- 安全仲裁的硬性检查项全部满足：红灯停车、行人避让、低 TTC 急刹、控制非有限值拦截、
  油门刹车不重叠、红灯与指令冲突时安全优先；
- 同配置连续 3 轮结果一致，7.1 分钟连续运行无失败、无时延漂移。

**不能证明**

- 任何关于 Student 的结论（本轮没有 Student 在环，planner 走的是场景自带命令）；
- 任何关于 Teacher/Qwen 的结论（未接 Qwen 服务）；
- Seen / Variant / Unseen 的正式分组结论（跑的是 smoke 与 safety_D，不是 B2 冻结的
  benchmark 分组）；
- 板端性能（无 J6P）。

## 运行环境与复现

CARLA `0.9.16`（`Town03_Opt` 起，场景各自声明地图），代码版本 `challenge` @ `64577ea0`。

```powershell
py -3.12 -m tools.run_carla_scenario_matrix `
  --scenario scenarios/smoke/S00_chain_start.json `
  --scenario scenarios/smoke/S01_set_speed_20.json `
  --scenario scenarios/smoke/S02_slow_down.json `
  --scenario scenarios/smoke/S03_stop.json `
  --scenario scenarios/smoke/S04_emergency_stop.json `
  --scenario scenarios/safety_D/D01_red_light_stop.json `
  --scenario scenarios/safety_D/D02_pedestrian_crossing.json `
  --scenario scenarios/safety_D/D03_front_vehicle_brake.json `
  --scenario scenarios/safety_D/D04_lane_deviation.json `
  --scenario scenarios/safety_D/D05_invalid_control_nan.json `
  --scenario scenarios/safety_D/D06_throttle_brake_conflict.json `
  --scenario scenarios/safety_D/D07_low_ttc_emergency_brake.json `
  --scenario scenarios/safety_D/D08_command_conflict_red_light_continue.json `
  --seeds 0 --repeats-per-seed 1 `
  --output-dir artifacts/carla_matrix/coverage_20260918
```

把 `--repeats-per-seed` 改成 3 即得到 `stability/` 批次；换场景列表即得到 `multiround/`。

## 限制

1. 单 seed（seed 0）、无 Student、无 Qwen；
2. `stability/` 是 7.1 分钟的连续窗口，不是文档要求的板端长稳（30 分钟）；
3. 每个 run 的逐帧 `.jsonl` 约 2.5 MB，留在 `artifacts/carla_matrix/`（gitignore 覆盖），
   本目录只保留各批次的 `scenario_matrix_report.json`（合计 33 KB）；
4. 时延数字仅在同一机器状态内可比，参见 X86 证据批里的 CPU 标定说明。
