# 配置目录

- `strategy_config.yaml`：A/B/C/D 共用的速度、曲率、安全距离和降级策略；由
  `config.strategy` 严格加载。
- `driving_policy.json`：正式场景可覆盖的感知与最终安全阈值。
- `generalization_matrix.json`：Variant/Unseen 场景确定性变换矩阵。
- `repro/`：不同机器的可复现环境变量模板。

配置文件只保存跨场景策略，不允许写场景 ID、固定出生点或仅为单个地图成立的特判。
