# `new` 与 `team2A` 融合验证记录（2026-08-02）

## 范围与来源

- 远端仓库：`https://github.com/oOxixi/carla_driving.git`
- `new` 融合前提交：`542cf8a8b3d8e445ed95fc9e3baae85bb0344ca2`
- `team2A` 提交：`f527913eb356e014f0f50c234732531fd6284c57`
- 共同基线：`b9150fcbda6959fcd6c50269b09b431b750632ba`
- 工作目录：`/home/abc/projects/carla_driving_new_20260802`

融合在新克隆的专用分支 `integration/new-team2a-20260802` 中完成，未修改原
`/home/abc/projects/carla_driving_main_20260730` 工作目录，也未使用强制推送。

## 融合处理

双方共有 9 个重叠文件，Git 自动合并其中 5 个，人工审查并解决 4 个文本冲突：

1. `car_control_D/tests/test_safety_supervisor.py`
   - 保留 `new` 的红灯保持、配置校验和异常输入失效闭锁测试。
   - 保留 `team2A` 的严重路径偏差禁止恢复油门语义。
2. `integration/carla_runner.py`
   - 同时保留 `new` 的远程 Qwen-VL 异步路径。
   - 同时保留 `team2A` 的实时麦克风、统一编排、图像暂存和感知计时路径。
   - 路径刷新失败告警继续进入看门狗安全链路。
3. `integration/scenario_evidence.py`
   - 使用线性插值分位数，与 `team2A` 的证据生成口径一致。
4. `integration/tests/test_runtime_loop.py`
   - 同时保留外部危险终态反馈、路径偏差停驶和无效横向参考闭锁测试。

另外为 `car_control_B/tests` 增加独立测试包标识，修复
系统 ROS `launch_testing` 插件自动加载时，同名 `test_path_utils.py` 导致的 pytest
收集冲突。该修复不改变车辆控制业务逻辑。

## 验证结果

### 队友 `new` 融合前基线

- 禁用外部 pytest 插件后：`427 passed, 1 skipped`。
- 默认 pytest 命令在收集阶段失败，原因为 B/B2 两个同名测试模块冲突。
- `new` 变更范围中有两份任务 6 Markdown 存在末尾多余空行；这是融合前已有的
  低风险格式问题，未改写其验收内容。

### 融合后

- 冲突相关定向测试：`320 passed`。
- 默认完整测试（不需要额外环境变量）：`497 passed, 1 skipped`。
- Python 编译检查：通过。
- Git 新增/修改内容空白检查：通过。
- 场景契约验证：
  - `S01_set_speed_20`：PASS
  - `D03_front_vehicle_brake`：PASS
  - `D08_command_conflict_red_light_continue`：PASS

### CARLA 0.9.16 实车闭环冒烟

- 地图：`Town10HD_Opt`
- 感知：真实 CARLA RGB/LiDAR/Radar，`low` 传感器配置
- 指令：20 km/h
- 帧数：120
- 结果：进程退出码 0；传感器启动和对齐成功；车辆从静止加速至约
  `5.20 m/s`（约 18.7 km/h）；末帧目标为 `5.56 m/s`；采样输出中的安全状态
  均为 `NONE`，没有运行异常或安全闭锁。
- 测试使用 `--no-log`，未把临时运行产物写入仓库；CARLA 临时实例已关闭并确认
  无残留进程。

## 证据边界

`submission/second_group_20260731/evidence_index.json` 是 `team2A` 在 2026-07-31
生成的不可变验收快照。融合后 45 个登记对象中 42 个仍逐字一致；
`integration/carla_runner.py`、`integration/runtime_loop.py` 和
`integration/scenario_evidence.py` 因冲突融合发生变化。旧哈希未被篡改，完整原始
快照仍可在父提交 `f527913` 验证。

本轮未连接真实 Qwen 服务、未加载生产 Qwen 权重，也未进行新的麦克风人工录音；
相关路径由自动化测试覆盖，不将其表述为本轮真实模型或人工语音验收。
