# 控制与安全策略泛化报告

## 1. 基线与范围

| 项目 | 内容 |
|---|---|
| Git 分支 | `scene` |
| 基线提交 | `f0fd3c2394381b93788c82c1dd22e4d2d07aef8c` |
| Python | 3.12 |
| CARLA | 0.9.16 |
| ScenarioRunner | v0.9.16 |
| 本轮范围 | CARLA 无关的策略重构、接口接入、离线数值与回归测试 |
| 未执行 | CARLA 实车闭环与真实场景测试（本机未安装 CARLA） |

## 2. 已完成内容

### 2.1 单一策略配置

新增根目录 `strategy_config.yaml`，集中管理：

- command / visual confidence；
- TTC、制动能力、驻车制动；
- 动态安全距离模型；
- PID 与纵向速度规划；
- Pure Pursuit / Stanley 横向增益调度；
- 路线偏差与安全接管；
- 单 Sensor 失效降级速度。

配置使用 JSON 语法的 YAML 1.2 文档，由标准库严格解析，不引入 PyYAML 运行依赖。加载时检查字段缺失、未知字段、非有限值、范围和字段间约束。

### 2.2 动态安全距离

安全距离不再使用固定的 10 m / 5 m 判断。每帧根据以下输入生成 caution / emergency 两层包络：

```text
基础间距
+ 速度 × 反应时间
+ 相对闭合速度² / (2 × 制动减速度)
+ Sensor 基础误差与速度相关误差
```

随后根据道路曲率和 Actor 类型调整。行人、骑行者等 VRU 使用更大的 caution 包络，但 emergency 包络单独限制，避免远距离检测直接触发不必要的紧急制动。

动态包络及各组成项写入 `SafetyStateSummary.safety_distance_components` 和 D 层 `risk_metrics.dynamic_safety_distance`，便于复盘。

### 2.3 横向控制自适应

Pure Pursuit 与 Stanley 已按以下变量调度：

- 速度；
- 道路曲率；
- 横向误差；
- 航向误差。

动态调整前视距离、转向上限、单帧转向变化率和 Stanley 增益。低速允许更快建立转角；高速降低转向幅值和变化速度；弯道或误差较大时缩短前视距离并提高必要的转向响应。

### 2.4 统一安全目标速度

`SpeedPlanner` 保持原 `plan() -> float` 接口兼容，同时增加 `last_plan` 诊断结果：

```text
safe_target_speed_mps
limiting_constraint
constraint_caps_mps
```

当前限制来源包括：

- 语音或默认目标速度；
- 道路限速；
- 道路曲率；
- 前车间距；
- 红灯 / 停止点；
- 感知或单 Sensor 降级速度上限。

### 2.5 安全原因分层

D 层新增 `reason_category`，并进入 `FrameResult`、runner 帧日志和场景证据日志：

| 分类 | 含义 |
|---|---|
| `QWEN_OR_COMMAND` | 指令未知、低置信度或需确认 |
| `PERCEPTION` | 感知状态无效、Sensor/感知 watchdog |
| `WATCHDOG` | 非感知模块心跳或运行时故障 |
| `ROUTE_OR_LATERAL_CONTROL` | 路线偏差、车道偏差、横向控制问题 |
| `CONTROL` | 控制输出非法或集成控制异常 |
| `SAFETY_POLICY` | TTC、前方障碍、红灯等安全层接管 |
| `NONE` | 未接管 |

原始 `reason` 仍然保留，用于具体根因定位。

## 3. 离线验证结果

| 测试 | 结果 | 说明 |
|---|---:|---|
| 新增 unittest | 4 / 4 通过 | 动态距离、横向调度、safe target speed、原因分类 |
| 原 B / runtime 直接回归 | 31 / 31 通过 | 不依赖 pytest 的原测试函数 |
| 原 C / D 选定回归 | 37 / 37 通过 | 使用等价断言执行；完整 pytest 环境当前缺失 |
| SafetyConfig 非法参数 | 4 / 4 通过 | NaN、TTC 倒置、制动越界、路线阈值倒置 |
| 泛化数值矩阵 | 36 / 36 通过 | 4 速度 × 3 道路 × 3 Actor |
| Python AST 编译 | 218 / 218 通过 | 不写 `__pycache__` 的语法编译检查 |

速度覆盖：10 / 20 / 30 / 40 km/h。

道路覆盖：直道 / 缓弯 / 急弯。

Actor 覆盖：车辆 / 行人 / 未分类障碍物。

离线验证命令：

```powershell
python -B -m unittest discover -s car_control_C/tests -p test_strategy_generalization.py -v
python -B tools/validate_control_generalization.py
```

## 4. 当前边界与后续依赖

### 成员1接口

当前已兼容现有 `RouteReference.curvature_per_m`、`route_deviation_m` 和 `lane_offset_m`。成员1完成统一 Route 坐标体系后，需要确认：

- `road_curvature` 的计算窗口、符号和单位；
- `route_progress` 与路线结束状态；
- 路线偏差在路口和相邻车道切换时的定义；
- 路线重规划期间是否提供有效性标志。

### 成员2接口

动态安全距离已支持 `front_actor_type`。成员2完成 Actor 泛化后，需要确认：

- Actor 类型的标准枚举；
- 前车 / 切入车相对速度来源；
- 行人横穿方向和是否进入 ego corridor；
- Sensor 误差或降级状态如何映射为 `sensor_margin_scale`。

### CARLA 实测

安装 CARLA 后需补跑：

- 4 档速度；
- 直道、缓弯、急弯、路口；
- 前车、行人、静态障碍、车辆切入；
- 正常、低置信度、单 Sensor 短暂失效、RGB/LiDAR 不一致。

届时补充成功率、碰撞、路线偏差、安全接管次数和失败样本。本报告目前不宣称 CARLA 场景通过。
