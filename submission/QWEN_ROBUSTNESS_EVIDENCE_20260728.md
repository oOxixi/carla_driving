# Qwen 天气、行人和遮挡鲁棒性证据（2026-07-28）

## 结论

在 CARLA 0.9.16 `Town03_Opt` 中新增 10 张真实 RGB、20 条目标关联指令，
覆盖晴天、暴雨、夜间、浓雾参数、日落、行人和同车道遮挡目标。真实
`Qwen2.5-VL-7B-Instruct` 首轮暴露 6 个漏写目标 ID 的失败；修复通用唯一目标
约束后，两次独立复测均为 20/20。

这是本地冻结代理集，不是主办方隐藏测试集。

## 覆盖

| 项目 | 数量 |
|---|---:|
| 独立 seed / RGB | 10 |
| 指令 | 20 |
| 行人目标场景 | 3 |
| 同车道遮挡目标场景 | 2 |
| 天气配置 | 晴天、暴雨、夜间、浓雾、日落 |

每个目标保留 CARLA actor ID、稳定 `track_id`、类别、距离、车型/行人蓝图和
三维框投影得到的二维框。投影失败的场景不会进入数据集。

说明：`Town03_Opt` 低资源渲染下部分浓雾视觉效果较弱，因此这里只能证明已设置
浓雾参数并完成对应链路测试，不能宣称已充分覆盖所有能见度条件。

## 三轮结果

| 轮次 | 严格解析 | 动作 | 确认 | 目标关联 | 全合同 |
|---|---:|---:|---:|---:|---:|
| round 1 | 100% | 100% | 100% | 70% | 70% |
| round 2 | 100% | 100% | 100% | 100% | 100% |
| round 3 | 100% | 100% | 100% | 100% | 100% |

首轮 6 个失败为：

- 3 个行人目标漏写 ID；
- 2 个遮挡远车漏写 ID；
- 1 个暴雨远车漏写 ID。

没有出现编造 `track_id`。修复后的规则不针对具体样本 ID，而是统一规定：
行人、骑行者、车辆、遮挡目标及“跟随/避让”指令只要唯一匹配检测对象，就必须
复制该对象的 `track_id`。

round 2 和 round 3 合计 40 次推理：

- mean：2351.406 ms
- P95：2478.419 ms
- P99：4211.379 ms
- max：4212.124 ms

## 证据

- `artifacts/qwen_robustness_0728/collection/scenes.jsonl`
- `artifacts/qwen_robustness_0728/collection/cases.jsonl`
- `artifacts/qwen_robustness_0728/collection/images/*.png`
- `artifacts/qwen_robustness_0728/qwen_report_round1.json`
- `artifacts/qwen_robustness_0728/qwen_report_round2.json`
- `artifacts/qwen_robustness_0728/qwen_report_round3.json`

## 边界

- 当前标注来自 CARLA 真值投影，不等价于真实道路检测器输出；
- 当前总量仍只有 10 张图和 20 条指令；
- 尚未覆盖不同相机曝光、重度运动模糊和密集人群；
- 官方隐藏测试集成绩仍需以主办方评测为准。
