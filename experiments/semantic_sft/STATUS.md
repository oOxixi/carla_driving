# 2026-10-28 准备阶段状态

## 原方案保护检查

- 原分支 `main_optimization` 仍在 `f92ac6fcc8e8c55e3b3a63825b6f4386d49b6d78`。
- 原本机工作区没有未提交修改；原服务器工作区仅保留既有 `outputs/`。
- 8000端口vLLM进程和18005端口适配器没有重启；最后检查health为READY，仍为固定版本Qwen3.5-2B。
- 本阶段仅修改新分支的 `experiments/semantic_sft/`，保护检查没有发现目录外变更。
- 没有加载基础模型权重做训练、没有优化器更新、没有合并/替换权重、没有安装训练依赖。

## 已完成

- 独立本机、服务器工作目录和 `qwen_semantic_adaptation` 分支。
- 24条新编写的DRAFT指令，6个语义类别、12个同组改写组；0条已批准标签。
- 标注说明、严格数据格式、源文本与标签版本绑定的双人复核记录。
- 旧开发/复核/提示材料排除、同组跨split检查、规范化重复检查、外部Test哈希排除接口。
- 受限SFT聊天数据导出；数据预检失败时不生成train/val文件。
- 固定2B版本与只输出独立adapter的候选配置；不允许配置成基础权重合并或共享生产GPU。
- 新增准备测试：本机28项通过，服务器28项通过。
- 在新工作区运行原软件回归：1385项通过、4项跳过；不是新的驾驶或模型成绩。
- 只读检查找到12个候选语言主干q/v模块，未包含visual或MTP；尚未实例化PEFT模型验证。
- CPU tokenizer单元小测试通过：152个prompt token全部屏蔽loss，7个assistant token含结束token。
  这是单元样例，不是已完成真实训练数据mask审计。

## 当前不能开始训练的原因

1. 24条记录的`label`仍为空，无真实双人批准。
2. 尚未按同组划分Train/Val，数量也未达到建议的200/50工程data-smoke门槛。
3. 缺少负责人提供的正式Frozen Test规范化文本哈希排除清单。
4. 未创建/冻结独立训练环境，推理环境里缺PEFT、Datasets、Accelerate、TRL等包，不能直接复用安装。
5. 未确认与生产隔离的GPU资源；不允许在原推理服务占用的GPU上启动训练。
6. 尚无完整训练入口、数据级token/mask审计、真实PEFT参数检查与小规模训练smoke。

因此当前状态是 **可开始人工标注与复核准备，不可开始正式训练**。
没有 `student_fp32`、Qwen新权重、LoRA成品或任何正式Gate结论。

## 人工入口与证据

本机人工清单：
`artifacts/semantic_sft/review_20261028_final/review_sheet.md`。

对应待填写记录：
`artifacts/semantic_sft/review_20261028_final/review_queue.jsonl`。

本机预检：
`artifacts/semantic_sft/preflight_20261028_final/report.json`。

服务器对应文件位于独立目录下相同的相对路径；环境检查位于
`artifacts/semantic_sft/environment_20261028_final/report.json`。
这些报告、源数据队列和未来权重均保留在私有artifact中，不直接提交GitHub。

下一步先由真实复核人完成首批标签与分歧处理。扩充新材料时保持旧测试隔离；
确认训练数据、环境与资源后再决定训练，不动原生产服务。
