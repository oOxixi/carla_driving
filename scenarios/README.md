# CARLA 基础与 Qwen 全链路测试场景包

本包用于项目本地联调、回归测试和最终证据生成。它不是CARLA官方隐藏测试，而是用于模拟基础、进阶、挑战任务的内部标准场景库。

## 场景分层

1. `smoke/`：主链路冒烟测试  
   验证A能启动CARLA、B/C/D能被调用、D在`apply_control`前运行、日志能生成。

2. `lateral_B/`：B横向控制专项测试  
   验证Pure Pursuit/Stanley的方向符号、直道稳定性、偏移修正、缓弯、左右转和变道。

3. `safety_D/`：D安全仲裁专项测试  
   验证红灯、行人、前车急刹、路线偏差、非法控制、油门刹车冲突和低TTC强制制动。

4. `regression/`：综合回归测试  
   将基础、进阶、挑战场景混合，加入不同seed、天气、命令序列和稳定性测试。

5. `qwen_routing/`：验证简单命令不调用、复杂命令调用以及歧义命令安全确认。

6. `qwen_fullchain/`：验证 Planner V2 正常计划、编译和车辆闭环。

7. `qwen_faults/`：验证超时、低层非法输出和 D 安全抢占。

8. `acceptance_suite/`：东风赛道高质量验收套件
   包含 18 个 P0 核心、18 个 P1 变体、6 个 P2 综合和 1 个 P3 长稳场景。

9. `official_competition/`：比赛文件要求的三个正式长里程场景
   包含 S1 基础语音操控 5km、S2 复杂避障 8km、S3 极限应急 6km，以及一键验证说明。

## 使用方式

从仓库根目录先验证全部 JSON，再通过正式 runner 加载具体场景：

```bash
python tools/validate_scenarios.py
python -m integration.carla_runner --scenario-file scenarios/smoke/S01_set_speed_20.json
```

## 重要说明

所有路线点当前使用`scenario_local_xy_m`局部坐标。A的`scenario_runner`接入CARLA时，需要做以下二选一：

1. 把局部坐标转换成CARLA世界坐标；
2. 根据CARLA地图waypoint重新生成车道中心线，再把场景的局部路线作为形状模板。

不能保证直接把这些局部坐标塞进Town03就一定落在车道中心线上。

## 推荐测试顺序

先跑：

```text
smoke/S00_chain_start.json
smoke/S01_set_speed_20.json
smoke/S03_stop.json
smoke/S04_emergency_stop.json
```

再跑B专项：

```text
lateral_B/B01_straight_center.json
lateral_B/B02_straight_left_offset.json
lateral_B/B03_straight_right_offset.json
lateral_B/B04_smooth_left_curve.json
lateral_B/B05_smooth_right_curve.json
lateral_B/B06_left_turn.json
lateral_B/B07_right_turn.json
lateral_B/B08_lane_change_left.json
lateral_B/B09_lane_change_right.json
```

再跑D专项：

```text
safety_D/D01_red_light_stop.json
safety_D/D02_pedestrian_crossing.json
safety_D/D03_front_vehicle_brake.json
safety_D/D07_low_ttc_emergency_brake.json
```

最后跑`regression/`里的综合回归。

东风赛道验收套件的清单、成熟度和执行方式见
`acceptance_suite/README.md` 与 `acceptance_suite/matrix.json`。

## 每个场景必须生成的证据

每次运行一个场景，建议写到：

```text
artifacts/logs/<scenario_id>/frame_log.jsonl
artifacts/logs/<scenario_id>/event_log.jsonl
artifacts/logs/<scenario_id>/result.json
artifacts/logs/<scenario_id>/score_report.json
```

`frame_log.jsonl`至少包含：

```text
scenario_id, frame, sim_time_s, command_id,
vehicle_state, B_lateral, C_longitudinal,
raw_control, D_safety, final_control
```

运行证据不提交到 `scenarios/`；场景 JSON 只在完成 schema、静态合同和实车冒烟验证后修改。
