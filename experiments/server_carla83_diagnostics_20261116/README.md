# CARLA 泛化小测：作业 40 临时采证代码

对应服务器 `carla-driving-challenge/artifacts/numeric_speed_conditioned_20261112/new4_layers.KmDNGatX/`。
保留了复跑脚本、临时 runner（逐帧零速来源）和临时 Student 服务（长度、动作 logits、解码前后动作）。
这些文件配合当时的作业 38 执行快照，仅用于诊断；没有覆盖 `main` 的正式入口，也不改变评分与安全逻辑。
详见[同次记录和归因](../../challenge/distillation/CARLA_GENERALIZATION_HANDOFF_20261116.md)和
[已归档的原 83 场分场判定](../../submission/project_summary/closure/carla83_paired_report.json)。
