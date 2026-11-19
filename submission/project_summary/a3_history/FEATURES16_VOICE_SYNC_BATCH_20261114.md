# 普通话录音与同帧路况：四例开发回归

在 Town03_Opt（seed 173061）中接入真实普通话录音，使用 SenseVoice + LoRA + VAD。Qwen3.5-2B Teacher 实时接收 CARLA 请求；FP32 和 Features16 BC 在 OE 容器中回放该请求及其同帧 RGB，不接管车辆。录音来自已有开发集，并非独立 Test；没有明确标注的多步录音，本批不衡量组合任务能力。

| 录音用例 | 判定基准 | Qwen Teacher | Student FP32 | Features16 BC |
| --- | --- | --- | --- | --- |
| 提到 40（第 298 帧） | 保持在实际限速 30 内 | 30.00 km/h | 30.00 km/h | 29.76 km/h |
| 降到 25（第 855 帧） | 目标 25，允许误差 ±2 km/h | 25.00 km/h | 23.90 km/h | 24.09 km/h |
| 请求左变道（第 1425 帧） | 左侧车道不存在，安全拒绝；不作横向动作 | 无有效计划，失败 | STOP | STOP |
| 另一种设速 30 说法（第 2030 帧） | 目标 30，允许误差 ±2 km/h，且不得超实际限速 | 30.00 km/h | 29.84 km/h | 29.76 km/h |

- 音频与同帧证据 4/4 完整，ASR 归一化文本 4/4 匹配。计划或安全拒绝：Teacher 3/4、FP32 4/4、Features16 BC 4/4。两种 Student 的 STOP 是离线计划，不是闭环停车结果。
- 左侧不可用时，Teacher 仍输出了指向 LEFT_ADJACENT 的步骤；适配器以 TARGET_LANE_UNAVAILABLE 拒绝（HTTP 502），路由记为 QWEN_ERROR，未产生有效替代计划。拒绝拦住了不可执行动作，但此次任务不能计为安全拒绝成功。
- Teacher 实时闭环任务 3 成功、1 失败，合计 0 次碰撞、0 次侵线。这是小样本开发回归，不是比赛准确率、正式 Gate 或 Student 实车/仿真闭环结果。
- 下一批应单独冻结新录音与人工参考标签，覆盖组合指令、让行和跟车；左侧不可用需区分「用户想左变道」和「当前路况下可执行的安全替代计划」，不改写原意或实验标签。

锁定口径：`voice_sync_batch_reference.json`，SHA256 `21bb4e630ae892dc449e5e6ed2375e5df67a5a9c5d81d0638bce19bb0a61a591`。
证据：`artifacts/numeric_speed_conditioned_20261112/voice_sync_run.bT3FfZRd/three_way_batch.json`，SHA256 `c018a618414f71aa6f47a73385384919e7220e8b9d170b8595a5275de96ed27b`。
