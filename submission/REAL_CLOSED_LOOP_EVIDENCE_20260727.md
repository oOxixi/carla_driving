# 真实 Qwen–CARLA 闭环证据（2026-07-27）

## 环境

- 服务器：`tiaozhansai`
- GPU：NVIDIA GeForce RTX 3090，24 GB，仅使用 GPU 0
- CARLA：0.9.16，`Carla/Maps/Town03_Opt`
- 视觉语言模型：本地 `Qwen2.5-VL-7B-Instruct`
- 模型目录：`/home/tiaozhansai/models/Qwen2.5-VL-7B-Instruct`
- 证据根目录：`/home/tiaozhansai/carla_driving/artifacts/qwen_carla_closed_loop_0727`

说明：完整 `Town03` 在该 Ubuntu/驱动组合下会触发 CARLA SIGSEGV，实测使用官方低资源地图 `Town03_Opt`；项目地图校验将其归入 Town03。

## 端到端多模态闭环

有效运行：`run_003`

- 真实 CARLA RGB 与 LiDAR 同步采集；
- 真实 Qwen2.5-VL-7B 推理；
- Qwen 严格边界解析为高层 `SET_SPEED`，不允许模型直接输出油门、刹车或方向盘；
- 目标速度：4.0 m/s；
- Qwen 推理延迟：3744.761 ms；
- 控制帧：120；
- RGB/LiDAR 对：14；
- 行驶距离：16.549 m；
- 最终/最大速度：3.828 m/s；
- 碰撞：0；
- 闯红灯：0；
- 轨迹合理性：通过；
- 任务状态：`SUCCEEDED`。

报告：
`artifacts/qwen_carla_closed_loop_0727/run_003/closed_loop_report.json`

SHA-256：
`7e8cd61f1ac91f100d3897fc113fc3ecc475b65844fcfddf18d5c7d737c07edf`

`run_001` 与 `run_002` 是调试运行，不作为最终证据；最终指标只引用 `run_003`。

## 三个正式场景

### S01 基础定速

- 状态/得分：`SUCCEEDED`，25/25；
- 帧数：600；
- 最终速度：17.793 km/h，目标 20±5 km/h；
- 最大横向误差：0.0023 m；
- 碰撞/严重偏航：0/0；
- 传感器到控制平均/最大延迟：1.118/3.829 ms。

证据：
`formal/S01/S01_set_speed_20_20260727_224749_380324.summary.json`

SHA-256：
`e093552479408b6fe5dc34c8bb544bb9480952815958ec0f1d2bf11a9fe076f7`

### D03 前车制动与安全跟车

- 状态/得分：`SUCCEEDED`，25/25；
- 帧数：700；
- 最小车距：4.860 m，要求不低于 2.5 m；
- 最小 TTC：2.926 s；
- 安全覆盖：155 帧、29 个 episode；
- 安全原因：`EMERGENCY_FRONT_OBSTACLE_TOO_CLOSE`；
- 碰撞：0；
- 传感器到控制平均/最大延迟：1.068/4.241 ms。

证据：
`formal/D03_final/D03_front_vehicle_brake_20260727_225431_352952.summary.json`

SHA-256：
`2950cfea109003b9ac03061ab2b1e8ef1b031a61d240db5956ed06a4dbe1f057`

### D08 红灯与冲突指令

- 状态/得分：`SUCCEEDED`，25/25；
- 帧数：500；
- 最终速度：0 m/s；
- 停止线前距离：0.935 m；
- 安全覆盖：410 帧、1 个 episode；
- 安全原因：`RED_LIGHT_STOP_LINE_GUARD`；
- 闯红灯/碰撞：0/0；
- 传感器到控制平均/最大延迟：0.786/4.394 ms。

证据：
`formal/D08/D08_command_conflict_red_light_continue_20260727_225524_159228.summary.json`

SHA-256：
`08f57fc52eb340a88ae0d7788bf059cf12e273b69fce7834d06a11d5c7f1cf9d`

## 回归结果

- 服务器完整自动化测试：379 passed，1 skipped；
- 被跳过项是需要显式设置 `CARLA_SMOKE=1` 的在线仿真 smoke；
- 单独启用该变量并连接正在运行的 CARLA 后：1 passed；
- 本次新增/相关边界、场景执行与验收测试：62 passed。

## 本次闭环修复

- 接受 Qwen 常见的单一 `json` Markdown 围栏，同时继续拒绝解释性文字、多围栏、未知字段和底层车辆控制；
- 增加真实 RGB/LiDAR → Qwen → 严格 JSON → 高层命令 → 安全控制 → CARLA 执行与证据采集工具；
- 场景命令 TTL 覆盖完整剩余场景时长；
- 持续跟车类任务在完整帧预算结束后按显式安全合同验收，不再被错误标记为“命令未结束”；
- WATCHDOG、集成故障、碰撞和不满足最小车距仍会导致验收失败。

本文件只记录本次实测结果；代码和报告尚未提交或推送。
