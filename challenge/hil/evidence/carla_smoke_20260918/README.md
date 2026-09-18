# CARLA 闭环可行性冒烟（2026-09-18）

**目的**：确认 B3 在这台机器上具备跑 CARLA 闭环测量的条件——CARLA 服务端、Python API、
`Town03_Opt` 地图、车辆与传感器、以及仓库自研的 A/B/C/D 执行链全部可用。

**这不是达标结论**：本轮**没有接入 Student 或 Teacher**，`qwen_status = DISABLED`，
用的是仓库的确定性命令路径。它只证明"链路能跑通"，不产出任何性能或精度结论。

## 结论

| 项 | 值 |
|---|---|
| 场景 | `scenarios/smoke/S01_set_speed_20.json`（basic 难度） |
| 入口 | `python -m integration.carla_runner`（仓库自研 runner，**不是 ScenarioRunner**） |
| 状态 | **`SUCCEEDED`** |
| 完成度 | `completion = true`，`unfinished_tasks = 0` |
| 得分 | **25 / 25**（`base_score 25`，`deduction 0`） |
| 帧数 | 600 帧（30 秒仿真，`fixed_delta_s = 0.05`） |
| 验收检查 | **6/6 通过**，`failed_keys = []` |
| 碰撞 / 偏离路线 | 0 / 0 |
| 末速 | 5.48 m/s（目标 5.56 m/s，即 20 km/h ±5） |
| 链路调用 | `called_B = true`、`called_C = true`、`called_D = true`、`carla_started = true` |
| 命令终态 | `scenario_cmd_000 = SUCCEEDED` |

验收检查明细（全部 PASS）：

| 检查 | 实测 | 要求 |
|---|---|---|
| `must_generate_logs` | true | true |
| `max_cross_track_error_m` | 0.0019 | ≤ 1.0 |
| `must_no_collision` | 0 | 0 |
| `must_no_route_deviation` | 0 | 0 |
| `target_speed_kph` | 19.29 | 20 ± 5 |
| `speed_tolerance_kph` | 5 | 与上一条配对 |

## 链路时序（无模型参与，仅供链路参考）

取自本轮的 `latency` 摘要，单位 ms：

| 指标 | avg | p95 | max |
|---|---:|---:|---:|
| 仿真 tick | 9.25 | 16.0 | 32.0 |
| 感知采集 | 22.11 | 47.0 | 63.0 |
| 决策 | 0.54 | 0.0 | 16.0 |
| 感知→控制 | 27.43 | 62.05 | 63.0 |
| 流水线活跃 | 49.70 | 109.0 | 125.0 |

**注意**：本轮 `qwen_model_*` 全为 `null`（无模型调用），因此这些数字**不能**与
B3 的 Planner 延迟证据（`evidence/x86_prevalidation_20260918/`）混为一谈。
后者测的是 Planner 链本身，这里是含仿真与传感器的整链开销。

## 运行环境

| 项 | 值 |
|---|---|
| CARLA | `0.9.16`，服务端 `D:\CARLA_Latest`（仓库内以 junction `CARLA_0.9.16` 暴露） |
| 地图 | `Carla/Maps/Town03_Opt` |
| Python | 系统 `py -3.12`（已装 `carla 0.9.16` cp312 wheel） |
| 代码版本 | `challenge` @ `64577ea0`（记录在日志的 `run_start.config.code_version`） |
| GPU | RTX 4060 Laptop，CARLA 服务端占用约 6.1 GB 显存 |

## 复现方式

```powershell
# 1) 启动 CARLA 服务端
Start-Process -FilePath "D:\CARLA_Latest\CarlaUE4.exe" `
  -ArgumentList "-quality-level=Low","-windowed","-ResX=800","-ResY=600","-nosound" `
  -WindowStyle Hidden

# 2) 跑场景（等端口 2000 就绪后）
py -3.12 -m integration.carla_runner `
  --scenario-file scenarios/smoke/S01_set_speed_20.json `
  --host 127.0.0.1 --port 2000 --timeout-s 60 `
  --perception-mode sensors --print-every 150 `
  --log-dir artifacts/logs/b3_smoke
```

## 已知限制

1. **无 Student / Teacher**：`qwen_status = DISABLED`，不构成闭环性能或任务完成率结论；
2. 本目录只保留 `summary.json`（6.7 KB）。原始逐帧 `.jsonl` 约 2.5 MB，留在
   `artifacts/logs/b3_smoke/`（该目录被 `.gitignore` 覆盖），需要时按上面的命令重跑；
3. 场景定义是仓库自研格式，**不是 ScenarioRunner 场景**；ScenarioRunner 只完成了
   安装与可执行性验证，尚未用于本仓库的场景执行（见 `repo_environment_findings.md` F1/F4）；
4. 显存占用高（6.1 GB / 8.2 GB），与 B3 的延迟测量**不能并行**进行。
