# Day23 Qwen 高层决策联调交接说明

## 1. 文档目的

本文档用于第一组与第二组完成 7 月 23 日最终 CARLA 联调。

按照任务分工：

- 第一组负责固定 Qwen 提示词、动作范围和输出协议；
- 第一组负责提供最终版高层决策结果；
- 第二组负责 CARLA 场景复现和车辆控制执行；
- 第一组配合第二组核对“Qwen 输入、Qwen 判断、最终车辆动作”是否一致。

第一组不需要单独在本机重新部署完整模型和 CARLA 环境。最终真实场景由第二组运行，第一组负责提供代码、协议、解释材料和结果核对。

## 2. 小组职责

### 2.1 第一组职责

第一组负责：

- 接收驾驶员自然语言指令；
- 接收 RGB 图像和 SceneState；
- 使用 Qwen 完成多模态语义理解；
- 生成统一的高层驾驶动作；
- 固定最终提示词；
- 固定动作白名单；
- 固定 JSON 输出格式；
- 校验 Qwen 输出是否合法；
- 向第二组提供最终高层决策结果；
- 核对高层决策与最终车辆动作是否一致；
- 准备模型选型、能力边界和答辩说明。

### 2.2 第二组职责

第二组负责：

- 拉取第一组提供的最终联调代码；
- 接收 Qwen 输出的高层驾驶动作；
- 将高层动作转换为车辆可执行目标；
- 运行最终 CARLA 场景；
- 执行车辆方向、油门和制动控制；
- 完成最终一轮场景复现；
- 保存控制结果和演示材料；
- 将联调产物返回第一组核对。

### 2.3 安全模块职责

安全模块负责：

- 检查当前驾驶意图是否安全；
- 在危险场景下覆盖不安全的高层动作；
- 对最终车辆控制进行安全仲裁；
- 在驾驶员指令、Qwen 判断和安全状态冲突时优先保证安全。

安全模块拥有最终仲裁权。

## 3. 代码版本

联调分支：

```text
feat/day23-qwen-finalization
```

关键提交：

```text
60e4ac6 test: enforce Qwen high-level action protocol
92da3cf feat: finalize Qwen decision prompt
7285020 feat: add Qwen decision trace
e24f82e feat: record closed-loop Qwen decision trace
```

第二组拉取命令：

```bash
git fetch origin
git switch feat/day23-qwen-finalization
git pull origin feat/day23-qwen-finalization
```

拉取后检查：

```bash
git status
git log -4 --oneline
```

预期工作区状态：

```text
nothing to commit, working tree clean
```

## 4. 联调前测试

第二组在仓库根目录运行：

```bash
python -m pytest -q integration/tests/test_day23_decision_trace.py integration/tests/test_day23_qwen_prompt.py integration/tests/test_day23_qwen_protocol.py integration/tests/test_day20_control_adapter.py
```

当前预期结果：

```text
17 passed
```

如果测试失败，应先解决代码或环境问题，再运行最终 CARLA 场景。

## 5. 第一组向第二组提供的输入

Qwen 高层决策模块使用三类输入：

1. 驾驶员自然语言指令；
2. RGB 摄像头图像；
3. SceneState 结构化环境状态。

SceneState 可包含：

- 当前帧号；
- 自车速度；
- 自车车道；
- 自车位置；
- 周围车辆；
- 行人；
- 障碍物；
- 目标距离；
- 目标方向；
- 道路和安全状态。

示例：

```json
{
  "frame_id": 100,
  "ego": {
    "speed_kmh": 18.0,
    "lane_id": 1
  },
  "objects": [
    {
      "object_id": "vehicle_12",
      "category": "vehicle",
      "distance_m": 10.0,
      "direction": "front"
    }
  ]
}
```

最终联调时需要记录：

- 驾驶员指令；
- RGB 图像或对应帧号；
- SceneState；
- 地图和场景名称；
- 使用的模型名称；
- 模型精度或量化方式；
- Git 分支和提交号。

## 6. Qwen 输出协议

Qwen 只能输出以下高层动作：

```text
START
STOP
SET_SPEED
TURN_LEFT
TURN_RIGHT
CHANGE_LANE_LEFT
CHANGE_LANE_RIGHT
AVOID_OBJECT
EMERGENCY_BRAKE
RETURN_TO_LANE
```

统一输出格式：

```json
{
  "actions": [
    {
      "action": "SET_SPEED",
      "target_id": "vehicle_12",
      "target_speed_kmh": 10.0
    }
  ],
  "confidence": 0.9,
  "reason": "前方车辆减速，需要降低目标速度"
}
```

字段说明：

- `actions`：高层动作列表；
- `action`：动作白名单中的动作；
- `target_id`：SceneState 中真实存在的目标；
- `target_speed_kmh`：目标速度；
- `confidence`：模型对判断的置信度；
- `reason`：简短的决策依据。

`actions` 至少包含一个有效动作。

## 7. Qwen 控制边界

Qwen 只负责高层理解和决策。

Qwen 禁止直接输出：

```text
throttle
brake
steer
方向盘角度
油门值
制动力
```

Qwen 不负责：

- 直接控制方向盘；
- 直接控制油门；
- 直接控制刹车；
- 计算高频连续控制量；
- 绕过车辆执行模块；
- 绕过安全模块；
- 独立完成端到端自动驾驶。

正确控制链路为：

```text
驾驶员指令
→ RGB 图像与 SceneState
→ Qwen 高层决策
→ 输出协议校验
→ 安全过滤
→ 第二组车辆执行模块
→ 底层车辆控制
→ 最终安全仲裁
→ CARLA 车辆动作
```

## 8. 联调执行流程

建议第二组按照以下步骤执行：

1. 拉取第一组最终分支；
2. 运行 17 个相关测试；
3. 确认模型和 CARLA 环境可用；
4. 启动固定 CARLA 场景；
5. 输入约定的驾驶员指令；
6. 保存对应 RGB 图像和 SceneState；
7. 运行 Qwen 高层决策；
8. 将高层动作交给车辆执行模块；
9. 记录最终车辆动作；
10. 将联调结果返回第一组；
11. 第一组核对完整决策链。

## 9. 联调输出文件

完成一次闭环场景后，应保存以下文件：

```text
artifacts/day20/qwen_raw_output.json
artifacts/day20/driving_intent.json
artifacts/day20/executor_target.json
artifacts/day20/carla_control.json
artifacts/day20/decision_trace.json
```

文件含义：

### `qwen_raw_output.json`

记录 Qwen 原始输出。

### `driving_intent.json`

记录解析和校验后的高层驾驶意图。

### `executor_target.json`

记录第二组执行模块生成的车辆目标。

### `carla_control.json`

记录最终车辆控制结果，例如：

```json
{
  "target_speed_kmh": 10.0,
  "control": {
    "throttle": 0.0,
    "brake": 0.35,
    "steer": 0.0
  },
  "safety_override": false
}
```

### `decision_trace.json`

汇总完整决策链，是第一组最终核对的主要文件。

## 10. 一致性验收标准

正常联调结果应满足：

```json
{
  "consistency": {
    "qwen_to_executor": true,
    "executor_to_controller": true,
    "final_control_recorded": true,
    "safety_override": false,
    "status": "CONSISTENT"
  }
}
```

含义：

- Qwen 高层动作已正确传入执行模块；
- 执行模块目标已正确传入控制模块；
- 最终车辆动作已被记录；
- 没有发生额外安全覆盖；
- 决策链整体一致。

发生安全接管时，可以出现：

```json
{
  "consistency": {
    "qwen_to_executor": true,
    "executor_to_controller": true,
    "final_control_recorded": true,
    "safety_override": true,
    "status": "CONSISTENT_WITH_SAFETY_OVERRIDE"
  }
}
```

`CONSISTENT_WITH_SAFETY_OVERRIDE` 不代表 Qwen 运行失败。

它表示：

- Qwen 高层决策已经进入控制链；
- 执行模块已经正确处理高层动作；
- 安全模块根据实时风险覆盖了最终动作；
- 系统仍然按照设计正常工作。

## 11. 不能通过验收的情况

以下情况不能通过验收：

- Qwen 输出动作白名单之外的动作；
- Qwen 输出 `throttle`、`brake` 或 `steer`；
- Qwen 输出无法解析的格式；
- Qwen 没有生成有效动作；
- Qwen 编造 SceneState 中不存在的 `target_id`；
- 高层动作没有传入第二组执行模块；
- 执行器目标与控制模块目标不一致；
- 最终车辆动作没有记录；
- 无法说明安全模块是否发生接管；
- 演示场景与保存的输入输出无法对应。

## 12. 推荐最终复现场景

推荐使用“前车减速”固定场景。

驾驶员指令：

```text
前方车辆减速，请降低速度并保持安全距离。
```

正常情况下，Qwen 可输出：

```text
SET_SPEED
```

存在明确紧急碰撞风险时，可以输出：

```text
EMERGENCY_BRAKE
```

预期执行过程：

1. Qwen 根据语言、RGB 图像和 SceneState 判断前方风险；
2. Qwen 输出高层减速或紧急制动动作；
3. 第二组将高层动作转换为目标速度；
4. 底层控制模块计算实际油门、制动和方向；
5. 安全模块保留最终覆盖权；
6. `decision_trace.json` 记录完整过程。

## 13. 第二组需要返回第一组的材料

第二组完成最终场景后，请返回：

1. `qwen_raw_output.json`；
2. `driving_intent.json`；
3. `executor_target.json`；
4. `carla_control.json`；
5. `decision_trace.json`；
6. 演示截图或录屏；
7. CARLA 地图名称；
8. 场景名称；
9. 驾驶员指令；
10. 使用的模型名称和版本；
11. 模型推理精度或量化方式；
12. 使用的代码分支和提交号；
13. 是否发生安全模块接管；
14. 联调过程中遇到的问题和处理方式。

模型文件、运行产物和大量 RGB 图片原则上不要提交到 Git 仓库。

## 14. 第一组核对清单

收到第二组材料后，第一组检查：

- Qwen 输入是否与演示场景一致；
- Qwen 输出是否符合动作白名单；
- JSON 格式是否统一；
- Qwen 是否输出底层控制量；
- `target_id` 是否真实存在；
- Qwen 判断是否传入执行模块；
- 执行器目标是否传入控制模块；
- 最终车辆动作是否已记录；
- 是否发生安全接管；
- 安全接管是否符合场景风险；
- 演示截图、输入和输出是否能够相互对应。

## 15. 答辩统一表述

本项目中的 Qwen 是高层语义理解和多模态行为决策模块。

Qwen 融合驾驶员自然语言指令、RGB 图像和 SceneState，生成有限动作集合内的高层 DrivingIntent。

Qwen 不直接输出方向盘、油门和制动控制量。高层动作由车辆执行模块转换为车辆目标，再由底层控制模块和安全模块生成最终车辆控制。

因此，本项目不是使用大模型直接完成端到端自动驾驶，而是将多模态大模型作为可解释、可约束的高层决策组件。
