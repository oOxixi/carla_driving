# 独立2B文本LoRA候选训练

负责人已批准本批216条标签及跨批分组，并明确要求重新检查后启动。
本轮使用冻结发布`semantic_text_sft_v1_20261101`：Train206、Val51；3条旧缺口隔离。
不是challenge的Student/A3训练，也不是CARLA闭环或视觉适配，不接管生产服务。

## 启动前硬检查

- 源码必须已提交且工作区干净；相对f92基线的变化只可在本实验目录。
- 发布manifest须与命令行预先固定的SHA256一致；逐文件重算哈希，并复验审批、数量、整组隔离、保护集合。
- train/val聊天记录须逐条等于已审核标签；全量token报告逐条绑定源/标签哈希，prompt loss必须屏蔽。
- 运行时再次对全部257条实际tokenize，禁止静默截断；不读取冻结Test标签。
- 只读基础模型路径固定，检查.model_revision，并重新计算全部artifact文件指纹，与固定2B指纹精确一致。
- 显式指定GPU1–7之一，GPU0永远拒绝；启动检查无compute进程、占用≤1GiB且空闲≥20GiB。
  实验目录内advisory lock防止本实验重复启动；这不是服务器调度器对其他用户的长期预约。
- 原18005服务须READY且仍为固定模型身份；不修改其依赖、端口、模型或运行进程。

## 首轮配置与产物

固定配置：3 epochs、microbatch1、梯度累积4、lr=5e-5、8次更新warmup、之后线性衰减、clip=1、seed=20261101。
206条每轮恰好遍历一次，最后2条按实际数归一化，不丢弃；共156次optimizer更新。
仅语言主干6个全局attention层的q/v LoRA可训练，r8/alpha16/dropout0.05，共417792参数；视觉、MTP和基础权重冻结。
全模型以BF16只读加载，不是4bit训练，不替换或合并原权重。

每轮保存一个独立adapter，以Val的token加权交叉熵选择best；不以Test成绩选模。
训练结束后核对adapter参数实际改变，重新加载best adapter，与保存时的同一输入logit对比，并再次检查生产健康。
`report.json`原子更新当前状态与更新数，`metrics.jsonl`保留逐步loss、梯度范数和学习率；epoch目录只含adapter。
所有输出在新`artifacts/semantic_sft/<run>/`内，不覆盖旧运行；无自动部署、Hub上传或基础权重合并。
当前不提供任意中断点续训；若失败，保留日志及已完成epoch的adapter，定位后另起新run，不自动无限重试。

## 命令

```bash
.venv/bin/python -m experiments.semantic_sft.train \
  --release-dir artifacts/semantic_sft/releases/semantic_text_sft_v1_20261101 \
  --release-manifest-sha256 <已核验的manifest文件SHA256> \
  --token-audit artifacts/semantic_sft/frozen_257_token_audit_20261101/report.json \
  --model-path /home/tiaozhansai/carla-driving-2B/models/Qwen3.5-2B \
  --gpu-index <启动时重新检查为空闲的非0设备> \
  --output-dir artifacts/semantic_sft/<新run>
```

状态COMPLETED表示真实训练、保存重载和健康检查完成，不代表语义正确率或正式Gate。
训练集主要是构造文本，TURN类数量仍少；Val loss下降也可能只是学会格式。
后续需将基座与adapter在相同冻结独立语义评测上比较完整步骤、目标/条件/参数、否定及歧义准确率；
本轮不提前消耗Test用于调参，不把teacher-forced loss包装成闭环能力提升。
