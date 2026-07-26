# CARLA `7.25` 分支 Town03_Opt 重测最终报告

测试日期：2026-07-26（Asia/Shanghai）

## 1. 结论

本次使用指定的新克隆、指定分支和 `carla312` 环境重新执行。两个阻断性问题已定位并作最小修复；修复后：

- Low/Default 两种传感器配置下，RGB、LiDAR、RGB+LiDAR 共 6 项稳定性门禁全部通过，每项正式窗口均为 `100/100` 连续同帧样本。
- S01、D03、D08 各执行 3 轮，共 9 轮正式运行，全部 `SUCCEEDED`，每轮验收项全部通过且均为 `25/25`。
- 9 轮共 5,400 个正式控制帧；完整性审计全部通过：帧号连续、仿真时间严格递增、vehicle/scene/C-safety 跨层帧号一致、每轮恰好一个 `run_complete`，且无碰撞、无红灯违规。
- ONNX 检测器在 5,400/5,400 个正式帧均真实执行；D03 的融合前车距离来源在每轮 683/700 帧为 `RGB_ONNX_LIDAR_FRONT_CORRIDOR`；D08 的真实 CARLA 交通灯/停车线来源每轮为 500/500 帧。
- 全仓隔离测试 `346 passed, 1 skipped`；唯一 skip 是需要实时 CARLA 的 smoke，随后单独开启并验证为 `1 passed`。
- 退出后 CARLA 已恢复异步，车辆和传感器 Actor 均清零，交通灯无冻结残留。

因此，在当前机器、当前 CARLA 进程和 `Town03_Opt` 条件下，图片对应的三项场景已经得到完整、可重复且有原始证据支撑的成功结果。

## 2. 代码与环境指纹

| 项目 | 实际值 |
|---|---|
| 新工作目录 | `/home/abc/projects/carla_driving_7_25_retest_20260726` |
| Git 远端 | `https://github.com/oOxixi/carla_driving.git` |
| 分支 | `7.25`（`HEAD -> 7.25, origin/7.25`） |
| 原始提交 | `bbfbeddffda65ec9270baed6154dc50207d7a155` |
| 提交说明 | `Add strict Qwen and dataset workflows` |
| Conda 环境 | `carla312` |
| Python | `3.12.13` |
| CARLA | 0.9.16 |
| 地图 | `Carla/Maps/Town03_Opt` |
| CARLA 启动方式 | `-quality-level=Low -RenderOffScreen -nosound -carla-rpc-port=2000` |
| GPU | NVIDIA GeForce RTX 4060 Laptop GPU，8188 MiB |
| 驱动 | 580.173.02 |

正式场景统一使用：

- `perception-mode=sensors`
- `scenario-facts-mode=perception`
- `sensor-profile=default`
- `sensor-timeout-s=2.0`
- `sensor-warmup-frames=60`
- YOLO11 ONNX，confidence `0.25`
- `--realtime`

YOLO 文件不属于这次新 clone，自兄弟 checkout 只读引用：

```text
/home/abc/projects/carla_driving/artifacts/models/yolo11n.onnx
SHA-256 634279b40c07c6391472c51ad45b81ebc48706a9a1fe72dd3396322acd0c053b
```

这一区分很重要：代码结果来自新目录的 `7.25` 分支；模型权重来自本机已有兄弟目录，并未伪装为新分支自带文件。

## 3. 失败根因与修复

### 3.1 传感器门禁首帧后超时

原始现象：RGB/LiDAR 在 Actor 附着后先返回一个回调，随后固定出现一个无回调的 pipeline bubble；旧逻辑把第一个回调立即视为“稳定流已启动”，因此第二个 tick 直接判失败。

修复：`integration/sensor_stability.py` 与 `integration/carla_runner.py` 仅在观察到两个连续、精确同帧的有效样本后结束预热。正式计量窗口开始后，任何掉帧仍会立即失败，因此该修改只隔离真实的 GPU/raycast 启动瞬态，没有放宽正式稳定性标准。

诊断和修复前失败日志均保留：

- `probe/rgb_low.log`
- `probe/lidar_low.log`
- `probe/both_low.log`
- `probe/cadence_diagnostic.log`

### 3.2 D03 前车反向撞向 Ego

修复前基线可稳定复现 1 次碰撞。根因是 CARLA 新生成 Actor 在首个 world tick 前可能返回尚未更新的默认 transform；代码据此设置初速度，使前车速度方向与场景 spawn 朝向相反，前车主动撞向 Ego。这不是控制器制动能力不足。

修复：

- 初始目标速度使用已知且权威的 spawn transform 的 forward vector。
- 后续前车速度反馈改为速度向量在车辆 forward vector 上的有符号投影，反向运动不会再被当作正向车速。
- 增加针对有符号速度和传感器 pipeline bubble 的回归测试。

修改文件：

- `integration/carla_runner.py`
- `integration/sensor_stability.py`
- `integration/tests/test_carla_runner_helpers.py`

本次测试以原始提交 `bbfbeddffda65ec9270baed6154dc50207d7a155` 为起点；修复后相对该提交为 104 行新增、20 行删除，`git diff --check` 通过。上述代码修复、回归测试及实跑证据现已提交并推送至 `7.25` 分支；“原始提交”仅表示测试起点，不代表当前分支 HEAD。

## 4. 六项传感器门禁

| Profile | 传感器 | 正式同帧结果 | 有效回调 | 无效回调 | 用时 | 结果 |
|---|---:|---:|---:|---:|---:|---:|
| Low | RGB | 100/100 | 103 | 0 | 12.747 s | PASS |
| Low | LiDAR | 100/100 | 103 | 0 | 8.481 s | PASS |
| Low | RGB+LiDAR | 100/100 | 两路各 103 | 两路各 0 | 12.785 s | PASS |
| Default | RGB | 100/100 | 103 | 0 | 13.311 s | PASS |
| Default | LiDAR | 100/100 | 103 | 0 | 8.483 s | PASS |
| Default | RGB+LiDAR | 100/100 | 两路各 103 | 两路各 0 | 13.351 s | PASS |

所有探针均运行在 `Carla/Maps/Town03_Opt`。每次启动序列均清晰记录为：首次有效、一个 pipeline bubble、随后连续两帧有效，再进入 100 帧正式窗口。

证据目录：`probe/`

## 5. 正式场景结果

### 5.1 汇总

| 场景 | 重复 | 每轮帧数 | 验收 | 关键结果 | 安全事件 | 得分 |
|---|---:|---:|---:|---|---|---:|
| S01 `set_speed_20` | 3/3 成功 | 600 | 6/6 PASS | 终速 17.7935 km/h；目标 20±5；最大横向误差 0.002319 m | 0 碰撞、0 接管、0 路线偏离 | 每轮 25/25 |
| D03 `front_vehicle_brake` | 3/3 成功 | 700 | 4/4 PASS | 最小间距 4.883453 m；最小 TTC 2.790404 s | 每轮 86 帧、26 段安全接管；0 碰撞 | 每轮 25/25 |
| D08 `command_conflict_red_light_continue` | 3/3 成功 | 500 | 4/4 PASS | 最终速度 0；停车线余量 0.935389 m；全程绑定真实 RED 灯 | 每轮 410 帧、1 段红灯停车接管；0 越线 | 每轮 25/25 |

三个场景的三轮数值完全一致，显示在相同仿真配置下具备良好确定性。

### 5.2 D03 感知与安全细节

- ONNX 对象检测：每轮 700/700 帧。
- 前车融合距离来源：每轮 683/700 帧为 `RGB_ONNX_LIDAR_FRONT_CORRIDOR`。
- 最小安全距离 4.883453 m，显著高于要求的 2.5 m。
- 最小 TTC 2.790404 s。
- 安全理由包含 `EMERGENCY_FRONT_OBSTACLE_TOO_CLOSE`，说明接管路径确实被触发，而不是静态事实直接判成功。
- 0 碰撞、0 红灯违规、0 路线偏离。

修复前基线被原样保留在 `D03/baseline_run_1_before_lead_fix/`：

- 状态 `FAILED`，得分 0。
- 700 帧，1 次碰撞。
- 最小间距 2.503344 m。
- 122 帧安全接管，验收失败项为 `must_no_collision`。

### 5.3 D08 真实交通灯证据

- 每轮 500/500 帧中，`traffic_light` 与 `distance_to_stop_line_m` 均来自 `CARLA_SCENARIO_TRAFFIC_LIGHT_ACTOR_STOP_WAYPOINT`。
- 场景绑定真实 CARLA traffic-light Actor（运行日志中的 Actor id 为 66），不是虚拟验收真值。
- 每轮 410 帧触发 `RED_LIGHT_STOP_LINE_GUARD`，安全层覆盖“继续前进”的冲突命令。
- 最终速度为 0，停车线余量 0.935389 m。
- 0 碰撞、0 红灯越线、0 路线偏离。

## 6. JSONL 证据完整性

独立审计脚本 `audit_jsonl.py` 对 9 个正式 JSONL 执行以下硬断言：

- 每轮记录组成恰好为 1 `run_start`、1 `command`、N `frame`、1 `feedback`、1 `run_complete`。
- 正式 frame 编号逐一连续，无空洞。
- `sim_time_s` 严格递增。
- 每条记录的顶层、vehicle、scene、C-safety frame 完全一致。
- `scene.collision` 与 `scene.red_light_violation` 全程为 false。
- 终态为 `SUCCEEDED` 且 acceptance 为 true。
- 安全接管帧数与 summary 完全一致。
- 所有 5,400 帧的检测来源均为 `RGB_ONNX_OBJECT_DETECTOR`。
- D03 和 D08 的关键感知 provenance 数量符合上述结果。

审计终态：

```json
{"audit":"PASS","formal_runs":9,"total_frames":5400}
```

脚本与输出：

- `audit_jsonl.py`
- `jsonl_integrity_audit.log`

## 7. 自动测试

与本次两处修复直接相关的回归集再次执行，结果为 `43 passed in 0.14s`，日志为 `pytest_targeted.log`。

### 7.1 默认 pytest 的收集冲突

直接运行默认 `pytest -q` 在收集阶段失败。原因是：

- ROS Humble 的外部 `launch_testing` pytest 插件自动加载；
- `car_control_B/tests/test_path_utils.py` 与 `car_control_B2/tests/test_path_utils.py` 同名；
- 插件使用普通 import 路径后触发 `_pytest.pathlib.ImportPathMismatchError`。

这是测试收集/环境插件冲突，不是本次代码逻辑失败。原始失败输出完整保留为 `pytest_default_collection_failure.log`。

使用项目隔离方式：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
conda run -n carla312 python -m pytest -q --import-mode=importlib
```

结果：`346 passed, 1 skipped in 0.41s`。唯一 skip 是 CARLA live smoke。

随后显式运行在线 smoke：

```bash
CARLA_SMOKE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
conda run -n carla312 python -m pytest -q --import-mode=importlib \
car_control_A/tests/test_simulator_smoke.py
```

结果：`1 passed in 4.49s`。

对应日志：

- `pytest_full.log`
- `pytest_carla_smoke.log`
- `pytest_targeted.log`

## 8. CARLA 最终清理状态

最终只读核验：

```json
{
  "map": "Carla/Maps/Town03_Opt",
  "synchronous_mode": false,
  "fixed_delta_seconds": null,
  "vehicles": 0,
  "sensors": 0,
  "traffic_lights": 38,
  "traffic_lights_frozen": 0
}
```

CARLA 服务仍在运行；本次测试未关闭用户启动的服务。完整输出保存在 `final_carla_state.log`。

## 9. 证据索引与注意事项

- `S01/`：3 轮 console、JSONL、summary。
- `D03/`：修复前失败基线 + 修复后 3 轮完整证据。
- `D08/`：修复后 3 轮完整证据。
- `probe/`：六项稳定性通过日志、修复前失败日志及 cadence 诊断。
- `pytest_*.log`：默认收集失败、隔离全仓测试、CARLA live smoke。
- `jsonl_integrity_audit.log`：9 轮 5,400 帧独立审计结果。
- `final_carla_state.log`：退出清理状态。

代码修复、测试与 `artifacts/ubuntu_0726_retest/` 证据目录均已纳入 `7.25` 分支提交，不再是未提交补丁；测试起点仍按本报告记录为 `bbfbeddffda65ec9270baed6154dc50207d7a155`。
