# 第二组 Qwen 模型卡（2026-07-31）

## 当前可部署状态

**未达到生产验收。** 当前机器的项目目录中没有 Qwen2.5-VL 权重，因此本次不能
验证许可证文件、权重 SHA-256、量化配置、真实显存或真实推理延迟。服务默认以
`DEGRADED` 启动，标准快路径继续工作，复杂指令 fail-closed。

仓库历史证据记录了另一台机器上的
`/home/tiaozhansai/models/Qwen2.5-VL-7B-Instruct`，但该绝对路径与权重当前均不存在，
不能把历史路径当成本机已安装模型，也不能补写一个未经验证的哈希。

## 候选与历史实测

| 候选 | 本机权重 | 真实正确率证据 | 真实 P95 | 结论 |
|---|---|---:|---:|---|
| Qwen2.5-VL-7B-Instruct | 缺失 | 历史冻结代理集 100%（round 2/3） | 2478.419 ms | 超过 300 ms，不通过 |
| Qwen2.5-VL-3B-Instruct | 缺失 | 无 | 无 | 不得选择 |
| Qwen2.5-VL-7B-AWQ/INT4 | 缺失 | 无 | 无 | 不得选择 |

历史数据集是 CARLA 冻结本地代理集，不是官方隐藏集。详细来源见
`artifacts/qwen_robustness_0728/` 和 `submission/QWEN_ROBUSTNESS_EVIDENCE_20260728.md`。

## 固定部署配置

- 最大输出：48 token；
- 道路 ROI 像素预算：64–256 个 `28×28` patch；
- 并发：1；
- 服务 deadline：300 ms；
- 输出：严格 `DecisionPlan V1`；
- 超时、断开、非法 JSON、目标 ID 不存在：拒绝，不阻塞控制环。

## 完成生产验收前必须补齐

1. 将候选权重放入 `models/`，保存每个权重文件 SHA-256 与许可证原文；
2. 同一固定验证集分别运行 7B、3B、AWQ/INT4，不能只跑选中的候选；
3. 同时比较安全正确率、目标关联、显存、吞吐、mean/P95/P99/max；
4. 只有复杂指令 P95 ≤300 ms 且正确率不退化时才可标记 `production_ready=true`。
