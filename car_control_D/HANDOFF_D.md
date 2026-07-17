# 成员 D 技术交接：安全仲裁、自动评测与证据记录

## 1. 职责与边界

成员 D 是最终安全仲裁和评分证据负责人。D 接收 A 合成后的原始控制量、车辆状态、语音结构化命令、C 的 RiskMetrics 和 A 的 watchdog 结果，在 CARLA `apply_control` 前返回最终 `ControlOutput`、安全接管标志和原因。

D 不启动 CARLA，不调用 `vehicle.apply_control()`，不负责横向轨迹、纵向 PID、ASR 或复杂多模态推理。A 是唯一运行时编排方和唯一控制下发方；D 是安全与评分证据出口。

## 2. 目录与模块图

```text
A/B/C raw_control + VehicleState + DrivingCommand + RiskMetrics
  -> safety_supervisor.SafetySupervisor.arbitrate()
     -> validators.py 检查命令和控制量
     -> adapters.py 兼容 dict / dataclass
     -> schemas.py D 内部数据结构
  -> SafetyDecision(final_control, safety_override, reason)
  -> A 统一下发 CARLA VehicleControl

场景结果 / 命令 / 每帧状态
  -> metrics.ScenarioRecorder
  -> official_score.OfficialScorer
  -> result.json / score_report.json / event_log.jsonl / frame_log.jsonl
```

| 文件 | 实际职责 |
|---|---|
| `schemas.py` | D 内部数据结构，只放 dataclass 和常量，不导入其他 D 模块 |
| `adapters.py` | 将 A/C 的 dataclass 或 dict 转为 D 的统一视图 |
| `validators.py` | 检查 DrivingCommand、ControlOutput、ExecutionFeedback 合法性 |
| `safety_supervisor.py` | 最终安全仲裁，输出 final_control 和 reason |
| `official_score.py` | 25/10/5 扣分、三级完成率、延迟统计 |
| `metrics.py` | 场景记录器，输出 result/score/event/frame 日志 |
| `scenario_runner.py` | 场景包装运行器，统一写入结果 |
| `demo_fake_integration.py` | 无 CARLA 假数据联调入口 |
| `tests/` | D 模块单元测试 |

## 3. 环境、运行与验证

在仓库根目录执行：

```powershell
python -m pytest car_control_D\tests -q
python -m car_control_D.demo_fake_integration
```

成功后会在 `logs/` 下生成：

```text
result.json
score_report.json
event_log.jsonl
frame_log.jsonl
```

## 4. 核心执行流程与实现要点

1. A 每帧收集车辆状态、命令状态、B/C 原始控制量和 C 的风险指标。
2. A 合成 `raw_control = {steer, throttle, brake}`。
3. A 调用 `SafetySupervisor.arbitrate(raw_control, vehicle_state, command, risk, watchdog_alerts)`。
4. D 检查控制输出合法性、命令置信度、TTC、前方距离、红灯/停止线、路线偏差、watchdog 等风险。
5. D 返回 `SafetyDecision`，包含 `final_control`、`safety_override`、`reason`、`risk_metrics`。
6. A 使用 `final_control` 唯一下发 CARLA。
7. D 记录每帧控制、安全接管和场景结果，生成评分证据。

## 5. 公开接口与字段表

| 接口 | 字段 | 说明 |
|---|---|---|
| `DrivingCommand` | `schema_version`, `command_id`, `source_text`, `intent`, `parameters`, `confidence`, `intent_confidence`, `ambiguity_type`, `confirm_required` | 兼容语音组结构化命令，intent 使用大写 |
| `ControlOutput` | `throttle`, `brake`, `steer` | 归一化控制量，油门刹车互斥，steer 在 `[-1,1]` |
| `VehicleStateView` | `frame`, `sim_time_s`, `speed_mps`, `front_distance_m`, `traffic_light`, `distance_to_stop_line_m`, `lane_offset_m`, `route_deviation_m` | A/感知层提供 |
| `RiskView` | `ttc_s`, `desired_gap_m`, `emergency_brake_requested` | C 纵向模块提供 |
| `SafetyDecision` | `final_control`, `safety_override`, `reason`, `risk_metrics`, `raw_control` | D 返回给 A 的最终仲裁结果 |

## 6. 配置、重置与生命周期

- D 不持有 CARLA Actor 生命周期。
- 每个 scenario 重新创建或清空 `ScenarioRecorder`。
- `SafetySupervisor` 可长期复用，但阈值应通过 `SafetyConfig` 统一配置。
- D 所有日志写入使用异步友好的 JSON/JSONL；正式版本应避免同步写盘阻塞控制循环。

## 7. 测试覆盖、边界与交接

已覆盖：语音组 `SLOW_DOWN` 命令校验、控制量冲突、低 TTC 强制刹车、UNKNOWN 命令安全保持、25/10/5 扣分和基础延迟统计。

当前边界：D 依赖 A 提供真实 CARLA collision、lane invasion、traffic light、route deviation 等状态；D 当前不生成真实场景，不保存失败视频，不做 Docker/Jupyter 打包。

## 8. 常见故障定位

| 现象 | 优先检查 |
|---|---|
| pytest 循环导入 | 确保 `schemas.py` 不导入 `official_score/adapters/safety_supervisor` |
| D 不接管危险场景 | 检查 `risk.ttc_s`、`front_distance_m`、`emergency_brake_requested` 是否真实传入 |
| 红灯不停车 | 必须同时有 `traffic_light` 和 `distance_to_stop_line_m` |
| 语音延迟无法统计 | 语音组需要补 `t_audio_start_ns/t_asr_end_ns/t_intent_end_ns` |
| Git 里出现重复文件 | 清理 `(1)/(2)/(4)` 文件，测试文件只保留在 `car_control_D/tests/` |
