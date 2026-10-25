# 2026-10-25 泛化矩阵与证据统计交付

> 本文为历史检查版本的结果记录。后续发现指令里程和指定慢车实际通过证据缺口，已增强检查并修改事件启动条件；历史 PASS 不代表新版合同通过。最新进展见 `main_optimization_event_integrity_20261025.md`。

## 本轮改动

基于 `cc806956517347b63a969cf245dddba772aa99be` 实施。新增 Town03_Opt 专用矩阵、真实闭环任务入口、已有日志旁路审计工具，以及版本/配置/模型来源记录。运行器现在将场景内 RGB 分辨率和 LiDAR 通道配置传入实际蓝图；官方 S2 JSON 和比赛评分阈值保持原样。

业务指令、内部执行步骤、内部等待停车的终态分别显示。原始终态不删除，失败阶段不会再被计为“已完成”。安全接管按原因拆分，红灯停车单独统计。

## 第一批实际验证（历史证据）

12 个变体、5 个事件窗口，共 60 个任务完成生成与静态校验。本轮实际执行 `case_index=5 / late_pedestrian` 一个目标段；其余 59 个未执行，完整矩阵尚未通过。

| 项目 | 真实结果 |
|---|---|
| 地图、天气 | Town03_Opt、ClearSunset |
| 模型 | Qwen/Qwen3.5-2B，生产 planner_v2 |
| exact revision | 15852e8c16360a2fea060d615a32b45270f8a8fc |
| artifact fingerprint | 4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa |
| 扰动 | Actor 纵向 +3 m、速度 1.2 倍、行人启动偏移 +0.5 s、16 通道 LiDAR、0.10 s 控制周期 |
| 行驶区间 | 从 6880 m 恢复，实际至 7502.55 m |
| 真实行人事件 | late_crossing_pedestrian 激活且触发横穿 |
| Qwen | QWEN_PLAN，外部命令唯一 SUCCEEDED / PLAN_COMPLETE |
| 最小行人净距 | 3.05493 m |
| 最大路线偏差 | 0.77710 m |
| 事件后最高恢复速度 | 38.80827 km/h |
| 碰撞、压线违规、闯红灯、路线偏离事件 | 均为 0 |
| 目标段功能检查 | 全部通过 |
| 延迟 | sensor-to-trajectory 最大 325.976 ms，仅记录，未作为当前目标段功能门禁 |

原始 summary 的整场景结果为 FAILED，因为本次仅跑目标段，完整路线与整场景时长合同未完成。重新检查报告明确为 `event_segment`、`full_8km=NOT_EVALUATED`，没有覆盖原始结果。

本次驾驶开始时记录的 HEAD 为 cc8069565，dirty=true，并保留修改差异哈希与配置哈希；新功能测试以未提交工作树执行，不能把后续提交 SHA 反向写入该驾驶日志。

## 历史完整 8 km 旁路审计

2026-10-24 正式完整运行的外部指令为 6 SUCCEEDED；内部执行步骤为 6 SUCCEEDED；内部等待停车为 6 FAILED。三类记录同时保留。

原 17,216 个安全接管帧中：红灯停止线保护 16,503、CAUTION_TTC 272、C_HAZARD_SPEED_CAP_BRAKE 437、EMERGENCY_FRONT_OBSTACLE_TOO_CLOSE 4。没有独立真值验证的前障碍接管不标成“误刹车”。历史日志未记录 dirty 状态，不补签当前 SHA。

原完整运行仍为功能通过、场景评分 25/25；正式 member3 checker 仍因最大轨迹延迟 236.479 ms 超过 150 ms 而整体未通过。阈值和报告未修改。

## 证据位置

代码验证：本机全量 pytest 为 1219 passed、4 skipped；服务器相关回归为 275 passed，最终新增证据测试 8 passed；155 个场景静态校验全部通过，官方 S1/S2/S3 合同校验全部通过。

服务器根目录：`/home/tiaozhansai/carla-driving-main-optimization`。

- 本轮真实驾驶：`artifacts/validation/s2_matrix_20261025_sparse_run/`。
- 使用最终检查项的只读复核：`artifacts/validation/s2_matrix_20261025_sparse_recheck/reevaluation.json`，已执行 1、未执行 59。
- 旧 8 km 审计：`artifacts/validation/s2_full_20261024_scoped_audit.json`。
- 原完整运行：`artifacts/logs/s2_full_regression_radar_corroborated_20261024/`。

本机已复制三个轻量证据文件到 artifacts/validation。原始日志和生成场景均为运行产物，不进入 Git。

## 后续顺序

先补公交站、行人超车返回、自行车、交叉口切入四类定点任务，优先选 RGB 降采样和实际 16 通道输入；再扩展 seed 和天气。跨地图 Unseen 需在地图约束允许时另行定义。全部事件稳定后选择代表组合跑长程，正式延迟门禁单独优化。

入口与判定说明见 `main_optimization_regression_workflow.md`。

## 追加事件验证与横向问题定位

新增 `s2_matrix_20261025_rgb_events` 实验，使用 case 1：WetSunset、0.10 s、四路 RGB 600×338、Actor 横向 +0.2 m。下表属于修复前代码的历史结果，不冒充新控制器的回归证明。

| 事件 | 目标段结论 | 最终里程 / m | 最大路线偏差 / m | 恢复速度 / km/h |
|---|---|---:|---:|---:|
| 公交站 | PASS | 1497.67 | 0.784 | 38.79 |
| 行人让行、超车返回 | FAIL：事件前下坡转弯摆动 | 2399.75 | 1.855 | 未恢复 |
| 自行车跟随 | PASS，最小净距 5.106 m | 4943.88 | 0.777 | 38.79 |
| 路口切入 | PASS | 5630.28 | 0.801 | 37.50 |

三项 PASS 的碰撞、违规压线、闯红灯和路线偏离事件均为 0。与第一批末段行人合计，历史矩阵覆盖 5/60 个唯一任务，其中 4 PASS、1 FAIL，55 个未执行；这是混合版本覆盖记录，不是冻结基线 Gate。

行人组合追加尝试均单独保留：

- `s2_matrix_20261025_chord_ped`：只修正曲率分母后，成功驶过下坡并触发行人/Qwen，但回程转向摆动后停车，任务失败；最小行人净距 3.153 m，最大路线偏差 4.144 m。
- `s2_matrix_20261025_forward_ped`：再修正局部前向选点后，业务计划到达 SUCCEEDED，仍在任务路线恢复后失稳，出现 1 次碰撞、1 次违规压线，最大路线偏差 4.571 m；不能因 Qwen 终态成功判为整段通过。
- `s2_matrix_20261025_physics_ped`：按真实车辆前轮最大转角校准后，目标段功能检查 PASS；实际至 2975.425 m，真实行人触发、QWEN_PLAN、唯一 SUCCEEDED、任务路线恢复 1 次，最小行人净距 3.153 m、慢车净距 6.182 m、最大路线偏差 0.687 m、恢复 38.756 km/h；碰撞、违规压线、闯红灯和路线偏离事件均为 0。最大轨迹延迟 207.453 ms，未达到正式 150 ms 门禁。

定位到三处通用问题：前视目标点实际距离与设定半径混用；横向误差较大时最近点落在车后；配置的最大转角为 0.60 rad，而实际 Model 3 前轮返回 1.22173034 rad（约 70°），归一化转向换算不匹配。修改不依赖场景 ID、固定坐标或 seed，不放宽安全和评分阈值。车型校准仅读取物理参数，不改物理世界。

新增 `tools/summarize_s2_optimization_matrix.py` 可合并独立证据，保存所有失败尝试、按任务去重，并拒绝将混合工作树版本签为冻结基线通过。其输出仍明确 `full_8km=NOT_EVALUATED`。

追加后的覆盖报告位于 `artifacts/validation/s2_matrix_20261025_coverage_after_physics.json`：最新尝试为 5 PASS、0 FAIL、55 未执行，`frozen_baseline_gate_passed=false`。其中只有行人组合是在本次车型标定修复上完成驾驶，其余四类是历史版本，仍需回归验证；不能称为同一版本 5/5。

车型标定驾驶记录仍为 HEAD `24d73ca01926b5c3b60ea403b1d8ad3feb451c3a`、dirty=true、差异哈希 `3b75c42b10b4fa5e8e13f279f41f883f33bd966c589333b7aafbe07cf1b10a65`，没有用后续提交补签。原始整场 summary 仍为 FAILED，除未跑完整路线/时长/后续命令外，仍有 `max_lane_center_offset_m` 失败，且行人指令实际发出里程为 2568.920 m，超出原合同 [2500, 2560] m。目标段工具没有将这些完整场景指标纳入其功能 PASS，因此不能据此宣称正式场景合规或评分 Gate 通过；后续需单独定位，不扩大门槛放行。

本机最终全量回归为 1237 passed、4 skipped，155 场景静态校验和官方 S1/S2/S3 合同校验均 PASS。新增运动学单测不是实车动力学证明。
