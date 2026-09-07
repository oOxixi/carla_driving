# 路线规划泛化报告

## 结论

成员1的路线主链已经具备“输入起点和终点，基于 CARLA 拓扑生成完整路线”的独立能力。新路线统一输出累计里程、进度、车道关系、曲率、最近路线点、剩余距离以及终点/偏航状态；场景不需要提供 waypoint 序列或固定路口分支。

本轮没有调用 Qwen。真实地图测试所用 Python 环境只用于提供 CARLA Python SDK。

## 实现范围

- `integration/route_manager.py`
  - 缓存 `world_map.get_topology()` 图；
  - 使用确定性 A* 按终点选择路口分支；
  - 通过 road/section/lane/s 身份避免平行道路按 XY 误选；
  - 检查非驾驶车道、不可达、断路、异常跳点、回环、提前结束；
  - 返回稳定 reason code；
  - 提供 `state()`、`placement()` 和 `replan()`。
  - 提供 `local_reference()`，把任意长度全局路线裁成稳定的局部控制窗口；
  - 提供 `mission_placement()`，在重规划后继续按任务绝对 `route_s` 放置事件。
- `integration/route_planner.py`
  - 原 destination 入口改为委托 `RouteManager`，避免保留第二套 A*。
- `integration/carla_runner.py`
  - destination 模式统一从 `RouteManager` 获取路线；
  - 每帧记录 `route_state`；
  - 终点判断使用单调 `route_s/remaining`，不再在路线交叉处用全局最近点误判完成；
  - 规划失败输出 `route_planning_failed.reason/detail`。
  - 对持续偏航使用确认时间、冷却时间和最大尝试次数触发自动重规划；
  - 确认/重规划期间使用车辆当前朝向的零速临时参考安全制动，避免旧失效路线让横向控制器误报目标在车后并终止正常指令；
  - 重规划从车辆真实姿态接入前方合法车道点，成功后只解除已恢复的横向故障锁；
  - 保留单调任务里程，不因替换局部路线而把任务进度清零。
  - 全局路线只负责规划、进度和终点，B 控制器只接收约 60～100m 的滑动局部参考；窗口接近末端才刷新。
- `integration/scenario_builder.py`
  - 重规划后只重基准化 Actor/行人目标的几何 `route_s`；
  - 激活/释放触发仍使用任务全局里程；已错过事件明确返回 `ROUTE_EVENT_ALREADY_PASSED`，不夹到路线起点。
- `integration/scenario_evidence.py` / `integration/scenario_acceptance.py`
  - 持久化 `route_recovery_state`、`route_replanned`、`route_replan_failed`；
  - 验收重规划是否发生、是否真正回到路线、尝试次数是否超限。
- `car_control_A/routing.py`
  - 路线引用增加向后兼容的 `route_id` 与 `metadata`。

统一接口字段：

| 字段 | 含义 |
|---|---|
| `route_s` | 当前沿路线累计距离（m） |
| `route_progress` | 0～1 路线完成比例 |
| `route_remaining_m` | 到终点的路线剩余距离 |
| `nearest_route_point` | 最近路线参考点 |
| `road_curvature` | 当前路线局部曲率 |
| `road_id` / `lane_id` | 当前道路和车道 |
| `lane_relation` | `LEFT` / `CURRENT` / `RIGHT` / `UNKNOWN` |
| `status` | `ON_ROUTE` / `OFF_ROUTE` / `DESTINATION_REACHED` |
| `reason` | 路线异常的稳定原因码 |

成员2可直接调用 `placement(route, route_s, lane_relation)` 获取合法路线位置；目标相邻车道不存在时返回 `ROUTE_LANE_UNAVAILABLE`，不再用固定 XY 横向偏移强行生成 Actor。成员3可直接读取曲率、横向偏差、剩余距离和偏航状态。

## 真实 CARLA 路线回归

日期：2026-09-06。规划采样间隔 2m，目标速度参数 11.1m/s。以下起终点均来自地图输入，代码未针对坐标调参。

| 测试地图 | 起点 / 终点（world XY，m） | 路线长度 | 路口数 | 是否到达 | 是否错误分支 | 是否提前结束 | 失败原因 |
|---|---|---:|---:|---|---|---|---|
| Town03_Opt | (227.30,-1.59) → (-78.09,-81.24) | 1977.09m | 22 | 规划终点命中；未做全程实车 | 否 | 否 | 无 |
| Town03_Opt | (227.30,-1.59) → (-77.72,52.04) | 1843.81m | 21 | 规划终点命中；未做全程实车 | 否 | 否 | 无 |
| Town03_Opt | (-77.72,-157.59) → (-61.54,190.85) | 987.24m | 7 | 规划终点命中；未做全程实车 | 否 | 否 | 无 |
| Town05 | (-51.20,-39.57) → (30.59,-117.97) | 1996.35m | 15 | 规划终点命中；未做全程实车 | 否 | 否 | 无 |
| Town05 | (-95.24,-88.04) → (37.59,-117.87) | 2247.99m | 26 | 规划终点命中；未做全程实车 | 否 | 否 | 无 |
| Town05 | (-96.75,-84.54) → (-115.24,154.67) | 1535.02m | 15 | 规划终点命中；未做全程实车 | 否 | 否 | 无 |
| Town03_Opt | (-74.55,-148.34) → (-36.54,-194.93) | 75.70m | 0 | **实车到达** | 否 | 否 | 无 |
| Town03_Opt | 初始横向偏移约 2.50m → (-36.54,-194.93) | 重规划后 75.95m | 0 | **偏航恢复后实车到达** | 否 | 否 | 无 |

六条多路口路线的终点误差均为 0m；最大相邻路线点间距为 2.91～3.00m。Town03_Opt 短路线实车在约 15s 到达，最终 `route_s=73.96m`、剩余 1.73m、状态为 `DESTINATION_REACHED`，全程无碰撞，最大路线偏差约 0.37m。

偏航恢复夹具 `ROUTE_GEN_TOWN03_OFF_ROUTE_RECOVERY` 从约 2.50m 的持续初始偏移触发确认，确认期间安全制动，第一次重规划即成功；下一帧恢复 `ON_ROUTE`，随后到达 `DESTINATION_REACHED`。最终任务进度 72.17m、剩余 1.21m、最大车速 5.47m/s、无碰撞，`KEEP_LANE` 指令成功终态，15 项验收 `failed_keys=[]`，场景状态 `SUCCEEDED`。记录器保留了初始 `LANE_OFFSET_TOO_LARGE` 安全介入证据，但没有把它误记为未恢复的运行时看门狗故障。

局部参考窗口接入后的同场复测只刷新两次：`0.00～60.00m`（36点）与 `32.02～75.95m`（27点）；窗口切换没有造成方向跳变、停车或额外偏航。Town03_Opt 的 987.24m 路线在任务进度约 299.86m 处重规划后，任务绝对 700m 的事件被正确映射到新路线 `road_id=67/lane_id=-1`，CARLA 判定为 Driving 车道。

该恢复夹具显式允许最大车道中心偏移 3.0m，因为 2.5m 初始偏移就是测试输入；生产场景自动补充的默认 2.2m 道路贴合上限未被全局放宽。Qwen 状态为 `DISABLED`，因此结果不混入模型推理因素。

## 回归中发现并隔离的问题

1. 第一条 1.977km 实车回归在 329m 处暴露旧终点判定会在交叉道路按全局最近点跳到路线尾部。修复后，destination 路线统一使用带前向窗口的单调 `route_s` 和 `route_remaining_m` 判定终点。
2. 长路线继续运行时，车辆会在红灯前正确停车，但当前安全/运行状态在绿灯后没有恢复巡航。日志中路线仍为 `ON_ROUTE`，剩余 1175～1650m，横向误差小于 0.01m；这是控制/安全状态恢复问题，不是规划失败，应交成员3处理。
3. 随机起终点中存在有向路网不可达组合，统一返回 `ROUTE_UNREACHABLE`，而不是生成跳路或错误分支。调用方应更换合法终点或按 reason 触发重规划。

## 自动化测试

核心命令：

```bash
python -m pytest -q integration/tests/test_route_manager.py \
  integration/tests/test_route_planner.py \
  integration/tests/test_carla_runner_helpers.py

python tools/validate_route_generalization.py \
  --maps Town03_Opt Town05 --pairs-per-map 3
```

覆盖项包括：正确路口分支、拓扑缓存、不可达终点、非驾驶车道、平行车道、路线坐标、相邻车道放置、偏航确认/冷却/次数上限、真实姿态重规划接入、恢复告警隔离、恢复证据与验收、断路、回环和旧入口委托。

### Town03_Opt 结构覆盖回归

增强后的 `tools/validate_route_generalization.py` 不再只返回最先成功的几条路线，而是从候选集合中确定性选择能增加道路结构覆盖的路线，并输出未覆盖类别和所有失败 reason。

本次枚举到 120 条合法候选路线，选择 8 条做结构集：

| 覆盖 | 结果 |
|---|---|
| 直道 / 弯道 | 均覆盖 |
| 短 / 中 / 长路线 | 均覆盖 |
| 普通路口 / 多路口 | 均覆盖 |
| 多 road 路线 | 覆盖 |
| 路线长度范围 | 133.28m～4418.13m |
| 最大路口数 | 49 |
| 终点误差 | 8条均为 0m |
| 缺失必需类别 | 无 |

候选搜索过程中另有 424 个有向起终点组合返回 `ROUTE_UNREACHABLE`。工具现在完整输出尝试数、候选成功率和失败原因分布，不再用只展示成功样本的方式掩盖。该结果表示当前不做隐式非法换道时的有向车道可达性边界；调用方必须更换合法终点，不能生成跳路或逆行路线。

与成员2最新泛化提交合并后的全仓结果：`962 passed, 2 skipped, 2 failed`。两个失败仅因为本机未保存 Git 忽略的 vLLM 发布输入（38MB 源码归档和构建 wheel），不是代码测试失败；全部路线、runner、场景和控制相关测试均通过。

## 兼容边界

`planning_mode: destination` 已完全不读取 `extensions.route_anchor_spawn_index`；起点由运行输入决定，终点由 `route.destination_xy_m` 决定。仓库中既有 `distance_coverage` 长里程场景仍保留旧兼容路径，避免在成员2完成事件路线坐标化之前破坏已经通过的 S2。新增场景应优先使用 destination 模式，不再新增固定 spawn index 或人工 waypoint 分支。
