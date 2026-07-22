# 车辆控制组成员 C 交接文档（YQQ，2026-07-22）

## 1. 交接概况

| 项目 | 内容 |
|---|---|
| 负责角色 | 成员 C：纵向控制、停车/跟车/TTC、RGB + LiDAR 保守融合 |
| 工作分支 | `carla_driving_rstar` |
| 已交付提交 | `f5671b0e3fcda9a432585f0ce114ef37dff26c65` |
| 提交说明 | `feat: complete role C perception safety integration` |
| 远端地址 | <https://github.com/oOxixi/carla_driving/tree/carla_driving_rstar> |
| 当前状态 | 代码、单元测试、集成测试和确定性验收证据已完成并推送；真实 CARLA + 实际 ONNX 模型联机验收待完成 |

## 2. 本次完成内容

### 2.1 纵向控制链路

- 保留并验证现有速度 PID、多约束限速、停车状态机、时距跟车和 TTC 紧急制动逻辑。
- 纵向目标会同时受命令速度、道路限速、曲率、停止线和前车约束，最终取最保守的速度上界。
- 停车支持 `DECELERATE -> CREEP -> HOLD`，不可达停止条件或低 TTC 会进入紧急制动。
- 油门与制动保持互斥，输出带变化率限制；每个新 episode/车辆重生后必须调用 `reset()`。

### 2.2 RGB + LiDAR 保守融合

- 新增 `ConservativeSensorFusion`，统一输出视觉、LiDAR 和融合状态的有效性、来源、前向距离、闭合速度、TTC、建议动作及原因。
- RGB 缺失或置信度不足时不编造目标类别，仍允许 LiDAR 独立触发减速或制动。
- RGB 已确认中央走廊危险目标但 LiDAR 无有效距离时，输出 `FULL_BRAKE / visual_hazard_without_range`。
- LiDAR 发现障碍而 RGB 漏检时，保留 `LIDAR_ONLY` 障碍，并按静止障碍进行保守处理。
- 传感器帧异常、检测器加载失败或推理失败时采用 fail-closed 策略，不允许正常推进。

### 2.3 ONNX 检测器接入

- 兼容合入上游 `ef7950a` 的 RGB ONNX 检测改进，没有覆盖当前分支已有的场景运行和证据链路。
- 新增 Ultralytics 风格 YOLO ONNX 解码、置信度过滤、NMS、道路参与者类别过滤和中央走廊筛选。
- 保留类别：`person`、`bicycle`、`car`、`motorcycle`、`bus`、`truck`。
- ONNX Runtime 使用延迟导入；未设置 `--rgb-detector-model` 时走原有默认流程。
- 模型权重未提交到 Git，需由接手人放入本地忽略路径，例如 `artifacts/models/yolo11n.onnx`。

### 2.4 运行时与证据链路

- `CarlaPerceptionBridge` 可选接入 ONNX 检测器，并将 RGB 检测结果与严格同帧 LiDAR 距离关联。
- `PerceptionFrame` 新增 `detected_objects`；默认值为空元组，仓库内旧调用保持兼容。
- 帧日志和场景证据新增 `c_safety_state`，可审计感知有效性、字段来源、TTC 和安全动作。
- 新增 C 角色确定性验收脚本与证据文件，可在没有 CARLA 服务的环境中复现。

## 3. 核心文件

| 文件 | 作用 |
|---|---|
| `car_control_C/safety_state.py` | RGB/LiDAR 有效性、来源、距离、闭合速度、TTC 和安全动作的保守融合 |
| `car_control_C/longitudinal_controller.py` | C 组纵向控制主入口，组合规划、PID、紧急制动及执行器输出 |
| `car_control_C/speed_planner.py` | 命令速度、曲率、交通规则、停车和前车约束融合 |
| `car_control_C/stop_controller.py` | 分阶段停车和静止保持 |
| `car_control_C/following_controller.py` | 时距、期望间距、前车速度上界和 TTC 风险 |
| `integration/rgb_detector.py` | ONNX 模型加载、YOLO 输出解码、NMS 和中央走廊目标过滤 |
| `integration/carla_perception.py` | CARLA RGB/LiDAR 同帧采集、目标与距离关联、安全状态输出 |
| `integration/carla_runner.py` | ONNX 参数入口、安全状态日志和 fail-closed 告警接入 |
| `integration/contracts.py` | `DetectedObject`、`PerceptionFrame.detected_objects` 等共享契约 |
| `integration/scenario_evidence.py` | 将 `c_safety_state` 写入场景 JSONL 证据 |
| `integration/RGB_ONNX.md` | ONNX 安装、模型放置和真实传感器运行说明 |
| `tools/validate_c_role.py` | 生成 C 角色停车曲线、TTC 样本和故障注入证据 |
| `artifacts/C_role_validation/` | 已生成的确定性验收结果 |

## 4. 关键数据流与接口

```text
CARLA RGB 帧 -> OnnxYoloDetector -> DetectedObject[]
                                           \
CARLA LiDAR 帧 -> 前向走廊距离 ------------> ConservativeSensorFusion
                                             -> SafetyStateSummary
                                             -> C 纵向控制 / D 最终仲裁
                                             -> c_safety_state 日志
```

`SafetyStateSummary` 需要重点关注以下字段：

| 字段 | 含义 |
|---|---|
| `visual_valid` | RGB 语义是否有效，低置信度不算有效 |
| `lidar_valid` | LiDAR 前向距离是否有效 |
| `fused_valid` | 当前是否形成可用融合状态 |
| `source_by_field` | 各输出字段的真实来源，答辩和排障时必须保留 |
| `front_distance_m` | 前向目标距离，单位 m |
| `closing_speed_mps` | `ego - lead`，正值代表正在接近 |
| `ttc_s` | 正闭合速度下的预计碰撞时间，单位 s |
| `recommended_action` | 正常、提醒、减速或 `FULL_BRAKE` |
| `reason` | 动作原因，例如 `visual_hazard_without_range` |

融合只提供 C 组局部安全建议，最终车辆控制仍须经过 D 组安全仲裁。

## 5. 安装与运行

### 5.1 安装依赖

```powershell
python -m pip install -r requirements.txt
```

本次新增依赖：

- `onnxruntime>=1.20`
- `Pillow>=10`

### 5.2 生成离线验收证据

```powershell
python tools\validate_c_role.py
```

输出目录：`artifacts/C_role_validation/`

- `summary.json`：验收摘要和参数快照。
- `front_distance_ttc_samples.csv`：距离/TTC/动作切换样本。
- `stop_curve.csv`：停车全过程曲线。
- `fault_injection.json`：传感器失效和冲突注入结果。

### 5.3 运行真实传感器模式

先启动 CARLA 服务，再从仓库根目录执行：

```powershell
python -m integration.carla_runner `
  --host 127.0.0.1 --port 2000 `
  --scenario-file scenarios/safety_D/D03_front_vehicle_brake.json `
  --scenario-facts-mode perception `
  --perception-mode sensors `
  --rgb-detector-model artifacts/models/yolo11n.onnx `
  --rgb-detector-confidence 0.35 `
  --rgb-detector-iou 0.45 `
  --realtime
```

不传 `--rgb-detector-model` 时不会启动 ONNX 推理，现有默认运行路径保持不变。

## 6. 已完成验证

提交前在仓库自身测试目录执行：

```powershell
python -m pytest -q `
  car_control_A\tests `
  car_control_B\tests `
  car_control_C\tests `
  car_control_D\tests `
  integration\tests

python tools\validate_scenarios.py
python tools\validate_c_role.py
```

结果：

| 验证项 | 结果 |
|---|---|
| Python 测试 | `214 passed, 1 skipped` |
| 场景契约 | 34 项通过，0 失败 |
| C 角色确定性验收 | `PASS` |
| 停车时间 | `3.8 s` |
| 停车距离 | `15.647921 m` |
| 停车曲线帧数 | 95 |
| 样本最小 TTC | `0.5 s` |
| 静止保持 | 连续 20 帧通过 |
| 故障注入 | 全部通过 |

跳过项是需要真实 CARLA 服务的联机冒烟测试，不代表失败。不要直接在仓库根目录裸跑 `pytest`，因为本地 `CARLA_0.9.16/`、`artifacts/upstream_main/` 等未跟踪目录可能被误收集；应使用上面的明确测试目录。

## 7. 已知边界与风险

1. 尚未用真实 CARLA + 实际 ONNX 模型完成联机道路验收，因此不能把离线结果等同于实时性能结论。
2. 当前 RGB/LiDAR 关联使用中央图像走廊启发式，不是车道分割或多目标跟踪；复杂弯道、遮挡和密集交通需要专项测试。
3. ONNX 模型权重和许可不在仓库内，正式打包前需确认模型来源、比赛分发规则和推理输出格式。
4. 新日志包含 `c_safety_state`；外部若存在严格拒绝未知字段的解析器，需要同步更新。
5. 仓库外代码若手动用四个位置参数构造 `PerceptionSample`，需要补充 `safety_summary`；仓库内没有此类不兼容调用。
6. 外部代码若手动构造缺少 RGB 检测参数的 `argparse.Namespace` 并直接调用 `carla_runner.run()`，需补齐相关参数；正常 CLI 调用不受影响。
7. `FULL_BRAKE` 是 C 组局部安全输出，不能替代 D 组对碰撞、侧向风险、规则和最终控制的统一仲裁。

## 8. 下一步建议

按优先级执行：

1. 在不配置 ONNX 模型时跑一次真实 CARLA 基线冒烟，确认原传感器和控制路径无回归。
2. 使用确定版本的 ONNX 模型跑前车、行人、低 TTC、RGB 丢帧和 LiDAR 丢帧场景。
3. 记录每帧 ONNX 推理延迟、传感器总延迟、最小距离/TTC、制动触发帧和停车误差，确认满足比赛实时性要求。
4. 检查 `c_safety_state.source_by_field`，确保答辩材料不会把 CARLA 真值、场景注入或启发式结果误写为真实视觉检测。
5. 结合实际 CARLA 车型标定 throttle/brake 映射和紧急制动阈值；修改参数后重新生成 C 角色证据包。
6. 与 D 组联合验证 `FULL_BRAKE` 锁存、解除条件及最终控制只下发一次。

## 9. 交接检查清单

- [x] C 组纵向控制测试通过。
- [x] RGB + LiDAR 保守融合完成。
- [x] ONNX 检测器可选接入完成。
- [x] 感知有效性和字段来源进入日志。
- [x] 传感器/检测器故障采用 fail-closed 策略。
- [x] 确定性验收脚本和证据已提交。
- [x] 代码已推送至 `carla_driving_rstar`，远端提交为 `f5671b0`。
- [ ] 真实 CARLA 无模型基线冒烟。
- [ ] 真实 CARLA + 实际 ONNX 模型验收。
- [ ] 现场车型控制参数标定。
- [ ] 与 D 组完成最终安全仲裁联调。

如需更完整的模块级说明，请继续查看 `car_control_C/HANDOFF.md`、`integration/HANDOFF.md` 和 `integration/RGB_ONNX.md`。
