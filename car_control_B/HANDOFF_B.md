# 成员B技术交接：横向控制、路径跟踪与变道轨迹

## 1. 职责与边界

成员B负责把A提供的`VehiclePose/RuntimeVehicleState`和`RouteReference`转化为稳定的横向控制输出`steer`，并提供横向误差、航向误差、目标点等调试指标。B的目标是让车辆在直道、缓弯、常规左右转、后续变道/避让场景中平顺跟踪路线，避免蛇形、越界和严重路线偏差。

不属于B的工作：油门/刹车/速度控制（C）、最终安全仲裁/扣分评分（D）、CARLA Actor和同步生命周期（A）、语音理解/多模态决策、碰撞/红灯最终安全否决。B不直接调用`vehicle.apply_control()`，只返回`LateralOutput.steer`。

## 2. 目录与模块图

```text
A: VehicleState + RouteReference
  -> adapters.adapt_vehicle_pose / adapt_route_reference
  -> PurePursuitController.step(vehicle, reference)
       -> path_utils.find_nearest_index()
       -> path_utils.find_lookahead_index()
       -> ego-frame target point
       -> normalized steer [-1, 1]
  -> LateralOutput(steer, cte, heading_error, target_point)
  -> A 与 C 的 throttle/brake 合成 raw_control
  -> D 最终安全仲裁
  -> A 唯一 apply_control
```

| 文件 | 实际职责 |
|---|---|
| `schemas.py` | B侧数据契约：`VehiclePose`、`RouteReference`、`LateralOutput` |
| `adapters.py` | 兼容A侧dict/dataclass输入，支持`yaw_deg`转`yaw_rad` |
| `path_utils.py` | 最近点、前视点、横向误差、航向误差、路径重采样、曲率估计 |
| `lateral_controller_base.py` | 统一`step()`/`steer()`接口 |
| `pure_pursuit.py` | 主力快速可用横向控制器 |
| `stanley.py` | 备用/对照横向控制器 |
| `lane_change.py` | 简单横向偏移/变道路径生成工具，不做高层决策 |
| `demo_fake_lateral.py` | 不依赖CARLA的方向符号测试 |
| `tests/` | 无CARLA单元测试 |

## 3. 环境、运行与验证

在仓库根目录运行：

```powershell
python -m pytest car_control_B\tests -q
```

无CARLA方向符号测试：

```powershell
python -m car_control_B.demo_fake_lateral
```

预期现象：

```text
车在路径中心：steer接近0
车在路径左侧：steer为正，表示CARLA右转修正
车在路径右侧：steer为负，表示CARLA左转修正
缓弯向左：默认CARLA符号下steer为负
```

如果实际CARLA中方向相反，修改`PurePursuitParams(steer_sign=+1.0)`或统一在A的适配层取反，但不要各处同时取反。

## 4. 核心执行流程与实现要点

1. A每帧构造车辆位姿与局部参考路径。输入单位统一为m、m/s、rad；A若使用`yaw_deg`，`adapters.py`会转换为`yaw_rad`。
2. B调用`PurePursuitController.step(vehicle, reference)`，内部根据速度计算前视距离`Ld=clip(L0+k*v,Lmin,Lmax)`。
3. B寻找最近点和前视点，将前视点转到车辆坐标系，计算期望曲率和归一化`steer`。
4. B对`steer`做限幅和每帧变化率限制，避免突转和蛇形。
5. B返回`LateralOutput`，其中`steer`由A与C的`throttle/brake`合成`raw_control`，再交给D安全仲裁。
6. B不保存CARLA Actor，不推进`world.tick()`，不调用`apply_control()`。

## 5. 公开接口与字段表

| 契约/接口 | 字段或调用 | 说明 |
|---|---|---|
| `VehiclePose` | `x_m`, `y_m`, `yaw_rad`, `speed_mps`, `frame?`, `sim_time_s?` | B所需最小车辆位姿 |
| `RouteReference` | `points_xy_m`, `curvature_per_m`, `target_speed_mps`, `route_id?` | A给B的局部路径；点应为世界坐标m，最好重采样 |
| `LateralOutput` | `steer`, `cross_track_error_m`, `heading_error_rad`, `target_point_xy_m`, `lookahead_distance_m`, `status`, `reason` | B给A/D的输出；`steer`范围`[-1,1]` |
| `PurePursuitController.step` | `(VehiclePose, RouteReference) -> LateralOutput` | 主入口 |
| `LateralController.steer` | `(vehicle_state, reference) -> float` | 兼容A交接口径，只返回steer |
| `StanleyController.step` | `(VehiclePose, RouteReference) -> LateralOutput` | 对照控制器 |
| `generate_lane_change_path` | `(base_points, lateral_offset_m, ...) -> points` | 平滑变道路径工具 |

## 6. 配置、重置与生命周期

- 每个独立CARLA场景/车辆respawn前调用`controller.reset()`，清除上一次`last_steer`和最近点缓存。
- `max_steer_delta_per_step`用于限制每帧steer突变；如果急弯跟不上，先提高速度适配前视距离，再调该值。
- `steer_sign=-1.0`默认适配CARLA常见约定：正值右转、负值左转。如果实测相反，只改一处。
- 路径点距建议0.5-1.0m。A若给原始CARLA waypoint，建议先用`resample_path()`重采样。
- 速度越高前视距离越大。初始参数：`L0=2.0m`、`k=0.4s`、范围`2-8m`。

## 7. 测试覆盖、边界与交接

已覆盖：角度wrap、最近点/前视点、横向误差正负、路径重采样、Pure Pursuit方向符号、输出限幅、Stanley方向符号。

已知边界：当前模块不做真实地图路线规划，不决定何时左转/右转/变道，也不处理动态障碍物的高层避让决策。B只负责“给定一条路径，输出平顺steer并跟踪”。左右转和变道能否比赛可用，取决于A提供的局部路径是否连续、C控制的速度是否合适、D的路线偏差阈值是否一致。

交接给A：A调用`step_any(vehicle_state, route_reference)`或先适配成`VehiclePose/RouteReference`后调用`step()`。A统一合成B的`steer`与C的`throttle/brake`。

交接给C：C可读取B输出的`heading_error_rad`和`cross_track_error_m`决定弯道/横向跟踪困难时降低目标速度，但C不修改B的steer。

交接给D：D记录`steer`、`cross_track_error_m`、`heading_error_rad`、`target_point_xy_m`，用于路线偏差、动作平顺和安全接管证据。

## 8. 常见故障定位

| 现象 | 优先检查 |
|---|---|
| 左右转反了 | 只改`steer_sign`，不要在A/B/D多处取反 |
| 直道蛇形 | 前视距离太小、steer变化率太大、速度过高、路径点不均匀 |
| 转弯切弯/过冲 | 前视距离太大或速度太高，要求C在弯道限速 |
| 车不跟路线 | 检查A给的路径是否在车辆前方、坐标系是否一致 |
| 前视点落到错误支路 | 路口路径不连续或分支选择错误，应由A的RouteReference修正 |
| 横向误差忽正忽负 | 最近点跳变、路径重采样不足、yaw单位deg/rad混用 |
| D判定严重偏差 | 先看`cross_track_error_m`曲线、路径是否正确、速度是否过高 |
