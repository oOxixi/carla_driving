# 成员 C 技术交接：纵向规划、停车、跟车与保守语音回退

## 1. 职责与非职责

成员 C 将 A 提供的帧对齐车况、请求速度、路径曲率、交通约束和前车观测，转换为确定性的纵向目标及互斥油门/刹车。功能包括速度 PID、多约束限速、停止线停车、时距跟车/TTC、低置信度或歧义语音的“减速—停车—确认”本地回退。

C 不实现横向转向/变道/绕障（B）、最终安全仲裁/官方评分（D）、CARLA Actor 或传感器生命周期（A）、检测/跟踪或语音识别。C 的 `emergency_brake_requested` 与局部制动是可解释的局部回退；D 仍是最终安全权威。CARLA 服务和 `CARLA_ROOT` 也仅由用户启动和管理。

## 2. 目录与模块图

```text
A: LongitudinalRequest
  -> FuzzyCommandPolicy（仅不可信/过期命令时将 requested_speed 置 0）
  -> LongitudinalController.step()
     -> TrafficRulePlanner（灯色/停止线/限速）
     -> StopController（CRUISE/DECELERATE/CREEP/HOLD）
     -> FollowingController（d_des、速度上界、TTC）
     -> SpeedPlanner（所有硬约束最小值 + 命令舒适斜坡）
     -> SpeedPID（目标速度 -> 请求加速度）
     -> 速率限制与油门/刹车互斥
  -> LongitudinalOutput(control, target_accel, target_speed, state, reason, risk)
  -> A/B 合成；D 最终仲裁；CARLA 下发
```

|文件|实际职责|
|---|---|
|`longitudinal_controller.py`|C 的主入口、控制映射、紧急回退和 episode reset|
|`speed_planner.py`|曲率、交通、停车、前车硬上界与命令速度斜坡|
|`speed_pid.py`|带限幅和 anti-windup 的 SI 速度 PID|
|`stop_controller.py`|四阶段停止状态、停止速度上界、不可达停止所需减速度|
|`following_controller.py`|时距间距、前车速度上界、TTC 风险|
|`traffic_rules.py`|红/黄/未知灯的保守停止线约束和限速提取|
|`fuzzy_command_policy.py`|低置信度/歧义/过期命令的局部安全回退|
|`config.py`|严格可序列化的模糊命令策略配置|
|`validation.py`|公共控制 API 的有限数值校验|
|`tests/`|无 CARLA 的纵向单测和 A/C 集成测试|

## 3. 环境与正确测试命令

代码本身 CARLA-independent；标准回归使用项目 Conda 环境：

```powershell
conda run --no-capture-output -n carla python -m pytest car_control_A/tests car_control_C/tests -q
```

若同时验证 A/C 的真实 CARLA 会话，必须由用户在另一个 PowerShell 自行启动服务：

```powershell
$env:CARLA_ROOT = 'F:\carla_driving_rstar\CARLA_0.9.16'
cd $env:CARLA_ROOT
.\CarlaUE4.exe -quality-level=Low -carla-port=2000
```

随后仅运行 A 的门控会话烟测：

```powershell
$env:CARLA_SMOKE = '1'
conda run --no-capture-output -n carla python -m pytest car_control_A/tests/test_simulator_smoke.py -q
```

C 没有单独的 CARLA socket/启动代码；`CARLA_SMOKE` 未设置时烟测会按设计跳过。

## 4. 核心流程与核心函数

### 每个仿真帧的调用顺序

1. A 构造 `LongitudinalRequest`，所有速度为 m/s、曲率为 `1/m`。若有前车，`lead_distance_m` 和 `closing_speed_mps` 必须同时提供，其中闭合速度为 `ego - lead`，正值表示接近。
2. 对语音命令先调用 `FuzzyCommandPolicy.evaluate(command, request)`。过期命令返回 `EXPIRED` 反馈并把请求速度置零；低于阈值、歧义或显式确认命令也置零、输出制动并请求确认。清晰命令原样透传。
3. 将得到的 request 传给 `LongitudinalController.step(request, dt_s)`；`dt_s` 应与 A 的同步固定步长一致（常用 `0.05`），且必须为正有限数。
4. 将返回的 `LongitudinalOutput.control` 与 B 的 steer 合成，交给 D 做最终仲裁；不得绕过 D 直接声称安全。
5. CARLA respawn、重载场景或 episode 边界调用 `LongitudinalController.reset()`，清空 PID 积分、速度规划历史和执行器历史。

### 关键算法实现

- **`SpeedPID.step(target_speed_mps, speed_mps, dt_s)`**：误差为 `target-current`；目标速度突变达到 `target_step_reset_mps` 时积分衰减为原值 25%。候选积分被 `±integral_limit` 限幅；输出加速度被 `[accel_min_mps2, accel_max_mps2]` 限幅，且仅在不会继续推高饱和输出时积分，避免 wind-up。
- **`SpeedPlanner.plan(request, dt_s)`**：先求曲率上界 `sqrt(max_lateral_accel / |curvature|)`（近零曲率为无穷），叠加道路限速、停止线限速、前车限速，取最小硬上界。命令速度仅按 `command_accel/decel * dt` 平滑，最后仍取硬上界最小值；安全上界不会被舒适斜坡放宽。
- **`StopController`**：状态依次为 `CRUISE`（无停止约束）、`DECELERATE`、`CREEP`（近停止线，目标不超过 `creep_speed_mps`）、`HOLD`（距离和速度均足够小，持续 hold brake）。正常速度上界基于 `v²=2ad` 的舒适减速度；若 `required_decel_mps2 >= max_decel_mps2`，主控制器输出可见的全制动回退。
- **`FollowingController`**：期望间距 `d_des = standstill_gap_m + time_gap_s * ego_speed_mps`。正闭合速度时 `TTC = lead_distance / closing_speed`，TTC 不大于 `emergency_ttc_s` 时置 `emergency_brake_requested=True`。前车上界用前车估计速度加上 `sqrt(2 * comfortable_decel * max(0, gap_error))`。
- **`TrafficRulePlanner`**：仅当存在停止线距离且灯为 `RED`、`YELLOW` 或 `UNKNOWN` 时要求停车；未知感知不能按绿灯处理。`GREEN` 不创建停止约束，但道路限速仍生效。
- **`LongitudinalController._rate_limited_control()`**：将请求加速度映射为 `[0,1]` throttle 或 brake，使用 `max_control_delta_per_s * dt_s` 限制变化率，并先清空相反执行器，保证油门/制动互斥。TTC 或不可达停止线的紧急分支直接零油门并提高制动。

## 5. 公开接口与字段表

共享输入/输出类型位于 `car_control_A.contracts`，均严格携带 `schema_version="1.0"`；未知字段、缺失字段、布尔或非有限数值会拒绝。所有纵向单位是 SI。

|类别|接口/字段|含义与限制|
|---|---|---|
|输入|`LongitudinalRequest.vehicle`|`RuntimeVehicleState`：`frame`、`sim_time_s`、`speed_mps`、位置、航向、`lane_id`|
|输入|`requested_speed_mps`|A/命令给出的期望速度，m/s，非负；不是硬安全授权|
|输入|`path_curvature_per_m`|局部路线曲率，`1/m`；C 使用绝对值计算横向加速度限速|
|输入|`traffic`|`TrafficConstraint(signal_state, distance_to_stop_line_m?, speed_limit_mps?)`；灯为 `RED/YELLOW/GREEN/UNKNOWN`|
|输入|`lead_distance_m`, `closing_speed_mps`|前车距离 m 与 `ego-lead` 闭合速度 m/s，必须同时存在|
|输出|`LongitudinalOutput.control`|`ControlOutput(throttle, brake, steer=0)`；C 输出 steer 为 0，B/A 填充转向；油门/制动互斥|
|输出|`target_accel_mps2`|C 的请求加速度 m/s²，非最终车辆控制权|
|输出|`target_speed_mps`|多约束后的目标速度 m/s|
|输出|`state`, `reason`|可审计状态：`LANE_FOLLOW/FOLLOWING/DECELERATE/CREEP/HOLD/EMERGENCY_BRAKE` 等及原因字符串|
|输出|`risk.ttc_s`|正闭合速度时的秒数；无前车或非闭合时为 `None`|
|输出|`risk.desired_gap_m`|`standstill_gap + time_gap * ego_speed`，m|
|输出|`risk.emergency_brake_requested`|本地风险信号，供 D 读取；不等于 D 的最终决策|
|策略|`FuzzyCommandPolicy.evaluate(command, request)`|返回 `FuzzyCommandDecision(request, intervened, requires_confirmation, output?, feedback?)`|
|策略配置|`FuzzyCommandPolicyConfig`|`confidence_threshold=0.80`, `comfort_decel_mps2=3`, `max_decel_mps2=5`, `hold_brake=.55`, `emergency_brake=.85`, `standstill_speed_mps=.20`|
|主入口|`LongitudinalController.step(request, dt_s)`|返回 `LongitudinalOutput`；每帧一次|
|重置|`LongitudinalController.reset()`|必须在独立 episode 前调用|

`LongitudinalParameters` 默认值：最大横向加速度 `2.5 m/s²`，命令加速/减速 `1.5/3.0 m/s²`，最大加速/减速 `2.5/5.0 m/s²`，执行器变化率 `2.0 /s`，保持制动 `0.55`，本地紧急制动 `0.85`，静止间距 `3 m`，时距 `1.5 s`，紧急 TTC `1.5 s`，舒适减速 `3.0 m/s²`。参数构造时全部验证为有限数，且范围不合法会失败；建议通过新建 `LongitudinalController(LongitudinalParameters(...))` 调参，不要运行中私改内部对象。

## 6. 配置、生命周期与 A/B/D 交接

- 每一个独立 CARLA scenario/respawn 均调用 `reset()`；否则上一场景的 PID 积分、目标速度与刹车历史会影响下一场景。
- C 不保存原始传感器数据，输入必须先由 A/感知层按 `frame` 对齐。不要把 wall-clock 秒当 `sim_time_s`，也不要将 km/h 直接传入 m/s 字段。
- A 负责将语音命令、FSM、帧状态组装为 request；当 `FuzzyCommandPolicy` 干预时，A 应将其 `feedback` 进入命令终态流程并等待确认。
- B 接收 A 的 `RouteReference`，只返回转向；其转向与 C 的 `ControlOutput` 合成后再送 D。
- D 应读取 C 的 `RiskMetrics`、`state/reason`、A watchdog，全局裁决最终 throttle/brake/steer。C 的本地紧急制动不能取代碰撞预测、侧向风险或规则评分。

## 7. 测试覆盖与已知边界

`car_control_C/tests/test_longitudinal.py` 覆盖 PID anti-windup、目标突变、参数拒绝、控制互斥和速率限制、曲率硬限速、不可达红灯全制动、四阶段停车/保持、跟车时距/TTC、非闭合前车、红黄绿未知灯、控制 JSON 及 `reset()`。`test_fuzzy_command_policy.py` 覆盖清晰透传、低置信度/歧义/显式确认、静止保持、低 TTC 升级、过期命令和严格配置序列化。A 的 `test_ac_integration.py` 覆盖 A→C→B/D 假模块链路。

边界：没有执行器标定模型或车辆动力学闭环辨识；`throttle/brake` 为归一化的确定性映射，现场必须针对 CARLA 车型和场景调参。没有横向/变道/绕障规划，没有直接读取 CARLA 信号灯或检测前车，也没有 D 的最终安全保证。`UNKNOWN` 灯在有停止线距离时保守停车，可能降低通行效率，这是明确的安全优先策略。

## 8. 常见故障定位

|现象|优先检查|
|---|---|
|速度看似过高|检查传入单位是否 m/s；确认曲率、交通、停止线和前车字段已真实填入 request|
|前车不触发 TTC|`lead_distance_m` 与 `closing_speed_mps` 必须同时提供；只有 `closing_speed_mps > 0` 才计算 TTC|
|红灯未停车|必须同时有 `distance_to_stop_line_m`，且信号状态为 `RED/YELLOW/UNKNOWN`；GREEN 明确不停车|
|持续制动影响下一场景|在 CARLA respawn 前调用 `LongitudinalController.reset()`|
|油门和刹车冲突|不要绕过 `_rate_limited_control` 手工拼 C 输出；`ControlOutput` 构造也会拒绝同时正值|
|模糊命令仍在巡航|必须先对该命令调用 `FuzzyCommandPolicy.evaluate()`，并将返回的 `decision.request` 而非原始 request 传给 controller|
|紧急制动触发过多|记录 `ttc_s`、间距、闭合速度、`emergency_ttc_s`；先修正感知/跟踪，再谨慎调参|
|CARLA 烟测无法连接|C 不启动 CARLA；确认用户已设定 `CARLA_ROOT` 并启动 `CarlaUE4.exe`，再设 `CARLA_SMOKE=1`|
