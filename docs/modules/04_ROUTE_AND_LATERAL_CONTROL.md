# 04 路线与横向控制

## 1. 模块目标

本模块把“车辆沿什么路线走”和“当前帧如何产生横向转向量”连成一条可审计链路，范围包括：

- 从 CARLA 地图拓扑生成终点路线或距离覆盖路线；
- 用统一的路线弧长坐标表示车辆进度、场景事件位置和剩余里程；
- 在路线交叉、回环、临时绕行和重规划时保持单调任务进度；
- 从全局路线裁出局部参考窗，供横向控制器逐帧跟踪；
- 通过 Pure Pursuit 计算主用转向量，并保留 Stanley 作为独立对照实现；
- 将无效横向参考转换为稳定 reason code，并交给运行时安全闭环处理。

本模块不负责纵向油门/制动、危险物识别、Qwen 指令理解、最终安全仲裁和场景评分。横向控制器只能输出 `steer`，不能直接调用 CARLA `apply_control`。

## 2. 状态快照

| 项目 | 本轮核对结果 |
|---|---|
| 核对分支 | `challenge` |
| 核对基线 | `ee94fab6f899b319f852939e3c5e969fb71f9f64` |
| 核对日期 | 2026-09-21 |
| 主路线实现 | `integration/route_manager.py` |
| 路线兼容/场景构造 | `integration/route_planner.py`、`integration/route_geometry.py` |
| 主横向控制器 | `car_control_B/pure_pursuit.py` |
| 对照控制器 | `car_control_B/stanley.py`；未接入生产自动切换 |
| 生产组合点 | `integration/carla_runner.py` → `integration/runtime_loop.py` |
| 参数来源 | `config/strategy_config.yaml` → `config/strategy.py` |
| 当前结论 | 代码主链、失败语义和自动化覆盖均存在；本轮完成静态精读、编译和文档检查，不新增 CARLA 实车结论 |

历史 CARLA 路线回归见 `docs/reports/route_generalization.md`。该报告中的日期、地图和结果是历史证据，不等同于本轮重新实车验证。

## 3. 上下游合同

### 3.1 路线输入与输出

`RouteManager` 接收 CARLA `world_map`、起点、终点或距离合同、目标速度，输出 `GlobalRoute`：

| 字段 | 单位/取值 | 语义 |
|---|---|---|
| `reference.points_xy_m` | world/map m | 至少两个有限点的路线折线 |
| `reference.curvature_per_m` | 1/m | 路线曲率摘要 |
| `reference.target_speed_mps` | m/s | 调度提示；横向模块不拥有纵向执行权 |
| `reference.route_id` | string | 路线身份，用于切换和证据关联 |
| `samples[*].s_m` | m | 全局路线累计弧长 |
| `validation` | object | 长度、点数、最大间距、终点误差、重复点和路口数 |

路线状态由 `RouteManager.state()` 输出：`route_s`、`route_progress`、`route_remaining_m`、横向偏差、曲率、道路/车道身份、相邻车道、终点状态和是否需要重规划。调用者必须把上一帧 `route_s` 作为 `previous_s_m` 传回，才能在交叉和重叠路线中保持单调进度。

### 3.2 横向控制输入与输出

`car_control_B.schemas` 定义严格数据合同：

- `VehiclePose`：`x_m/y_m/yaw_rad/speed_mps`，速度不得为负；
- `RouteReference`：至少两个 world/map 米制点，曲率和目标速度必须有限；
- `LateralOutput`：`steer` 必须在 `[-1, 1]`，同时输出横向误差、航向误差、目标点、前视距离和索引；
- `status/reason`：正常为 `OK/PURE_PURSUIT`；目标点落在车后时为 `INVALID/TARGET_BEHIND_EGO`。

生产路线由 `car_control_A.routing.RouteReference` 生成，B 层入口 `LateralController.step_any()`
把该对象适配成 B 层严格 `RouteReference`，并按源点容器缓存转换结果。因此当前是“两套同形
合同 + 显式 adapter”，不是同一个 Python 类型；该边界将在第 9 项“接口与坐标转换”继续核对。

坐标约定必须统一：CARLA 车体局部 `+x` 向前，代码把局部 `+y` 解释为地图右侧；正横向误差表示车辆位于路线右侧。当前 Model 3 标定使用 `steer_sign=1.0`，不能仅凭画面主观判断反转符号。

### 3.3 失败语义

规划失败使用 `RoutePlanningError(code, detail, context)`，而不是返回一条看似可走的替代直线。核心 reason code 包括：

- `ROUTE_START_UNMAPPABLE` / `ROUTE_DESTINATION_UNMAPPABLE`；
- `ROUTE_UNREACHABLE`；
- `ROUTE_DISCONTINUOUS` / `ROUTE_LOOP_DETECTED` / `ROUTE_ENDED_EARLY`；
- `ROUTE_LANE_CHANGE_UNAVAILABLE` / `ROUTE_LANE_CHANGE_SEQUENCE_INVALID`；
- `ROUTE_NO_COMPATIBLE_ANCHOR` / `ROUTE_LANE_UNAVAILABLE`；
- `ROUTE_EVENT_ALREADY_PASSED` / `ROUTE_EVENT_BEYOND_ACTIVE_ROUTE`。

`ControlRuntime.step()` 若收到非 `OK` 横向结果，会锁存 `LATERAL_<reason>`，把请求速度置零并终止当前指令。偏航恢复成功时，runner 只清除 `LATERAL_` 前缀故障，不清除无关安全故障。

## 4. 真实调用链

```text
场景 route contract / CARLA map
  -> carla_runner 选择 destination 或 topology_coverage
  -> RouteManager.plan(...) / plan_distance(...)
  -> GlobalRoute + RouteValidation
  -> 每帧 RouteManager.state(previous_s_m=上一帧 route_s)
  -> RouteManager.local_reference(lookbehind/lookahead)
  -> ControlRuntime.step(vehicle, scene, effective_route)
  -> PurePursuitController.step_any(...)
  -> LateralOutput
  -> 纵向控制 + SafetySupervisor
  -> 唯一最终 VehicleControl
```

生产 runner 通过 `_acceptance_lateral_controller()` 固定创建 Pure Pursuit：普通帧最近点搜索窗口为 2 个采样点，恢复长期路线时的重新捕获窗口为 50 个采样点。全局路线不会每帧整条交给控制器；runner 按速度裁出约 60 m 以上的前向局部窗口，并在靠近窗口末端时刷新。

临时变道/转向路线完成后：

- 距离覆盖任务从车辆当前真实姿态规划剩余里程的 continuation；
- 终点任务恢复保留的 mission route，并用 `synchronize_route_progress()` 对齐外部单调进度；
- 两种路径切换都避免重新从整条重叠路线做无界最近点搜索；
- continuation 使用 `reset(preserve_steer=True)`，保留上一帧转向量并继续受转向变化率限制。

## 5. 路线规划实现映射

### 5.1 全局拓扑路线

`RouteManager.plan()` 把起点/终点投影到驾驶车道，缓存 `world_map.get_topology()`，用 road/section/lane/s 身份构图并确定性搜索。合法换道边要求同向驾驶车道和 CARLA 车道线许可；不可执行的换道连接会被屏蔽并重新搜索，耗尽后才明确失败。

`integration/route_planner.build_destination_route_reference()` 只是兼容入口，直接委托 `RouteManager`，没有保留第二套目的地 A*。

### 5.2 8 km 距离覆盖路线

`RouteManager.plan_distance()` 根据已访问拓扑和后续新颖容量选择分支，允许为了满足距离合同再次经过合法拓扑，但不隐式换道。`plan_distance_compatible()` 可依次尝试候选起点，并在生成后检查：

- 指定里程窗口内是否存在左/右相邻同向车道；
- 是否要求无路口换道走廊；
- 指定速度窗口在曲率和最大横向加速度下是否可实现。

该兼容检查用于在生成阶段拒绝“不可能完成场景合同”的路线，而不是运行中用硬编码场景 ID 修补。

### 5.3 单调进度与路线相对位置

`integration/route_geometry.py` 统一完成：

- 折线累计弧长和任意 `s_m` 的插值姿态；
- 按路线切线生成左右横向偏移；
- 把新式 `route_position` 和旧式 actor `spawn.x/y` 统一解释为路线弧长/横向偏移；
- 使用 `previous_s_m`、后退容差和前向窗口解决自交路线的投影歧义；
- 输出路线长度、最大步长、空间唯一性和距离合同完成质量。

`mission_placement()` 把任务绝对里程减去重规划前累计偏移，避免重规划后事件重新从 0 km 触发；已经错过或超出新路线的事件会明确失败。

### 5.4 偏航恢复

`RouteRecoveryTracker` 采用四个地图无关参数：偏航阈值、确认时间、重试冷却和最大次数。主动变道/绕行时传入 `recovery_suppressed=True`，避免把预期横移误判成路线故障。

确认和重规划期间，runner 使用车辆当前朝向构造零速前向参考并安全制动。成功后：

1. 更新全局路线和任务里程偏移；
2. 清空局部参考缓存和 actor 几何进度缓存；
3. 恢复重规划前的目标速度；
4. 只解除已经恢复的横向告警；
5. 记录 `route_replanned` 证据。

## 6. 横向控制实现映射

### 6.1 Pure Pursuit 主控制器

控制器先在受限窗口内寻找最近点，再计算路线航向、线段投影横向误差和前方局部最大曲率。前视距离为：

```text
Ld = clip(
  (base_lookahead + speed_gain * speed)
  / (1 + curvature_gain * |curvature|
       + error_gain * (|cte| + wheel_base * |heading_error|)),
  min_lookahead,
  max_lookahead
)
```

随后将目标点变换到车体坐标，计算 Pure Pursuit 曲率前馈，并叠加带速度软化的横向误差反馈。最终转向同时受速度/曲率相关幅值限制和每帧变化率限制。目标点位于车后时不静默输出“正常零转向”，而是返回 `INVALID/TARGET_BEHIND_EGO` 交给上层失败关闭。

控制器按实际 `points_xy_m` 容器保存各条路线进度，不能只用 Python `id()`，否则临时路线释放后地址复用会错误继承进度。当前实现会在一次任务中保留接触过的路线容器和索引；长时间产生大量短期唯一路线时内存上界尚未显式配置，见阻塞项 RLC-03。

### 6.2 Stanley 对照控制器

`StanleyController` 实现航向误差与横向误差反馈、速度软化、曲率增益、转向幅值和变化率限制。它有独立单元测试，但生产 runner 没有自动 Pure Pursuit→Stanley 降级逻辑。因此文档只能称其为“对照/备用实现”，不能称为运行时冗余控制器。

### 6.3 变道几何

存在两类辅助实现：

- `car_control_B/lane_change.py`：对一般折线重采样后使用五次 smoothstep 生成平滑横向偏移；
- `integration/route_planner.py`：面向 CARLA 拓扑逐点匹配源车道和相邻车道，检查同向驾驶车道、路口和稳定段，再生成可执行的变道路线。

生产 CARLA 场景使用后者。前者是纯几何工具，不包含车道线合法性，不能单独证明道路上的变道可执行。

## 7. 当前参数

参数单一来源是 `config/strategy_config.yaml`，由 `config/strategy.py` 做字段全集和数值校验。关键默认值：

| 参数 | 当前值 | 作用 |
|---|---:|---|
| `wheel_base_m` | 2.8 | 自行车模型轴距 |
| `base_lookahead_m` / `speed_gain_s` | 2.5 / 0.45 | 基础及速度相关前视 |
| `min_lookahead_m` / `max_lookahead_m` | 2.5 / 8.0 | 前视范围 |
| `max_steer_angle_rad` | 0.60 | 归一化转向尺度 |
| `max_steer` / `min_steer_limit` | 0.60 / 0.35 | 动态转向限幅边界 |
| `base_steer_delta_per_step` | 0.038 | 基础单帧转向变化上限 |
| `steer_sign` | 1.0 | CARLA 0.9.16 Model 3 标定符号 |
| `stanley_gain` / `stanley_softening_speed_mps` | 0.8 / 1.0 | Stanley 对照参数 |

这些是控制策略配置，不是场景专属常量。runner 的最近点窗口 `2/50` 仍写在 `_acceptance_lateral_controller()` 中，尚未进入统一配置，见 RLC-02。

## 8. 自动化验证

本模块的直接测试面包括：

| 测试文件 | 测试数 | 主要覆盖 |
|---|---:|---|
| `car_control_B/tests/test_pure_pursuit.py` | 13 | 符号、限幅、曲率前视、误差反馈、重叠路线、临时路线恢复、adapter 缓存 |
| `car_control_B/tests/test_stanley.py` | 2 | 左右偏差纠正方向 |
| `integration/tests/test_route_geometry.py` | 7 | 弧长、插值、偏移、自交单调投影、质量 |
| `integration/tests/test_route_planner.py` | 15 | 路口分支、变道、朝向兼容、路线构造 |
| `integration/tests/test_route_manager.py` | 22 | A*、覆盖路线、合同兼容、失败码、状态、重规划、局部窗 |
| `integration/tests/test_carla_runner_helpers.py` | 131（全文件） | runner 辅助合同；其中包含路线恢复、局部窗、动态返回、闭环转向等交叉覆盖 |

最小回归命令：

```bash
python -m pytest -q \
  car_control_B/tests/test_pure_pursuit.py \
  car_control_B/tests/test_stanley.py \
  integration/tests/test_route_geometry.py \
  integration/tests/test_route_planner.py \
  integration/tests/test_route_manager.py
```

完整 runner 交叉回归另执行：

```bash
python -m pytest -q integration/tests/test_carla_runner_helpers.py
```

真实地图结构泛化入口是 `tools/validate_route_generalization.py`；它依赖可用 CARLA 地图环境，不能用纯 Python 单元测试结果替代。

## 9. 精读发现与阻塞项

| ID | 级别 | 当前事实 | 关闭条件 |
|---|---|---|---|
| RLC-01 | 边界说明 | Stanley 存在但生产 runner 始终实例化 Pure Pursuit | 若要声称冗余控制，必须定义切换条件、状态迁移、失败关闭和 CARLA 回归；否则继续明确标注“对照实现” |
| RLC-02 | 配置一致性 | `nearest_search_window=2`、`route_reacquire_search_window=50` 写在 runner，而非统一策略配置 | 将字段纳入严格配置 schema，补默认值/非法值/生产装配测试 |
| RLC-03 | 长时资源 | Pure Pursuit 的 `_route_progress` 会保留每个真实路线容器，没有显式容量或淘汰策略 | 建立可证明不破坏路线恢复语义的上界，并加入大量临时路线压力测试 |
| RLC-04 | 证据等级 | 历史报告有 Town03_Opt/Town05 实车结果，本轮没有重新运行 CARLA | 固定提交、CARLA 版本、场景配置和原始日志后重跑，生成新的可追溯证据包 |
| RLC-05 | 合同可变性 | `RouteReference` 是 frozen dataclass，但 `points_xy_m` 和 `metadata` 内部仍是可变对象 | 决定是否升级为不可变 tuple/mapping；若升级需提供兼容 adapter 和全链回归 |

上述项目不是当前链路“未实现”的同义词：RLC-01/02/03/05 是工程边界或加固项，RLC-04 是证据刷新项。不得为了清零表格而删除失败测试或把历史结果改写为当前结果。

## 10. 修改约束

后续优化必须满足：

1. 不按 scenario ID、固定 spawn 或固定坐标写控制阈值；
2. 路线交叉/回环仍通过单调弧长和有界窗口处理；
3. 变道合法性由地图拓扑与车道线权限决定，不能只做 XY 平移；
4. 重规划不能重置任务绝对里程或重复触发已完成事件；
5. 路线切换不能跳过转向变化率限制；
6. 横向异常必须进入安全失败语义，不能伪装为 `OK`；
7. 调参应修改统一配置并覆盖直道、弯道、路口、变道、重叠路线和恢复测试。

## 11. 完成定义

本轮“模块精读完成”要求：

- 已定位生产入口、调用链、数据合同、坐标约定和参数来源；
- 已区分主实现、兼容入口、对照实现和历史证据；
- 已列出稳定失败语义及安全闭环行为；
- 已给出可执行的最小回归和真实地图泛化入口；
- 已把所有未关闭问题改写成带 ID 和关闭条件的阻塞项；
- 本轮验证结果记录在提交说明中，不在执行前预写为 PASS。

这一定义只关闭第 4 项“路线与横向控制”的文档占位，不代表 RLC-01～RLC-05 已全部完成，也不代表挑战赛道已完成实车验收。
