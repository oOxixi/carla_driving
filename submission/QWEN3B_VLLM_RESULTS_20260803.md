# Qwen2.5-VL-3B 独立部署与调优结果

日期：2026-08-03  
范围：服务器本地 `carla-driving-3B`，未提交或推送 GitHub。

## 结论

已在 RTX 3090 GPU 0 上建立与 7B、2B 隔离的 Qwen2.5-VL-3B BF16 +
vLLM 路线。固定输入热门禁 P95 为 `127.10 ms`；320 条多图冻结代理集
P95 为 `285.05 ms`，均通过 `300 ms` 模型门槛。

原始 320 条严格契约为 `306/320 = 95.625%`。标签一致性验证确认剩余
14 条全部来自 seed 28/31：语音要求“右侧相邻车道的行人”，但唯一行人
在结构化感知中标为 `far_ahead`。3B 均高置信度输出正确的 `C=SLOW_DOWN`，
严格目标绑定层按安全策略拒绝语义冲突并停车。有效且自洽的 306 条为
`306/306 = 100%`；不得把该有效子集结果写成原始 320 条 100%。

## 固定环境与模型

| 项目 | 值 |
|---|---|
| GPU | NVIDIA GeForce RTX 3090 24GB，GPU 0 |
| 驱动 | 580.173.02 |
| Python | 3.11.15 |
| PyTorch | 2.11.0+cu130 |
| CUDA runtime | 13.0 |
| vLLM | 0.26.0 |
| 模型 | `Qwen/Qwen2.5-VL-3B-Instruct`，BF16 |
| revision | `66285546d2b821cf421d4f5eb2576359d3770cd3` |
| 模型文件总大小 | 7,520,919,614 bytes |
| 聚合清单 SHA-256 | `f95aa375d5f54002e63be13d9641eff7f0c6f0e9a82e9da6010a5acd7f016be3` |
| 服务 | GPU 0，`127.0.0.1:8002`，batch 1，BF16，eager |
| 输出 | `A/B/C/D/E` 单 Token，代码组装严格 Schema |
| 安全阈值 | 0.60，全程未降低 |

权重逐文件哈希见
`artifacts/B_role_validation/qwen25vl_3b_bf16_model_manifest.json`。

## 调优过程

| 版本 | 320条严格契约 | 多图 mean / P95 | 说明 |
|---|---:|---:|---|
| v1 | 42.5% | 279.02 / 372.71 ms | 原始提示词；130条正确C被低置信度闭锁，40条目标缺失确认边界错误 |
| v2 | 未进入320正式复测 | 10条 mean 189.94 / P95 382.07 ms | 过度压缩字段，10条仅1条通过，淘汰 |
| v3 | 95.625% | 272.59 / 359.53 ms | 修复目标缺失确认；末尾复核规则恢复模型置信度 |
| v4 | **95.625%** | **199.54 / 285.05 ms** | 仅裁掉增强、来源和蓝图等非决策字段；准确率不退化且通过延迟门槛 |

v4 的 40 条 `detector_miss` 全部正确执行 `STOP + requires_confirmation=true`。
其余 14 条失败均由标签一致性报告定位为输入语义冲突，不是输出动作错误。

## 最终指标

| 测试 | 样本 | 结果 |
|---|---:|---:|
| 固定图热门禁 | 5次预热 + 20次测量 | mean 115.15 ms，P95 127.10 ms，max 128.53 ms |
| 目标关联小集合 v4 | 10 | 10/10，目标关联100% |
| 冻结多图集合 v4 | 320 | strict parse 100%，原始严格契约95.625%，P95 285.05 ms |
| 标签一致性 | 280个有目标样本 | 266一致、14冲突 |
| 有效自洽样本 | 306 | 306/306，100% |
| 定向代码测试 | 76 | 76 passed |

## 关键证据

- `artifacts/B_role_validation/qwen25vl_3b_bf16_3090_latency_gate_v4.json`
- `artifacts/B_role_validation/qwen25vl_3b_bf16_3090_target10_v4.json`
- `artifacts/B_role_validation/qwen25vl_3b_bf16_3090_frozen320_v4.json`
- `artifacts/B_role_validation/qwen25vl_3b_frozen320_label_integrity.json`
- `artifacts/B_role_validation/qwen25vl_3b_bf16_model_manifest.json`
- `artifacts/B_role_validation/qwen25vl_3b_bf16_vllm_server.log`

## 尚未完成

- 三个 CARLA 正式场景的真实3B闭环重复实跑；
- 语音输入到车辆动作的全链路 P50/P95/P99/max；
- 通过闭环门槛后的30分钟稳定性；
- 在同一硬件、同一有效数据集上与最终2B版本进行正式A/B选择。

启动命令：

```bash
cd /home/tiaozhansai/carla-driving-3B
bash tools/run_qwen25vl_3b_vllm_cu130.sh
```
