# 服务器感知、车道关联与跟踪实验归档

这是 2026-11-16/17 的实验，不由 `main` 的 CARLA 入口导入。未替换正式检测阈值、模型、目标证据、Planner 或 A/B/C/D 控制。

## 源码层次

| 路径 | 原始分支与复现顺序 |
| --- | --- |
| [source_overlay](source_overlay/) | 相对服务器基线 `ca353478af8130bf5d2f9622cade4c25284776da` 的新增/改动文件，来源 `carla-driving-target-and-provement@69db71a83f8fcb906fdc2a15928d1b4956f4112b`。包括相机与 LiDAR 关联、实验辅助检测、时序点云、场景及相应测试。 |
| [projection_audit_overlay](projection_audit_overlay/) | `carla-driving-baseline-audit-20261116` 的同基线投影审计，单独覆盖，含 runner 调试变更。 |
| [association_overlay](association_overlay/) | `69db71a8` → `5775b6457daa1083fc4d2d727b88ef503f2dd98d` 的新增文件，车道关联、目标分组及点云定位。来自独立 `carla-lane-association-20261117`。 |
| [disambiguator_overlay](disambiguator_overlay/) | `carla-disambiguator-experiment-20261117` 未提交的新增实验文件；以 `5775b645` 为底，含目标消歧、连续跟踪与统一跟踪。 |
| [runs](runs/) 和 [late_runs](late_runs/) | 已保存报告、汇总数据和实跑辅助脚本；命令里的绝对路径、传感器帧、模型、服务及其他依赖资产须按各报告恢复。 |

复现时先在独立目录准备基线，按上表从所需 overlay 目录**内部**复制到该目录根部；不要覆盖正在使用的服务器 checkout。投影审计和关联实验是两个不同的路径，不要求同时叠加。转存源文件不等于重新验收。

## 结果与边界

- [分阶段点云报告](runs/pointcloud_adaptive_development_20261117/自适应聚类分阶段验证报告.md)：新增 48 个同步帧，RGB/LiDAR 时间差 ≤1 ms；剔除 3 个地理近重复项后，留出 21 帧、35 个目标机会。YOLO 0.35 匹配 10/35；基线定位 1/35，V1/V2/V3 各 4/35，均不是已验证定位；固定半径 1.20 m 的 7/35 是留出集诊断，不作部署选型。
- [双通道隔离复核](runs/yolo_dual_channel_isolation_20261117/final_offline_report.md)：低阈值辅助通道新增 9 个候选，人工确认 9/9 有车，2/9 有多车；没有可信三维或 FOLLOW 判定（0/9），正式输出在 21/21 固定帧保持不变。
- [单帧三维消歧](late_runs/target3d_disambiguator_20261117/report.md)：两例最终均为 UNKNOWN。一例单簇 11/11 点级 precision 不能外推；另一例没有选中有效簇，precision 未定义。两例都没有授权跟车。
- [统一跟踪诊断](late_runs/unified_tracking_c1_retry_20261117/summary.json)：单段 60 帧，前车跟踪命中 46/60 且有 3 次 ID 切换，旁车命中 60/60 但 0 帧被确认。命中、身份连续与控制可用是不同指标。
- [三车固定帧车道关联](association_overlay/tools/lane_assoc/README.md)和 [Student / Teacher 诊断汇总](runs/student_teacher_20261116/comparison_summary.json)保留模型前后的边界证据，不是完整安全链验证。
