# 路线、横向跟踪与完成里程

上级：[路线与横向模块](../modules/vehicle-lateral.md)。

## 三个量不要混用

路线几何决定“往哪里开”；route progress 表示沿参考线的投影进展；distance coverage 表示实际移动距离。回环、重叠路线、瞬移或偏离道路时，这些数值可能不同，不能用较大的一个替代另一个提高完成率。

## 现有实现职责

[planning_stage](../../../integration/planning_stage.py) 验证路线合同；[route_manager](../../../integration/route_manager.py) 维护当前路线；[route_planner](../../../integration/route_planner.py) 与 [route_geometry](../../../integration/route_geometry.py) 提供几何/规划支持；[execution_stage](../../../integration/execution_stage.py) 分开维护 RouteProgressTracker 和 DistanceCoverageTracker。

B 控制器经 adapt_vehicle_pose/adapt_route_reference 接收统一姿态与路径，Pure Pursuit 或 Stanley 返回归一化 steer 和 status。lane_change 用平滑横向路径过渡，不直接输出另一套车辆控制。

## 改横向行为时容易漏的依赖

- 改最近点搜索或路线进度同步，需要验证交叉/回环路段，防止跳到未来段。
- 改前视距离、曲率或 steer 限制，需要看 C 使用的前方曲率限速；横向和纵向不是完全独立。
- 新路线被切换后，控制器的历史 nearest index/舵量状态应按现有 reset/synchronize 行为处理，不能让旧索引落到新路径。
- 无效路径返回状态会在 ControlRuntime 中转成锁存告警和制动；算法不能只返回 0 steer 冒充 OK。

验证：[B tests](../../../car_control_B/tests)、[route manager tests](../../../integration/tests/test_route_manager.py)、[route planner tests](../../../integration/tests/test_route_planner.py)、[scenario execution tests](../../../integration/tests/test_scenario_execution.py)。真实闭环验证还应记录偏移、压线、路线偏差、实际里程与控制限制，不能只比较 steer 数值。
