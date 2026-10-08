# 应用指标结果表（已有证据复算）

安装：将 overlay 的 `payload` 内容合并到完整材料包根目录并保持相对目录。复算需完整包中的保存预测、冻结标签、历史 ASR 结果及其音频输入；这些原件不随本 overlay 重复上传。脚本默认从自身位置定位材料包，也可用 `--package-root /path/to/package` 指定另一份完整包。

本目录给出可直接引用的结果及来源哈希；不是 B2 Gate 签署，也不代表新增未见样本评测。

| 集合 | 模型/条件 | 指标 | 分子/分母 | 结果 |
|---|---|---|---|---|
| 240已存预测 | Teacher | step_count_agreement | 240/240 | 100.0000% |
| 240已存预测 | Teacher | behavior_sequence_agreement | 240/240 | 100.0000% |
| 240已存预测 | Teacher | behavior_agreement | 262/262 | 100.0000% |
| 240已存预测 | Teacher | completion_type_agreement | 262/262 | 100.0000% |
| 240已存预测 | Teacher | target_lane_agreement | 262/262 | 100.0000% |
| 240已存预测 | Teacher | target_id_agreement | 262/262 | 100.0000% |
| 240已存预测 | FP32 | step_count_agreement | 240/240 | 100.0000% |
| 240已存预测 | FP32 | behavior_sequence_agreement | 238/240 | 99.1667% |
| 240已存预测 | FP32 | behavior_agreement | 260/262 | 99.2366% |
| 240已存预测 | FP32 | completion_type_agreement | 260/262 | 99.2366% |
| 240已存预测 | FP32 | target_lane_agreement | 260/262 | 99.2366% |
| 240已存预测 | FP32 | target_id_agreement | 262/262 | 100.0000% |
| 240已存预测 | INT8 | step_count_agreement | 240/240 | 100.0000% |
| 240已存预测 | INT8 | behavior_sequence_agreement | 238/240 | 99.1667% |
| 240已存预测 | INT8 | behavior_agreement | 260/262 | 99.2366% |
| 240已存预测 | INT8 | completion_type_agreement | 260/262 | 99.2366% |
| 240已存预测 | INT8 | target_lane_agreement | 260/262 | 99.2366% |
| 240已存预测 | INT8 | target_id_agreement | 262/262 | 100.0000% |
| 250历史TTS音频 | local_clean_250_final_20260726 | asr_exact_accuracy | 239/250 | 95.6000% |
| 250历史TTS音频 | local_clean_250_final_20260726 | asr_character_accuracy | 1445/1456 | 99.2445% |
| 250历史TTS音频 | local_clean_250_final_20260726 | intent_accuracy | 249/250 | 99.6000% |
| 250历史TTS音频 | local_clean_250_final_20260726 | slot_accuracy | 248/250 | 99.2000% |
| 250历史TTS音频 | local_synthetic_snr10_250_20260726 | asr_exact_accuracy | 236/250 | 94.4000% |
| 250历史TTS音频 | local_synthetic_snr10_250_20260726 | asr_character_accuracy | 1441/1456 | 98.9698% |
| 250历史TTS音频 | local_synthetic_snr10_250_20260726 | intent_accuracy | 244/250 | 97.6000% |
| 250历史TTS音频 | local_synthetic_snr10_250_20260726 | slot_accuracy | 247/250 | 98.8000% |
| 250历史TTS音频 | local_clean_250_cascade_priority_20260726 | asr_exact_accuracy | 239/250 | 95.6000% |
| 250历史TTS音频 | local_clean_250_cascade_priority_20260726 | asr_character_accuracy | 1445/1456 | 99.2445% |
| 250历史TTS音频 | local_clean_250_cascade_priority_20260726 | intent_accuracy | 249/250 | 99.6000% |
| 250历史TTS音频 | local_clean_250_cascade_priority_20260726 | slot_accuracy | 248/250 | 99.2000% |
| 83场闭环 | FP32 | scenario_task_success | 63/83 | 75.9036% |
| 83场闭环 | FP32 | scenario_behavior_oracle_alignment | 77/80 | 96.2500% |
| 83场闭环 | FP32 | extension_acceptance | 70/83 | 84.3373% |
| 83场闭环 | INT8 | scenario_task_success | 63/83 | 75.9036% |
| 83场闭环 | INT8 | scenario_behavior_oracle_alignment | 77/80 | 96.2500% |
| 83场闭环 | INT8 | extension_acceptance | 70/83 | 84.3373% |
| 850源报告聚合 | FP32 | step_count_agreement | 849/850 | 99.8824% |
| 850源报告聚合 | FP32 | behaviour_agreement | 927/931 | 99.5704% |
| 850源报告聚合 | FP32 | lane_agreement | 929/931 | 99.7852% |
| 850源报告聚合 | FP32 | completion_agreement | 929/931 | 99.7852% |
| 850源报告聚合 | FP32 | target_id_agreement | 189/213 | 88.7324% |
| 850源报告聚合 | FP32 | speed_within_0p5_mps_rate | 209/931 | 22.4490% |
| 850源报告聚合 | INT8 | step_count_agreement | 849/850 | 99.8824% |
| 850源报告聚合 | INT8 | behaviour_agreement | 927/931 | 99.5704% |
| 850源报告聚合 | INT8 | lane_agreement | 929/931 | 99.7852% |
| 850源报告聚合 | INT8 | completion_agreement | 929/931 | 99.7852% |
| 850源报告聚合 | INT8 | target_id_agreement | 189/213 | 88.7324% |
| 850源报告聚合 | INT8 | speed_within_0p5_mps_rate | 196/931 | 21.0526% |

240 条以保存的 Qwen Teacher 计划作标签，Teacher 的 100% 是自身标签一致率。所有参考步纳入分母，Student 缺步按错误，null 目标对 null 目标按相等。行为序列一致率仅比较行为与步数，不包含速度等连续字段。原诊断明确标签在适配器修订前已暴露，因此这些数字只用于事后应用诊断。当前 FP32 与 INT8 在表内语义计划指标无额外下降，不能代称 ASR 指标。

83 场采用场景自带的 oracle_expected_behaviors 判据；只有 80 场有该检查，其余 3 场不进入对齐分母。任务完成、扩展验收、oracle 对齐是不同指标。表中数字来自保存的聚合记录，复算脚本只复核其分组计数与失败数。

850 例六队列/931 个 Teacher 步的输入数量已经复算。当前 v3.1 的保存聚合结果：FP32/INT8 行为对齐均为 99.5704%，车道/完成类型均为 99.7852%；Teacher 提供目标时目标一致率 88.7324%。这批 Student 逐例输出不在包内，故只收录为源报告聚合证据，不能冒充新复算。速度缺值有 561 步；原报告 MAE 使用包含缺值的分母，不应据此宣传低速度误差。

250 条音频均为 edge-tts 合成，历史报告确实执行过音频识别；完全匹配/字符准确率/意图/槽位指标分开列出。10 dB SNR 数字加噪不能写为 50 dBA。没有材料证明官方强制真人音频。

压缩模型接收已转写文本，可确认 ASR 是上游独立模块。尚无当前 Teacher/FP32/INT8 共用前端的同次运行清单与权重、配置绑定，故不能写“当前 ASR 衰减 0%”。正式衰减仍需当前同输入的保存转写结果及模型前端身份，正式 B2 Gate 还需未见独立测试集与冻结判据。

运行复算：`python recompute_results.py`。只读包内保存的数据，不运行模型/CARLA，不联网；只覆盖本目录三份结果。`application_results.json` 保存逐例差异、模型身份、限制及全部输入哈希，`application_metrics.csv` 为可引用表。
