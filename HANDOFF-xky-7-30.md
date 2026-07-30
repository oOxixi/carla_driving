# HANDOFF xky 7/30

## 分支与范围

- 目标分支：`new`
- 本次只优化 D 控制、安全仲裁、指令终态和性能验收。
- 未修改 Qwen 模型、ASR 模型或 CARLA 传感器算法。

## 今日完成

1. 修复红灯前车辆松油门滑行但未制动时可能越线的问题，并在停车后保持制动。
2. 对非法控制、NaN/非法传感器状态、非法交通灯状态、碰撞、闯红灯和 Watchdog 告警统一 fail-closed。
3. 增加安全配置范围校验，拒绝非法 TTC、距离、置信度和控制参数。
4. 增加 `SAFETY_OVERRIDE` 指令终态：
   - 硬安全接管后，活跃指令立即产生唯一终态；
   - 短暂 TTC 谨慎制动、车道偏移和路线恢复不会误终止高层指令。
5. 新增可重复的控制性能基准：
   - `python tools/run_control_safety_benchmark.py`
   - 输出：`artifacts/control_benchmark.json`
6. 删除旧交付快照中 3 个无意义 `.bak` 文件；历史源码、HANDOFF 和实跑证据均保留。

## 本机验收结果

- 全仓库：`420 passed, 1 skipped`
- 安全仲裁 P95：`0.0130 ms`
- A/B/C/D 完整控制步 P95：`0.0539 ms`
- 验收门槛：P95 `<= 5 ms`
- 本机纯 Python 控制链验收：通过

## 关键文件

- `car_control_D/safety_supervisor.py`
- `car_control_D/adapters.py`
- `car_control_D/benchmark.py`
- `car_control_A/behavior_fsm.py`
- `car_control_A/contracts.py`
- `integration/runtime_loop.py`
- `tools/run_control_safety_benchmark.py`
- `artifacts/control_benchmark.json`

## 下一阶段：必须真实 CARLA 实跑

按顺序执行：

1. 单次连通性与场景冒烟：S01、D03、D08 各 1 次。
2. 确认场景 actor、传感器来源、交通灯和前车制动事实真实生效。
3. 三场景多 seed 重复：每场至少 `5 seeds × 20 runs`。
4. 连续稳定运行至少 60 分钟。
5. 汇总并检查：
   - 碰撞数、闯红灯数、严重路线偏离数均为 0；
   - 每个 `command_id` 有且仅有一个终态；
   - D 接管原因、TTC、最小前车距离、停车线误差可审计；
   - 控制/安全 P95 `<= 5 ms`；
   - 日志、summary、视频和运行命令完整。

## 注意

- `SAFETY_OVERRIDE` 是合法且可审计的终态，不应改写为普通 `FAILED`。
- D03/D08 的正式传感器验收必须使用真实 perception 来源，不能把 scenario truth 当作实测感知。
- 如果先用 `scenario` 或 `fuse` 模式校准 actor，只能标注为场景契约测试，不能替代正式 sensors/perception 证据。

## 7/30 Ubuntu 实跑进度

- 服务器 worktree：`/home/tiaozhansai/carla_driving_new_0730`
- CARLA：0.9.16，GPU 0，`Town03_Opt`，端口 2000
- 模式：`perception-mode=sensors`、`scenario-facts-mode=perception`
- 单次冒烟：
  - S01：通过，25 分
  - D03：通过，25 分，真实前车 actor 和 LiDAR 距离生效
  - D08：通过，25 分，产生 `RED_LIGHT_STOP_LINE_GUARD` 和 `SAFETY_OVERRIDE`
- 5-seed 校准：三场景共 `15/15` 通过，碰撞/闯灯/路线偏离均为 0。
- 校准中最差单次 P95：D03 `1.848416 ms`，低于 5 ms。
- 正式 `5 seeds × 20 runs × 3 scenarios` 已用断点续跑启动：
  - PID：`2197516`
  - 进度日志：`artifacts/d_0730_matrix_full.log`
  - 最终报告：`artifacts/d_0730_matrix/scenario_matrix_report.json`
  - 单次证据：`artifacts/d_0730_matrix/<scenario>/seed_<n>/run_<nn>/`
