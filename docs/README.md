# 文档索引

- `REPOSITORY_STRUCTURE.md`：所有顶层目录和主要子目录的用途。
- `setup/`：CARLA 等基础环境说明。
- `runbooks/`：当前可执行的部署、联调和运行手册。
- `reproduction/`：2B 模型与提交包复现说明。
- `reference/`：语音命令定义等只读参考材料。
- `reports/`：路线、场景、控制、安全和分支归并的当前验证记录。
- `modules/`：按职责拆分的模块说明、上下游合同、运行门禁和当前阻塞项。
- `GENERALIZATION_ARCHITECTURE.md`：路线相对场景、真值隔离、五阶段运行边界和泛化测试门禁。

当前已经细化的挑战赛道模块：

- [`modules/B1_TO_A3_DATA_PIPELINE.md`](modules/B1_TO_A3_DATA_PIPELINE.md)：B1 发布包进入 A3
  蒸馏前的身份、完整性、切分、派生视图和训练门禁；包含 D2 v1.1 已验证路径与 D3
  Wave1 当前接入结论。
- [`modules/MODEL_AND_WEIGHT_LIFECYCLE.md`](modules/MODEL_AND_WEIGHT_LIFECYCLE.md)：Teacher、
  Student FP32、INT8 和 Runtime 的模型身份、权重状态机、晋级门禁与当前阻塞项。
- [`modules/A3_TRAINING_AND_HARD_CASES.md`](modules/A3_TRAINING_AND_HARD_CASES.md)：A3 的
  运行等级、Loss、Validation、确定性恢复、产物语义和三类 Hard-case 闭环边界。
- [`modules/B2_EVALUATION_AND_FP32_GATE.md`](modules/B2_EVALUATION_AND_FP32_GATE.md)：
  独立 Validation、FP32 promotion、B2 Frozen Benchmark、证据合同与防泄露边界。
- [`modules/A2_INT8_QUANTIZATION_AND_QAT.md`](modules/A2_INT8_QUANTIZATION_AND_QAT.md)：
  真实 FP32 导出、Calibration、PTQ、敏感层、QAT、INT8 Gate 与 A4/B3 交接合同。

架构边界分别见各模块的 `README.md` 或 `ARCHITECTURE.md`。正式场景定义与验收条件以
`scenarios/` 为准；运行生成的日志、截图、点云和临时报告只放 `artifacts/`。
