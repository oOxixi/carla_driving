# D 真实传感器矩阵证据

- CARLA 0.9.16，Town03_Opt，GPU 0。
- `sensors/perception` 模式，不使用 scenario truth 替代实测感知。
- S01、D03、D08 各 5 个 seed，每 seed 20 次，共 300 次。
- 300/300 场景验收通过，碰撞、闯红灯、严重路线偏离和未终态指令均为 0。
- 三场景最差单次运行 P95 分别为 3.647185、2.140257、1.318166 ms，均满足 5 ms 门槛。

文件说明：

- `evidence_index.json`：正式机器可读证据索引。
- `scenario_matrix_report.json`：300 次运行的完整汇总记录。
- `scenario_matrix_full.log`：批量执行控制台记录。
- `scenario_matrix_seed_calibration.log`：首轮 5-seed 校准记录。
- `control_benchmark_ubuntu_0730.json`：Ubuntu 控制热路径基准。
- `sensor_soak_60min.log`：60 分钟 RGB+LiDAR 连续稳定性原始日志。

60 分钟 RGB+LiDAR 连续稳定性测试已通过：

- 实际持续时间：`3607.802 s`
- 对齐帧：`100210`
- RGB/LiDAR 回调：各 `100213`
- 无效回调：两路均为 `0`
- CARLA 地图：`Town03_Opt`
