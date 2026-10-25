# main_optimization 泛化回归与证据说明

## 使用范围

当前地图固定为 Town03_Opt，生产模型使用 Qwen/Qwen3.5-2B，模式为 planner_v2。官方 S2 场景 JSON 保持原合同；扰动场景生成到 artifacts/validation 下，每次实验使用独立目录。

`config/s2_optimization_matrix.json` 定义 12 个可复现变体，组合 5 个 seed、三种傍晚天气、0.05/0.10 s 周期、Actor 纵横偏移、0.8/1.0/1.2 倍速度、行人启动时刻，以及正常/RGB 降采样/LiDAR 减少通道三种输入条件。Actor 数量与业务目标绑定不变，车道关系遵循原场景合同。

五个目标窗口分别为公交站、行人避让与超车返回、自行车、交叉口切入、末段行人，共 60 个定点闭环任务。它们是同地图 Variant，不能作为跨地图 Unseen 的证据。

## 生成与运行

在仓库根目录执行。仅生成和静态校验不会启动 CARLA：

```bash
python tools/run_s2_optimization_matrix.py \
  --output-dir artifacts/validation/s2_matrix_build_<timestamp>
```

服务器使用其现有虚拟环境 Python。显式选择变体和事件后才执行真实闭环：

```bash
/home/tiaozhansai/carla-driving-challenge/.venv/bin/python \
  tools/run_s2_optimization_matrix.py \
  --output-dir artifacts/validation/s2_sparse_ped_<timestamp> \
  --run --case-index 5 --event late_pedestrian \
  --host 127.0.0.1 --port 2100 --qwen-url http://127.0.0.1:18005
```

`--case-index` 和 `--event` 可以重复。事件名为 `bus_stop`、`pedestrian_overtake`、`bicycle`、`cut_in`、`late_pedestrian`。相同 CARLA 世界只能顺序执行；不要与正式 S2 或队友的闭环进程并发。

每个实验目录包含 `matrix_manifest.json`、具体场景 JSON、各任务控制台日志，以及原始 JSONL、summary、provenance。已有目录拒绝覆盖。manifest 记录每个配置的 SHA256、具体命令、运行结果及原始 summary 哈希。

## 目标段判定

定点运行从事件前恢复到路线里程；先前完成的命令由恢复机制显式记录。报告要求目标阶段成功、实际 QWEN_PLAN、外部命令唯一成功终态、生产 Qwen 2B 健康信息、Actor 激活、驶过事件出口、恢复至少 32 km/h、无碰撞/违规/路线偏离。自行车额外要求 3 m 净距；超车任务额外要求恢复任务路线。

报告的 scope 为 `event_segment`，完整 8 km 状态为 `NOT_EVALUATED`。未执行的后续命令和未跑完的长程路线仍保留在原始 summary 中；原始整场景可能显示 FAILED。只有独立的目标段检查全部通过，目标段才算 PASS。缺少阶段、终态、出口里程或模型证据都会失败。

延迟数值继续记录；当前定点功能回归不以延迟判定通过。正式比赛 checker 仍使用原阈值。selected tasks 通过不表示整个 60 任务矩阵已通过；新版 manifest 只有全部任务通过才标记 PASS，否则已执行子集通过标记 PARTIAL_PASS，并显示未运行任务数量。

检查项改进后，可基于原始 manifest 重新检查已有证据，无需重复驾驶：

```bash
python tools/run_s2_optimization_matrix.py \
  --evaluate-manifest artifacts/validation/<previous-run>/matrix_manifest.json \
  --output-dir artifacts/validation/<reevaluation-timestamp>
```

该过程核验保存的场景与 summary 哈希，并要求事件起止窗口和预算一致；不覆盖历史 manifest，不把评估代码当前的 SHA 写成历史驾驶代码版本。

## 证据追踪

运行器现在在 run_start、summary 和独立 `.provenance.json` 中记录实际 git HEAD、dirty 状态、修改差异哈希、未跟踪文件哈希、场景文件 SHA256、Python/依赖版本、机器信息、Qwen 模型/revision/artifact fingerprint，以及传给传感器蓝图的有效参数。外部 `CARLA_DRIVING_CODE_VERSION` 标签与实际 HEAD 分开保留。

RGB 尺寸和 LiDAR 通道扰动会由 `sensor_specs_for_scenario` 传入真实传感器创建过程。之前版本的生成器虽修改 JSON，但运行器仅取固定 profile；因此旧报告中的 reduced_rgb/sparse_lidar 名称只证明配置生成，不能据此宣称硬件传感器参数已改变。旧报告的 Actor、时序与控制证据应分别检查。

`command_terminal_statuses` 与旧 `qwen_status_counts` 保留原始统计。新增 `command_statistics` 将外部指令、内部执行步骤、内部 Qwen 等待停车分开；extension evidence 新增 `external_qwen_terminal_statuses` 和 `external_qwen_status_counts`。内部等待被后续计划替换时的 FAILED 仍可追查，不算外部业务失败。失败阶段不再进入 completed_phase_ids。

`safety_overrides_by_reason` 给出每种原因的帧数、原因段数和类别。连续接管中原因发生改变会拆分原因段，所以原因段数之和可能大于原 continuous override episodes。前障碍类只是触发原因，不能在没有独立真值时直接叫作误刹车。

## 审计已有日志

无需重跑，通过流式读取原始 JSONL 生成旁路审计：

```bash
python tools/summarize_optimization_evidence.py <run.jsonl> \
  --output artifacts/validation/<run>_scoped_audit.json
```

审计工具不修改原日志、分数或 Gate。历史未记录 dirty/config fingerprint 时，provenance 显示 LEGACY_NOT_RECORDED；不能用当前 SHA 反向补签历史运行。

2026-10-24 完整 S2 的重新审计得到：外部 6 SUCCEEDED、内部执行步骤 6 SUCCEEDED、内部等待 6 FAILED。17,216 个接管帧中，16,503 帧来自红灯停止线保护；前障碍相关为 CAUTION_TTC 272 帧、速度上限制动 437 帧、紧急前障碍制动 4 帧。完整运行的功能通过和 236.48 ms 延迟超限结论保持原样。
