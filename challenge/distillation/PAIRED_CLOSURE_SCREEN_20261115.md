# Student 仿真闭环：七个历史失分场景同条件复跑

目标是定位会影响场景通过率或安全验收的差异，不要求 Student 的动作细节、目标速度或其他字段和 Teacher 一样。最终目标仍是按比赛口径测得核心性能相对衰减不超过 3%，这个只选历史失分场景的小批次不用于计算正式衰减。

## 复跑口径

- 从旧 V3.1 的 `05_teacher_student_decay_v31.json` 预先固定的 `teacher_passed_student_failed` 选全部七个场景，无结果后筛选。同场景原始 JSON、同配置、场景自带 seed、同 `planner_v2` / 同车控和安全链；每场换规划服务重跑。继续引用原 `scenario_acceptance` 和 `scenario_extension_acceptance`，不放宽评分。
- tiaozhansai 的隔离 CARLA 0.9.16，RGB/LiDAR 真传感器，`scenario_facts_mode=perception`。使用低分辨率传感器、1.5 s 感知超时、4 s 看门狗的成对诊断配置；这是文本指令场景，不测 ASR 或正式时延。
- Teacher：Qwen3.5-2B revision `15852e8c16360a2fea060d615a32b45270f8a8fc`，adapter Git `95e97b00def8ec36f12937da34ce8bb9082c4a04`；Student：已跑通转后设速的 explicit-v2 FP32 ONNX `e8e4cb0f500a848b0462015d7f80f7716316aa5364cd3494526c72724d04a63c`。两组使用相同修复后执行快照；新版同源量化不在本轮范围。
- 第一轮隔离启动因显存预算不足，在进入 CARLA 前终止（作业 34）；第二轮只将隔离 Teacher 的 vLLM 显存预算调为 0.45（作业 35）。不停止原有服务，没有改权重、生产链路或验收代码。服务器证据路径 `artifacts/numeric_speed_conditioned_20261112/paired_closure.CfICanDf/` 含 `inputs.sha256`、`runtime.sha256`、各角色逐帧日志和原验收 JSON。

## 结果与取舍

| 场景 | Teacher | Student | 判定依据 |
| --- | --- | --- | --- |
| `ACC_A04` 静态障碍停车 | 失败 | 失败 | 两边均输出 KEEP_LANE，扩展验收的障碍目标绑定和要求动作未通过；不是 Student 独有掉分 |
| `ACC_B02` 设速 20 km/h | 通过 | 通过 | Student 计划速度约 18.46 km/h，仍符合原场景验收 |
| `ACC_B06` 偏移纠正 | 通过 | 失败 | 路线未完成，横向误差未降低至合同要求 |
| `SUP_A06` 黄转红 | 通过 | 失败 | 红灯前未达到要求的最低行驶速度 |
| `SUP_A10` 占道静态车 | 通过 | 通过 | Student 与 Teacher 的减速目标约为 9.51 和 10.8 km/h，差异不丢分 |
| `SUP_B06` 右偏纠正 | 通过 | 失败 | 路线未完成，横向误差未降低至合同要求 |
| `VAR_B06` 弯道保持 | 通过 | 失败 | 路线未完成 |

Teacher 通过 6/7，Student 通过 2/7。14 次运行均生成验收结果，每场每角色均有 1 次规划请求记录，均未记录到碰撞。4 个 Student 独有失败里，两边均成功部署 KEEP_LANE；Teacher 部署 4.167 m/s，Student 未显式指定目标速度，部署值为 0.0 m/s。与已定位的转弯等待 STOP 速度继承问题相符：上一轮只为无显式速度的转弯保存和恢复原请求速度，保持车道目前不走该保护。下一轮若修，只对在同一等待中、计划已通过校验、确实应继续行驶且没有安全禁止的 KEEP_LANE 恢复等待前速度；不动有显式速度、停车、制动或红黄灯行为。须对照安全反例及上述四例，不能靠放宽原判分通过。

本地运行摘要同名 `run.log` 的 SHA256 为 `97293111e5d80fbd75acc73611881a42a7fa07e2c5312fd1b86b6f860defd3b2`。作业完成后，四个隔离监听端口均已退出。此次未做独立全量验收、实板测试、模型训练或推送。
