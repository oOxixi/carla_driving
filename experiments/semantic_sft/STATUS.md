# 2026-10-30 准备阶段状态

## 当前结论与本轮进展

仍未开始训练，原驾驶代码/配置、2B服务、7B历史方案和整理后的目录未变。
当前材料：原24条 + negative_v1新增8条，共32条。21条旧样本有用户首轮批准，3条旧契约缺口隔离；
新8条尚未批准。0条最终双人批准，无正式Train/Val；旧批准没有延伸到新批次。

- 本机/服务器准备区各64项软件测试通过。
- 新增`batches/negative_v1/`：8条禁止类候选，4个拟定组，各含2条改写；复用既有CLI，不增加批次框架。
  禁止转弯、禁止跟车、禁止靠边与肯定任务/目标/条件分开；不扩大为禁止变道、普通停车或安全制动。
- 新批与旧24条、旧提示/开发/探针题无规范化文本完全重复；跨批语义近重复仍须人审，缺正式Test排除清单。
- 两端均生成新批待审清单，实际export被拦截，只生成manifest/report，没有train.jsonl/val.jsonl。
  新8条label=null、reviews=[]、DRAFT、UNASSIGNED；原21条首轮批准快照未改，旧3条隔离未放行。
- 服务器真实Qwen3.5模型仅以meta张量构建，所有参数/缓冲均在meta，CUDA未初始化，未读取权重。
- 候选正则与索引一致，实际匹配6个语言attention层、12个Linear；未匹配visual/MTP。
  r=8的A/B矩阵参数估算417792（FP32约1.59MiB）；尚未安装或实际注入PEFT，更不是模型成绩。
- 新增独立改写组覆盖诊断：21条首轮审核标签共11组，禁止类仅`no_left_slow_park_02`这一组。
  同组不能跨Train/Val；新4组尚未人审，不能提前算作已补齐这一缺口。
- 没有拆散同义组、放行隔离样本、伪造复核身份、改保护集或降低工程数据门槛。

本轮证据：`artifacts/semantic_sft/meta_modules_20261030_verified/report.json`、
`artifacts/semantic_sft/group_coverage_20261030/report.json`。原服务和模型仍为固定2B。
新批复核入口：`artifacts/semantic_sft/negative_v1_20261030/draft_review_sheet.md`、
`draft_review_queue.jsonl`；导出拦截：`artifacts/semantic_sft/negative_v1_export_20261030/report.json`。

## 下一步剩余项

1. 数据审核：用户先审核新增8条；另一位真实复核人审核需要保留的全部标签，不能代造身份；修改后需重审。
2. 数据补充：已补禁止类8条候选，需确认语义和跨批分组后再决定采纳，再扩充其余类别；不能只改group_id。
   暂定200 Train/50 Val是本实验工程策略，不是已确认的比赛硬性规定。
3. 数据隔离：负责人提供正式Frozen Test规范化文本哈希排除清单，再冻结独立group split。
4. 训练环境：另建独立环境并验证PEFT注入/冻结；确认不与生产GPU共享后，才实现并运行训练smoke。
5. 契约缺口：013/014/023继续隔离；需要精确区分禁止超车/禁止加速的独立设计，不能误禁所有绕障/调速。

以下为历史快照，旧测试数量和旧缺口不代表当前进度。

## 历史：2026-10-29结构整理（无功能代码改动）

- 用户确认继续使用下划线分支qwen_semantic_adaptation，不另建连字符近似分支。
- 服务器6个历史目录整体归档到`/home/tiaozhansai/carla-archive/20261029-layout/worktrees/`，
  包括dirty scene、旧main验证、两处A3、旧运行包和上次审计；源码/权重/数据完整保留。
- 73个零散文件按传输包、日志和旧启动脚本归档；CARLA仍打开的日志原位保留。
- 67个未跟踪缓存目录在备份核验后删除，约13MB，可恢复或重新生成；没有永久删除历史源码资产。
- main_optimization、旧2B、challenge共3160个受检源码/配置文件的哈希、HEAD与Git状态保持一致。
  8个关键7B历史方案文件额外核验未变；当前仍用2B，未修改profile。
- 服务及CARLA的PID和启动标识不变，8000/18005健康正常；服务器准备区51项测试通过。
- 后续查看SERVER_LAYOUT.md；完整私有证据在归档manifest及本机artifacts/semantic_sft/server_layout_20261029。

## 分支整理与服务器盘点

- 新增BRANCH_MAP.md，统一离线贡献审计、多步理解、数据审核、未来独立adapter的查找入口。
  新增开发只在本分支，原有语义实现已在祖先提交中，不重复cherry-pick、不重写main_optimization。
- 新增SERVER_CODE_INVENTORY.md，按活动依赖、历史工作区、未晋升实验、可归档候选分类。
- 确认端口18005服务从原main_optimization目录启动；新分支未接管服务。
  进程早于磁盘最新提交，未重启，因此不冒称内存中运行的精确SHA就是f92。
- 2B旧目录内的模型/venv和challenge目录内的测试venv仍在使用；旧scene有大量未提交修改。
  没有把这些整个目录判定为可删除，没有实际删除或搬移。

## 历史：2026-10-29首轮人工批准与整批CPU诊断

- 用户在当前对话明确回复“批准，下一步”。以`human_user_current_chat`标识记录一次批准，
  不虚构实名、队友身份或第二位审核；记录时间不是反推的原消息发送时间。
- 21条非隔离样本已填写与该次批准绑定的`label`、源文本/标签哈希和1条审核记录。
  三条契约缺口保持`label=null`、无批准；所有样本仍DRAFT、UNASSIGNED。
- 本机/服务器各51项准备区测试通过；新增审核记录、防覆盖及整批token诊断测试。
- 服务器使用本地固定2B目录的真实tokenizer：21/21长度、前缀、prompt loss屏蔽、assistant结束token
  检查通过，最长358 tokens（候选上限4096）；3条隔离样本跳过。没有加载模型权重或启动训练。
- 审核队列与授权收据：`artifacts/semantic_sft/first_review_20261029/{review_queue.jsonl,report.json}`。
- 本机预检：`artifacts/semantic_sft/first_review_preflight_20261029/report.json`。
- 两端token报告：`artifacts/semantic_sft/first_review_token_audit_20261029/report.json`。
- 整批CPU诊断通过不是正式训练准入、PEFT兼容性验证、模型准确率或闭环成绩。
  仍缺第二位审核、样本规模/独立split、正式保护集哈希、独立训练环境/GPU和Trainer。
- 本机、服务器原main_optimization仍f92ac6fcc，原服务PID 6587/2535027未重启。

## 上一轮：AI待审标签，不是训练

- 已为24条种子编写候选多步标签及逐条复核提示，候选作者明确记为AI_ASSISTANT。
- 真实`label`仍全部为空；0条人工批准，未分配Train/Val，未启动训练。
- 21条进入普通人工复核；013/014/023因“禁止超车/禁止加速”的表达缺口保留隔离。
- 新增`draft`命令及原句/候选哈希绑定；拒绝缺项、多项、重复ID和覆盖既有人工作业。
- 草稿不能替代人工标签；合同缺口即使填入审批，仍被预检和导出拦截。
- 本机、服务器准备区各42项测试通过。单元测试通过不是模型准确率或驾驶闭环通过。
- 人工查看入口：`artifacts/semantic_sft/ai_drafts_20261029_verified/draft_review_sheet.md`；
  可编辑待审队列：同目录`draft_review_queue.jsonl`。
- 两端导出拦截证据：`artifacts/semantic_sft/ai_draft_export_20261029_verified/report.json`；
  24条缺人工标签/批准/划分，3条合同缺口，另外缺样本数量及外部保护集清单；拦截符合预期。
  实际仅产生manifest/report，没有train.jsonl或val.jsonl；命令返回1是预期拦截，不是生成任务失败。
- 服务器额外预检：`artifacts/semantic_sft/ai_draft_preflight_20261029_verified/report.json`。
- 本轮确认原本机/服务器HEAD仍为f92ac6fcc；服务器仅既有outputs/未跟踪。
  原适配器PID 6587、vLLM PID 2535027未重启；两个health均HTTP 200，适配器READY且模型版本未变。

以下保留上一轮环境与原方案回归记录，不把历史检查冒充本轮新运行。

## 原方案保护检查

- 原分支 `main_optimization` 仍在 `f92ac6fcc8e8c55e3b3a63825b6f4386d49b6d78`。
- 原本机工作区没有未提交修改；原服务器工作区仅保留既有 `outputs/`。
- 8000端口vLLM进程和18005端口适配器没有重启；最后检查health为READY，仍为固定版本Qwen3.5-2B。
- 本阶段仅修改新分支的 `experiments/semantic_sft/`，保护检查没有发现目录外变更。
- 没有加载基础模型权重做训练、没有优化器更新、没有合并/替换权重、没有安装训练依赖。

## 历史：2026-10-28首轮准备

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

## 上一轮记录的训练缺口（以页首最新进展为准）

1. 24条记录的`label`仍为空，无真实双人批准。
2. 尚未按同组划分Train/Val，数量也未达到建议的200/50工程data-smoke门槛。
3. 缺少负责人提供的正式Frozen Test规范化文本哈希排除清单。
4. 未创建/冻结独立训练环境，推理环境里缺PEFT、Datasets、Accelerate、TRL等包，不能直接复用安装。
5. 未确认与生产隔离的GPU资源；不允许在原推理服务占用的GPU上启动训练。
6. 尚无完整训练入口、数据级token/mask审计、真实PEFT参数检查与小规模训练smoke。

该历史快照的结论为 **可开始人工标注与复核准备，不可开始正式训练**。
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
