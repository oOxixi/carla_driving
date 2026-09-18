# CARLA 闭环 · 经 Qwen 契约层（2026-09-18）

**可信范围**：`QWEN_DETERMINISTIC_CHAIN_ONLY` —— 链路级验证，**不是模型结论**。

本轮把 CARLA 闭环接到了 Qwen 的 HTTP 契约层，走通了此前完全未验证的分支：
`planner_v2` 模式、异步 Qwen 桥接、计划编译与执行、以及 fail-closed。

## 用的不是真模型

| 项 | 值 |
|---|---|
| 后端 | `DETERMINISTIC_PLANNER_V2_TEST_BACKEND` |
| `production_ready` | **false** |
| 服务端自述 | "planner v2 test backend ready (not a production Qwen model)" |
| 启动命令 | `python -m qwen_service.server --deterministic-test-backend --qwen-mode planner_v2 --port 8765` |

代码 docstring 明确写着 *"Contract-test backend; never valid evidence for Qwen
correctness/latency"*。**本轮所有时延都不含任何模型推理**，只是 HTTP 契约与编排开销。

## 结论

| 项 | 值 |
|---|---|
| 场景 | `scenarios/smoke/S01_set_speed_20.json` |
| 状态 | **`SUCCEEDED`** |
| 完成度 | `completion = true` |
| 得分 | **25 / 25** |
| 帧数 | 600（30 秒仿真） |
| 验收检查 | **6/6 通过** |
| 碰撞 / 偏离路线 | 0 / 0 |
| 末速 | 5.482 m/s（目标 5.56） |
| A/B/C/D | `called_B/C/D = true` |

Qwen 计划的完整生命周期（日志中的真实记录）：

```
canonical_command_route  SLOW_PENDING  (QWEN_QUEUED)
canonical_slow_result    SLOW_READY    "validated Qwen plan dispatched"
qwen_plan_started        PLAN_ACCEPTED      plan-qwen-d4313a16…
qwen_step_started        STEP_ENTER         step s1
qwen_step_completed      COMPLETION_HELD
qwen_terminal            SUCCEEDED          PLAN_COMPLETE
scenario_acceptance      SUCCEEDED          score 25.0
```

## Qwen 链路时延分解（不含模型推理）

取自 `qwen_trajectory` 记录，单位 ms：

| 环节 | 值 |
|---|---:|
| 传感器就绪 → 提交（`sensor_to_submit_ms`） | 15.0 |
| 排队等待（`queue_wait_ms`） | 0.0 |
| **infer 回调合计（`infer_callback_ms`）** | **47.0** |
| ├ HTTP 往返（`client_http_roundtrip_ms`） | 44.89 |
| ├ 图像变换（`client_image_transform_ms`） | 4.93 |
| ├ 序列化 / 解码 | 0.03 / 0.02 |
| **传感器就绪 → 轨迹就绪（`sensor_to_trajectory_ms`）** | **62.0** |

**这 62 ms 全是契约层与编排开销**——确定性后端不做任何前向计算。真实模型的数字会显著
高于此，两者不可混用。

## 一个重要的操作发现：必须加 `--realtime`

第一次运行时**没有**加 `--realtime`，结果 Qwen 请求超时失败：

```
service 端日志：POST /infer → 408
runner 日志  ：disposition=REJECTED  status=TIMED_OUT  terminal_reason=QWEN_TIMEOUT
               → 车辆全程 HOLD（brake 0.55），场景 FAILED（target_speed_kph 未达成）
```

服务端返回的是 **408 `REQUEST_EXPIRED`**（不是 504 模型超时）：请求到达时，它自己的
`deadline_ns`（提交时刻 + 300 ms）已经过期。根因是**主循环满速运行抢占 GIL，Qwen 工作
线程拿不到时间片**，导致 HTTP 请求发出得太晚。

加上 `--realtime` 后同一条命令即通过，服务端日志出现 `POST /infer → 200`。

**结论**：接入 Qwen 时必须加 `--realtime`（仓库的官方脚本 `run_official_scenes.ps1`
本来就带这个参数，所以官方路径不会踩到）。这条已记入
`challenge/hil/repo_environment_findings.md` **F5**。

**附带价值**：这次失败**顺带验证了 fail-closed 的真实行为**——Qwen 超时后编排器没有放行
推进，而是落到 HOLD 保持制动。这是纯软件回放测不到的。

## 运行环境

| 项 | 值 |
|---|---|
| CARLA | `0.9.16`，`Town03_Opt` 地图，服务端在 `127.0.0.1:2000` |
| Qwen 契约层 | `127.0.0.1:8765`，`qwen_mode=planner_v2`，`timeout_ms=300`，`max_concurrency=1` |
| Python | 系统 `py -3.12` |
| 代码版本 | `challenge` @ `64577ea0` |

## 复现方式

```powershell
# 1) 起确定性后端
py -3.12 -m qwen_service.server --deterministic-test-backend --qwen-mode planner_v2 `
  --host 127.0.0.1 --port 8765

# 2) 起 CARLA 服务端（若未运行）
#    见 evidence/carla_smoke_20260918/README.md

# 3) 跑闭环（--realtime 不可省）
py -3.12 -m integration.carla_runner `
  --scenario-file scenarios/smoke/S01_set_speed_20.json `
  --host 127.0.0.1 --port 2000 --timeout-s 60 --realtime `
  --perception-mode sensors --scenario-facts-mode perception `
  --qwen-service-url http://127.0.0.1:8765 --qwen-mode planner_v2 `
  --qwen-timeout-ms 300 --qwen-queue-size 1 `
  --qwen-image-root . --qwen-image-prefix artifacts/runtime/qwen_local `
  --log-dir artifacts/logs/b3_qwen_loop
```

## 已知限制

1. **后端是确定性规则，不是模型**：`production_ready=false`，不得作为 Qwen 正确性/性能证据；
2. 本轮时延（62 ms 级）**不含模型推理**，与真实 2B 服务的量级完全不同；
3. 只跑了 1 个场景、1 个 seed、1 轮；未做多轮重复与 Seen/Variant/Unseen 分组；
4. 未接入 Student（该闭环的"planner"是确定性后端，不是 Student）；
5. 原始逐帧日志 2.5 MB 留在 `artifacts/logs/b3_qwen_loop/`（gitignore 覆盖），
   本目录只保留 summary。
