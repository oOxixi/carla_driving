# V3.1 Adapter 与 INT8 回归诊断（2026-10-08）

## 结论

V3 权重和 FP32 ONNX 字节保持不变，在 `StudentPlanAdapter` 中落地固定的 V3.1
语义契约后，B1 Independent Validation v1 的 240 条回放阈值投影由 FAIL 变为
**PASS**。Full INT8 与 Mixed Top-3 在相同 Adapter 下也都得到 PASS 投影，且与 FP32
的 240/240 个计划核心字段完全一致。

这里的 PASS 只表示**已暴露集合上的回归阈值投影通过**，不是 B2 正式 Gate：Adapter
修订发生在查看旧 240 条结果之后，必须由 B2 在新的未暴露集合上独立复核，才可签发
`A3_FP32_GATE_PASSED` / `A2_INT8_GATE_PASSED`。

## 实现内容

Adapter V3.1 合同 ID：`student-plan-adapter-v3.1-semantic-contract`。

1. 对 `KEEP_LANE/SET_SPEED/SLOW_DOWN/STOP/YIELD/FOLLOW/HOLD` 显式输出
   `target_lane=CURRENT`，消除 `null`/`CURRENT` 表示歧义；
2. 仅在 `route_available=true`、命令明确为 TURN 且方向确定时，允许模型提前输出对应
   转弯；反方向转弯始终被屏蔽；
3. 转弯步骤继续保留 `INTERSECTION_AHEAD` 前置条件。FSM 在路口未出现时输出
   `safe_behavior=SLOW_DOWN`，不会提前执行转弯；
4. `AVOID_OBSTACLE` 使用模型预测且经场景能力验证的相邻车道；预测车道不存在时可切到
   另一条真实存在的相邻车道，两侧都不存在时 fail-closed；
5. `SLOW_DOWN` 的 completion 固定为 `SPEED_BELOW`，并在指针有效时保留目标 ID；
6. `left/right_gap_safe=false` 的普通换道仍被屏蔽为 STOP，未为追求指标移除安全门。

实现代码提交：`2900258aa97392a1ed9936748decfc8c27067cd9`；Adapter 文件 SHA256：
`bb30726b8287b422516820af8e8af21e5d6a205cd81d3f9de6871de9badfcf21`。

## FP32 回归结果

模型身份保持：weights `7f379c78...6e805`，FP32 ONNX `681a5d4b...b4286`。

| 指标 | Teacher | V3.1 FP32 | 下降 | 限值 | 投影 |
|---|---:|---:|---:|---:|---|
| behavior accuracy | 1.000000 | 0.992366（260/262） | 0.007634 | 0.015 | PASS |
| target pointer accuracy | 1.000000 | 1.000000（262/262） | 0 | 0.015 | PASS |
| target lane accuracy | 1.000000 | 0.992366（260/262） | 0.007634 | 0.015 | PASS |
| completion accuracy | 1.000000 | 0.992366（260/262） | 0.007634 | 0.015 | PASS |
| plan sequence accuracy | 1.000000 | 0.991667（238/240） | 0.008333 | 0.015 | PASS |
| safety-critical behavior recall | 1.000000 | 1.000000（28/28） | 0 | 0 | PASS |

240/240 推理成功，schema validity = 1.0。剩余两个不一致样本均为 Teacher 要求
`CHANGE_LANE_LEFT`、但输入明确给出 `left_gap_safe=false`；Student 输出 STOP。因此这两个
差异是保留运行时安全约束的结果，不应通过取消安全门修成 100%。

FP32 证据目录：`artifacts/b2_role_exception_v3_1_adapter_20261008_final/`；report SHA256：
`bb9a2e5a08de59f7e795095942b6ee161cb3c283a7d16f8b55260d35f9572585`；raw Student
predictions SHA256：`75148883dbcaee1a661989136ed4685ee03d56b8327ecebfa811a070e40d3285`。

## INT8 同口径结果

两份 INT8 均为 240/240 合法输出，Teacher 指标与上表 FP32 完全相同；相对 FP32 的
behavior、target pointer、target lane、completion 和完整计划核心字段均为 **100% 一致**。

| 候选 | SHA256 | 大小 | FP32 核心字段一致 | 速度绝对差（109 步） | 投影 |
|---|---|---:|---:|---:|---|
| Full INT8 | `275dce5c...836c3` | 23,273,686 B | 240/240 | mean 0.150893、P95 0.395727、max 0.597761 m/s | PASS |
| Mixed Top-3 | `9a08a03c...132d3` | 23,622,853 B | 240/240 | mean 0.150893、P95 0.395727、max 0.597761 m/s | PASS |

两份 INT8 在这 240 条上的解码 predictions 字节完全相同，SHA256 均为
`445f4a6df643cd91c2cf70f50b669d9134f905cdc12c06e69b545f2aca995038`。

推荐把 **Mixed Top-3** 作为下一轮未暴露 B2 Gate 的首选候选，把 Full INT8 保留为体积
优先备选。理由不是旧 240 标签，而是先前冻结 Calibration v1 的逐 Head 漂移证据：Mixed
恢复 behavior/pointer/lane 三个敏感输出层，离散头 MAE 更低；代价仅比 Full 增加
349,167 B（约 1.50%），速度头漂移与 Full 相同。最终选择仍需 B2 未暴露集与 A4 编译
代价共同确认。

- Full INT8 证据：`artifacts/b2_role_exception_v3_1_full_int8_20261008_final/`，report
  SHA256 `d970ffb87ca8eb0791b4c7944627568c3164826374bf40699870008234b36931`；
- Mixed Top-3 证据：`artifacts/b2_role_exception_v3_1_mixed_int8_20261008_final/`，report
  SHA256 `4326f032e9a5baa02355f1657f1a96ca0426980c9d65a07cfb7f86d138141e4b`。

本机 CPU 时间只作冒烟诊断；两份 final 证据是并行执行，禁止据此比较二者延迟。

## 测试与边界

- Adapter 定向测试：21 passed；
- Student 核心测试（排除两个 Windows 临时目录 ACL 用例）：31 passed；
- schema/compiler/FSM/语义归一化回归：34 passed；
- INT8 诊断工具单元测试：3 passed；
- FP32、Full INT8、Mixed Top-3 三次 240 条回放均为 240/240 SUCCESS。

两个 `tmp_path` 测试在当前 Windows 主机因 pytest 临时目录 ACL 无法建立而未执行；相同文件
中的其余 31 项已通过。这是本机测试基础设施限制，不计作模型 PASS，也未被隐瞒。

正式剩余项：B2 冻结新未暴露 benchmark/policy 并独立复测 exact
weights+ONNX+Adapter；通过后 A2 才能生成正式 INT8 manifest；随后 A4/B3 对 exact
候选补齐 OpenExplorer Runtime、`.bc/.hbm` 与 J6P 实测，B4 才能建立 Final。
