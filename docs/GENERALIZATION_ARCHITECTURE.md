# 场景泛化架构与开发门禁

本文件描述 `scene_organized` 本地工作区中的泛化边界。目标不是为某个官方场景增加特判，而是让相同代码处理允许地图、天气、道路几何和 Actor 扰动。

## 五阶段边界

1. `integration/planning_stage.py`：准备并验证路线距离合同；短路线在创建 Actor 前失败。
2. `integration/scenario_builder.py`：使用路线弧长 `s`、车道关系和横向偏移创建 Actor。
3. `integration/perception_stage.py`：审计字段来源；正式 sensor 模式禁止场景真值、CARLA Actor 真值和虚拟真值进入控制。
4. `integration/execution_stage.py`：维护可处理重叠道路的单调路线进度；C/D 使用统一驾驶策略。
5. `integration/scoring_stage.py`：只从运行证据构造评分上下文，不修改控制状态。

`integration/carla_runner.py` 仍是唯一的 CARLA 生命周期与 `apply_control` 所有者，只负责编排上述阶段。

## 场景坐标合同

新场景优先为 Actor 使用：

```json
{
  "route_position": {
    "s_m": 180.0,
    "lane_relation": "RIGHT_ADJACENT",
    "lateral_offset_m": 0.2,
    "yaw_offset_deg": 0.0
  }
}
```

允许的 `lane_relation` 为 `CURRENT`、`ORIGINAL`、`LEFT_ADJACENT`、`RIGHT_ADJACENT`。旧场景的 `spawn.x/y` 自动解释为路线弧长和横向偏移，不需要逐场景重写。

路线支持三种规划合同：

- `distance_coverage`：达到声明里程并优先探索未访问、非死路拓扑；
- `destination`：使用 CARLA waypoint 图进行 A* 目的地寻路；
- `local_polyline`：仅用于明确声明的局部测试路线。

## 控制与评分隔离

- 正式控制：RGB、LiDAR、Radar、车辆状态和地图几何。
- 场景真值：Actor 触发、故障注入、验收和评分。
- Sensor 目标使用 `C-xxxx` 时序 Track ID；场景配置中的 Actor ID 不注入正式控制。
- Qwen 只输出高层行为，不能输出油门、刹车或方向盘控制量。
- `expected` 只描述评分；控制覆盖值放在 `extensions.control_policy`。

## 本地门禁

```powershell
python tools/validate_scenarios.py --root scenarios
python tools/validate_official_scenes.py
python tools/run_generalization_gate.py
python tools/run_generalization_gate.py --holdout
python -m pytest -q
```

泛化矩阵位于 `config/generalization_matrix.json`。每个基础场景生成 27 个内存变体，覆盖允许地图、天气、固定步长、随机种子、Actor 前后/横向位置及速度扰动。`holdout_scenarios` 不用于调参，只在冻结版本后运行。

## 修复准入规则

- 生产模块不得判断官方场景 ID 或具体 Town 名称；
- 修复必须作用于路线、感知、计划、控制或评分的通用合同；
- 至少加入三个几何或时序扰动回归；
- 实际驾驶失败与评分失败必须用不同 failure stage；
- 没有真实 CARLA 长里程证据时，不得把静态/单元测试通过表述为完整实车场景通过。
