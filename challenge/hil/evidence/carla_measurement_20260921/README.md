# CARLA 闭环实测（2026-09-21，B3 入口脚本首次落地）

**目的**：用本轮新增的 `challenge/hil/carla_measurement.ps1` 跑一次**真实** CARLA 闭环，
验证"可重复测量入口"确实可用，并为 CARLA 侧留下新的原始证据。

**这不是达标结论**：本轮仍未接入 Student/Teacher（`qwen_status = DISABLED`），走的是仓库
确定性命令链。它证明链路可跑通、入口可重复，不产出任何性能或精度结论。

## 运行条件

| 项 | 值 |
|---|---|
| 入口 | `powershell -File challenge/hil/carla_measurement.ps1 -Scenario S01_set_speed_20 -Realtime` |
| 底层 runner | `python -m integration.carla_runner --scenario-file scenarios/smoke/S01_set_speed_20.json`（仓库自研，**不是** ScenarioRunner） |
| CARLA | `D:\CARLA_Latest\CarlaUE4.exe -quality-level=Low -nosound`，端口 2000 可达后才开跑 |
| Python | 系统 `py -3.12`（`PYTHONPATH` 含 `D:\CARLA_Latest\PythonAPI` 与 scenario_runner 本体） |
| 地图 / 场景 | `Town03` / `Town03_Opt`，`S01_set_speed_20`（basic） |
| 时长 | 600 帧、`fixed_delta_s = 0.05`、30 s 实时仿真 |

## 结果

| 项 | 值 |
|---|---|
| 状态 | **`SUCCEEDED`**（进程返回码 0） |
| 验收 | **6/6 通过**，`failed_keys = []`，`unsupported_keys = []` |
| 得分 | 25 / 25（`deduction 0`，`unfinished_tasks 0`） |
| 碰撞 / 路线偏离 | 0 / 0 |
| 红灯违规 / 车道入侵 | 0 / 0 |
| 末速 | 5.482 m/s = **19.74 km/h**（目标 20 ±5） |
| 最大横向误差 | 0.0085 m（要求 ≤ 1.0 m） |
| 链路调用 | `called_B / called_C / called_D = true`、`carla_started = true`、`commands_all_succeeded = true` |
| 控制输出 | `final_control_all_finite = true`、`final_control_overlap_count = 0` |

逐项验收（全部 PASS）：`must_generate_logs`、`max_cross_track_error_m`、
`must_no_collision`、`must_no_route_deviation`、`target_speed_kph`、`speed_tolerance_kph`。

## 本目录文件

| 文件 | 内容 |
|---|---|
| `S01_set_speed_20.summary.json` | runner 产出的验收汇总（含 `acceptance.checks` 与全部 metrics） |
| `carla_run_summary.json` | B3 入口记录的本次调用：命令、返回码、stdout 尾部、日志目录 |
| `carla_measurement_plan.json` | 入口的总体清单：解释器、CARLA 根、scenario root、PYTHONPATH、每场景状态 |

原始逐帧 JSONL（约 2.5 MB，本次 600 帧）留在 `artifacts/b3/carla_measurement_20260921/`
（被 gitignore 覆盖），未入库；其摘要即本目录的第一份文件。

## 与 2026-09-18 冒烟的关系

`evidence/carla_smoke_20260918` 是手工命令跑出的同一场景（25/25、600 帧、末速 19.29 km/h）。
本次是**用固定入口脚本重跑**：结论一致（25/25，末速 19.74 km/h），差别只是入口可重复、
参数与 PYTHONPATH 被固化，且新增了"CARLA 不可达即失败退出"的守卫。

## 限制

- 无 Student/Teacher 在环，因此不含任何模型相关的结论；
- 场景仅 1 个（`S01_set_speed_20`），不是 Seen/Variant/Unseen 分组矩阵；
- 本机在电池供电下运行，若日后用这些数据谈延迟，必须先按 §8 口径在 AC 上重跑。
