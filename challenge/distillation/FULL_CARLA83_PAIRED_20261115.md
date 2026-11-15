# 当前 Student：83 场完整 CARLA 仿真验收

本轮只测，不修改权重、仿真场景、车控、安全逻辑或原判分，亦不需要实板。当前受测 Student 为已实跑的 explicit-v2 FP32 ONNX `e8e4cb0f500a848b0462015d7f80f7716316aa5364cd3494526c72724d04a63c`；Teacher 为 Qwen3.5-2B revision `15852e8c16360a2fea060d615a32b45270f8a8fc`，Planner V2 adapter `95e97b00def8ec36f12937da34ce8bb9082c4a04`。两侧使用相同执行代码与测试配置，各跑相同原始 83 场一次；不混入前一轮专挑失分的结果，也不用旧量化产物冒充本候选。

服务器 `tiaozhansai`，Slurm job `36`，运行目录 `/home/tiaozhansai/carla-driving-challenge/artifacts/numeric_speed_conditioned_20261112/paired_full83.spL8EQ1E`。`frozen_inputs.sha256` 记录矩阵、83 个场景和运行/汇总脚本；`runtime.sha256` 记录执行快照。两个角色使用 CARLA 0.9.16、原场景 seed、真实 RGB/LiDAR、`perception=sensors` 与 `scenario_facts_mode=perception`。低分辨率 profile、感知超时 1.5 s、看门狗 4 s 为与前一轮相同的诊断配置，不作为正式时延验收。

`run.log` 逐场记录结果；每侧原始判定、退出码、逐帧与汇总证据位于 `<scenario>/<role>/`。`paired_report.json` 由作业末尾自动写入，缺失任何一侧判定则不计算衰减。使用矩阵基础/进阶/挑战完成率的原 30%/40%/30% 权重，计算 `(Teacher 加权完成率 − Student 加权完成率) / Teacher 加权完成率`，同时保留 6 场综合回归、5 场系统稳定性和安全计数。当前这份矩阵仍是项目自建仿真套件，不是官方独立基准；本轮也未测 ASR、实板或当前新 FP32 的量化版。

汇总预检已用完整 83 组模拟判定验证权重与相对衰减计算；制造一侧超时时，报告保留缺项并拒绝输出 3% 结论。

## 完整结果

166/166 次有唯一判定，无缺项。Teacher 76/83，Student 64/83；原权重计算的通过率分别为 92.17% 与 76.50%，相对衰减 **17.00%**，高于项目仿真使用的 3% 线约 14.00 个百分点。两侧的 83 份场景汇总都记录零碰撞、零红灯违规和零严重路线偏离。正式赛用独立数据与量化版另测，不能拿这组代替。

| 分组 | Teacher | Student |
| --- | ---: | ---: |
| 基础（30%） | 18/18 | 14/18 |
| 进阶（40%） | 26/30 | 23/30 |
| 挑战（30%） | 22/24 | 18/24 |
| 综合回归（不计加权） | 5/6 | 4/6 |
| 系统稳定性（不计加权） | 5/5 | 5/5 |

12 场只有 Student 失败，10 场都在成功部署 KEEP_LANE 后因计划无速度而部署 0.0 m/s。这些命令已有结构化速度（12–20 km/h），不需要模型猜交通规则或复制 Teacher。剩余两场 `SUP_A16_detour_right_static_vehicle`、`CX03_construction_bicycle_detour` 是绕障/返回/路线执行问题，不能归到同一缺省速度原因。此轮是 FP32，不能据此归因于 INT8；模型为何省略速度也没有在这轮证明是模型容量造成的。

后续仅在车道保持、未给计划速度且原请求已获准的情况下，按原指令速度或等待前已有的运行速度提供执行初值。显式零速、红黄灯、危险/过期感知、安全接管与确认约束不变。100 项相关单测通过。隔离复测 Slurm `37`：`artifacts/numeric_speed_conditioned_20261112/keep_lane_restore.MiDrUBfy`，包含 10 个同类失分及 2 个普通/紧急停车对照；不能用该子集替代完整复测。

隔离复测 12/12 通过，原失败 10/10 修回，两种停车对照均保持通过，场景汇总无碰撞、红灯违规或严重路线偏离。将这 10 条的判定代回基线只得到 **1.45% 的推算值**，不是最终测量。

修复版全量作业 `38` 运行目录为 `artifacts/numeric_speed_conditioned_20261112/paired_full83_fix.uTXN9EMh/`。逐字节复用基线的场景矩阵、83 个场景和评分脚本；两侧都在同一个修复后执行快照上各跑一次。与作业 `36` 的 Python 执行快照逐文件哈希对比，仅 `integration/second_group_runtime.py` 改变（SHA256 `011b2049b4e76d0d5097d43a6c0060fd367a148c24e9873c65e1ce85d21d5100`）。输出仍为 `paired_report.json`；未聚合全部 166 个判定前不宣称达标。
