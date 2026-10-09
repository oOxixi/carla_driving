# 新 CPU 850 例离线补采结果

New local CPU offline replay; no ASR or CARLA; stored Teacher labels not rerun; no official-image timing or formal B2 Gate.

| 模型 | 指标 | 分子/分母 | 值 |
|---|---|---|---|
| FP32 | prediction_success | 850/850 | 100.000000% |
| FP32 | step_count_agreement | 849/850 | 99.882353% |
| FP32 | semantic_plan_agreement | 821/850 | 96.588235% |
| FP32 | behavior_sequence_agreement | 845/850 | 99.411765% |
| FP32 | behavior_agreement | 927/931 | 99.570354% |
| FP32 | completion_agreement | 929/931 | 99.785177% |
| FP32 | lane_agreement | 929/931 | 99.785177% |
| FP32 | target_agreement | 907/931 | 97.422127% |
| FP32 | target_id_agreement_when_teacher_present | 189/213 | 88.732394% |
| FP32 | speed_within_0p5_mps_including_missing_as_failure | 209/931 | 22.448980% |
| FP32 | numeric_speed_coverage | 370/931 | 39.742213% |
| INT8 | prediction_success | 850/850 | 100.000000% |
| INT8 | step_count_agreement | 849/850 | 99.882353% |
| INT8 | semantic_plan_agreement | 821/850 | 96.588235% |
| INT8 | behavior_sequence_agreement | 845/850 | 99.411765% |
| INT8 | behavior_agreement | 927/931 | 99.570354% |
| INT8 | completion_agreement | 929/931 | 99.785177% |
| INT8 | lane_agreement | 929/931 | 99.785177% |
| INT8 | target_agreement | 907/931 | 97.422127% |
| INT8 | target_id_agreement_when_teacher_present | 189/213 | 88.732394% |
| INT8 | speed_within_0p5_mps_including_missing_as_failure | 192/931 | 20.622986% |
| INT8 | numeric_speed_coverage | 370/931 | 39.742213% |

All 850 cases and all 931 Teacher steps; missing predicted steps count as mismatches. Null target equals null target in all-step target metric; separate nonnull-Teacher target metric is supplied. Semantic plan compares behavior, completion type, target lane and target ID plus sequence length; speed omitted from this categorical signature and reported separately.

Teacher 100% 基线表示自身保存标签一致率，并非独立人工真值。语义字段一致不代表完整数值计划等同；速度覆盖、误差和缺值必须同时查看。新结果独立保存，不覆盖旧 B3 成绩；旧的包含缺值分母 MAE 不在此沿用。

具体逐例错误、模型/输入/源码和原始输出文件哈希见 comparison.json。
