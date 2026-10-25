# 2026-10-25 泛化矩阵与证据统计交付

## 本轮改动

基于 `cc806956517347b63a969cf245dddba772aa99be` 实施。新增 Town03_Opt 专用矩阵、真实闭环任务入口、已有日志旁路审计工具，以及版本/配置/模型来源记录。运行器现在将场景内 RGB 分辨率和 LiDAR 通道配置传入实际蓝图；官方 S2 JSON 和比赛评分阈值保持原样。

业务指令、内部执行步骤、内部等待停车的终态分别显示。原始终态不删除，失败阶段不会再被计为“已完成”。安全接管按原因拆分，红灯停车单独统计。

## 实际验证

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
