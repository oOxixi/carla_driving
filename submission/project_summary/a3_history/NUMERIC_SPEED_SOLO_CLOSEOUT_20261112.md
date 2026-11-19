# 首步速度 Head：单人验收与部署预检

结论：**850 例内部 FP32 回归已完成，新版保留为冻结开发候选。**
单人可执行采集、评测和验收，不需要等待 A/B 岗位互签。独立性由候选先冻结、
输入未曝光、同协议评测和不可回灌调参来保证，不能用岗位合并替代这些条件。

## 实测结果

在 tiaozhansai 对提交材料所列六个固定队列完成双模型 CPU ONNX 回放。六份
案例文件与 challenge `2da949be` 历史预检的 SHA256 在统一 CRLF 后全部匹配，
850 张 RGB 逐张核验。使用同一预处理、同一 Adapter、同一保存的 Teacher
参考计划；未运行 Teacher、ASR 或 CARLA 闭环。本轮的旧版是同权重诊断再导出，
不是历史 A2 ONNX 的同字节复现。

| 指标 | 旧版 | 新版 |
|---|---:|---:|
| 有效计划 | 850/850 | 850/850 |
| 语义计划完全一致（动作、完成条件、目标车道、目标 ID；不含速度） | 843/850 | 843/850 |
| 动作 | 927/931 | 927/931 |
| 目标 ID | 931/931 | 931/931 |
| 可配对目标速度 MAE（472 步） | 0.4930 m/s | 0.2455 m/s |

两版的上述离散计划字段逐例一致（850/850）。可配对速度误差下降 50.2%；
可配对条件为同位置的预测动作均与参考一致，且两版与参考都有数值速度。
这批是已曝光的验证队列，不是独立盲测；速度误差不计为比赛核心准确率或实际车速。
上轮 240 条历史回归与本轮证据分开保留，不合并成独立样本总量。

## 还不能签发的项目

- **独立 FP32 验收。** 通用配置仍未完成，但既有 prospective 专用配置的冻结
  判分策略已通过 readiness（含阈值、切片分母、合并规则）。该设计绑定旧 V3，
  没有已采 case manifest。新版训练使用开发补样，不能套用旧的正式 handoff 签名
  或将其声称为 Teacher 采集样本。新版需要如实绑定补样来源、精确权重和 Adapter，
  再冻结未曝光采集集。
- **采集环境。** Windows CARLA 容器因 OOM 退出。服务器通过 Slurm 单 GPU 隔离
  启动 CARLA 0.9.16，实际 RPC 读到了 Town10HD_Opt，探测进程已退出。
  指定 Teacher 源码提交 `95e97b00` 已在服务器找到，按固定 revision 复算 13 个
  权重及配置文件，模型指纹为 `4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa`，
  与冻结值一致。
  现有 18006 服务报告 Qwen3.5-2B READY，但服务进程当前工作目录的 checkout
  为 `ca353478`，不足以证明运行的是指定 `95e97b00` Teacher adapter 和
  exact model revision。检查到的独立 vLLM 环境为 0.26.0 / Torch 2.11.0，
  与 v4 记录的 0.29.0 / 2.13.0+cu132 不同。没有用它替代固定 Teacher，
  也没有生成正式样本。
- **部署验证。** 本机 Docker 无 OpenExplorer 3.9.1 CPU 镜像，直接查 registry
  超时；仓库记录的公开 registry 预检为 401。须取得官方工具包后，使用同一哈希
  ONNX 运行 `hb_compile --model student_numeric_primary_diagnostic.onnx --march nash-p`，
  再检查算子落点、CPU 回退。未测 J6P、INT8 或正式利用率。

## 可复核产物

- 源码：`replay_numeric_speed_submission.py`，复用已有回放、合同验证和 ONNX CPU 加载。
- 回归结果：`artifacts/numeric_speed_conditioned_20261112/submission_850_fp32_regression.json`。
  SHA256 `036411728daecb99ce2cc100e1372915d136d39c22f2363a6a0adcfeeA9e0f41`。
- 复算模型指纹：`artifacts/numeric_speed_conditioned_20261112/verified_teacher_model_artifact.json`。
- 候选与权重、ONNX 哈希：见 `NUMERIC_SPEED_B2_A4_CHECK_20261112.md`。
  本轮未修改权重、生产配置、阈值和评分代码，未发布正式 Gate 或推送 GitHub。
