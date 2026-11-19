# robust-v3 速度Head专项训练

结论：第38轮速度Head候选在既有Val上通过预定筛选，其他9个Head逐字节一致。已知组合设速失败的固定输入回放改善到19.73 km/h；单独20 km/h指令仍有3.04 km/h误差。此结果是开发候选，不是独立Test、闭环或正式Gate通过。

## 数据与训练

- 权重起点是robust-v3，SHA256 `7f379c78c170228713e3d91b8e2eabd04172010ae0ed0b8cf71afe291fe6e805`。训练后复验原文件SHA不变。
- 复用原严格正样本视图 `b1_governed_closeout_v1_a3_strict_positive_v1`，**5856 Train / 1108 Val**。核验原视图、Train/Val及来源清单的哈希，使用现有preflight校验split、Teacher provenance、合同和真实RGB；0错误。未读取独立Test进行训练或选模，也未把本轮已知失败输入回灌。
- Teacher为 `Qwen/Qwen3.5-2B`，revision `15852e8c16360a2fea060d615a32b45270f8a8fc`；保留原清单对历史运行身份样本的限制，不反向补签Teacher provenance。
- 速度标签单位m/s。Train/Val的数值标签共6327/1213步；SET_SPEED中标签与请求hint相差超过0.5 m/s的有19/10步，仅列为审核线索，未认定都是错标，也未改写标签。
- 冻结主干和其他Head，用原A1打包器提取冻结特征，只优化速度Head的4100个参数；masked Smooth L1、原风险权重、AdamW `3e-5`、40轮。仅用Val择优：总体MAE至少改善0.002 m/s，SET_SPEED、安全关键、后续步骤切片MAE不得退化。
- 服务器GPU 4执行；隔离源提交 `5958103606d63232b1482a001b5bf8abbff00bbf`。新增冻结/指标测试和原loss测试共4项通过。生产服务未换模型，未推送GitHub。

## 同口径Val对比

| 指标（MAE，m/s） | 原robust-v3 | 速度Head候选 |
| --- | ---: | ---: |
| 全部数值步骤，1213步 | 0.3782 | 0.2004 |
| SET_SPEED，345步 | 0.5029 | 0.3215 |
| 安全关键，165步 | 0.5315 | 0.0697 |
| 后续步骤，105步 | 1.0826 | 0.0697 |

全部数值步骤的±0.5 m/s命中率从74.03%增至89.69%。仅 `target_speed_head.weight` 和 `target_speed_head.bias` 改变。加载选中Head后重新跑完整Val，确认9个非速度Head的输出逐字节相同；这不表示速度变化后的实际轨迹也完全相同。

## 已知失败回放（选模后）

复用前次闭环的三条真实请求，核对四路实际输入张量SHA与当次记录一致，原模型CPU回放与已记录ONNX输出数值一致。不是新CARLA运行，也不是独立Test。

| 任务 | 原目标速度 | 新目标速度 | 对20±2 km/h的结果 |
| --- | ---: | ---: | --- |
| 单独设速20 km/h | 15.78 | 16.96 | 改善，仍未达标 |
| 先左换道再设速20 km/h（第二步） | 10.26 | 19.73 | 固定输入回放达标 |

STOP仍保持原输出合同，目标pointer不变；速度Head训练不会修复目标绑定。未更改Adapter或安全门禁，也未用请求数字直接覆盖模型速度。

## 产物

本机 `artifacts/speed_head_repair_20261111/trial_01/`、服务器 `/home/tiaozhansai/carla-driving-challenge/artifacts/speed_head_repair_20261111/trial_01/`：

- `student_speed_head_candidate.pt`：完整FP32候选权重，SHA256 `0fa3c63494be69503059a4f4f30d87b1a04dd0b6ca5ccec947ad4124272d3287`。
- `run_config.json`、`dataset_preflight.json`、`label_audit.json`、`training.jsonl`、`result.json`：配置、数据核验、标签审核、训练过程及Val结果。
- `known_failure_replay.json`：三条固定输入回放，含trace哈希、每步预测及Adapter速度。

证据包 `speed_head_trial_01_evidence.tar.gz` SHA256：`ee76312b3342023d2ec9043d5ce82119c724192476786eac994891cb9d11f8ef`。下一步应独立验证显式速度档位与指令改述，复测组合闭环；不得用两条已知失败样本直接调参后再把它们当独立成绩。
