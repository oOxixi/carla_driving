# Qwen 多图像多目标关联证据（2026-07-28）

## 结论

在服务器 `tiaozhansai` 的 GPU 0 上，使用本地
`Qwen2.5-VL-7B-Instruct` 和 CARLA 0.9.16 `Town03_Opt` 完成了真实 RGB
多目标关联批测。

- 5 个独立 seed、5 张真实 CARLA RGB；
- 每张图包含 2 个真实车辆 actor，共 10 条定向指令；
- 每个目标均保存 CARLA actor ID、稳定 `track_id`、距离、车型和投影框；
- 修正提示约束后的两次独立批测均为 10/10；
- 严格解析、动作、确认、目标关联及全合同准确率均为 100%。

这是本地冻结代理集结果，不是主办方隐藏测试集成绩。

## 数据采集

采集工具：`tools/collect_qwen_target_scenes.py`

每个 seed 创建：

1. 一辆自车；
2. 一辆正前方车辆；
3. 一辆左侧或右侧相邻车道车辆；
4. 一台固定在自车上的 800×450、90° FOV 前视 RGB 相机。

目标框由 CARLA actor 的三维包围盒通过相机内外参投影得到。若目标不在画面内或
投影框无效，采集器直接失败，不会生成该样本。

数据文件：

- `artifacts/qwen_target_assoc_0728/collection/scenes.jsonl`
- `artifacts/qwen_target_assoc_0728/collection/cases.jsonl`
- `artifacts/qwen_target_assoc_0728/collection/collection_report.json`
- `artifacts/qwen_target_assoc_0728/collection/images/*.png`

## 输出边界

Qwen 响应 schema 新增可受控验收的 `target_track_id`：

- 只能逐字复制 `perception.detected_objects[].track_id`；
- 不允许编造不存在的 ID，适配器会拒绝；
- 指令存在唯一空间目标时必须返回该字段；
- 目标不唯一时要求确认并省略目标；
- 模型仍禁止输出油门、刹车、方向盘等底层控制量。

## 迭代与失败保留

| 轮次 | 严格解析 | 动作 | 确认 | 目标关联 | 全合同 |
|---|---:|---:|---:|---:|---:|
| round 1 | 100% | 100% | 100% | 60% | 60% |
| round 2 | 100% | 100% | 100% | 100% | 100% |
| round 3 | 100% | 100% | 100% | 100% | 100% |

round 1 的 4 个失败均为相邻车道目标漏写 `target_track_id`，没有编造目标。修复为：
当指令包含正前方、左/右相邻车道等唯一目标描述时，明确要求必须返回
`target_track_id`，且不能用速度或解释字段替代。失败报告原样保留。

round 2 和 round 3 合计 20 次推理延迟：

- mean：2435.593 ms
- P95：4096.396 ms
- P99：4223.645 ms
- max：4255.457 ms

Qwen 延迟为事件触发的高层决策延迟，不应放入逐帧控制环。

## 证据

- `artifacts/qwen_target_assoc_0728/qwen_report_round1.json`
- `artifacts/qwen_target_assoc_0728/qwen_report_round2.json`
- `artifacts/qwen_target_assoc_0728/qwen_report_round3.json`
- `artifacts/qwen_target_assoc_0728/evidence_manifest.sha256`

## 仍未证明

- 5 张图、10 条指令规模较小，不足以替代大规模冻结集或官方隐藏集；
- 当前只覆盖白天、晴天、前方和相邻车道车辆；
- 尚需扩展夜间、雨雾、遮挡、行人/骑行者及检测器误差条件；
- 标注来自 CARLA 真值投影，不能代替真实道路人工标注；
- 仍需 30 分钟持续运行的 FPS、掉帧、显存、超时及恢复统计。
