# V5：仅动作加权的受控开发对照

V4已经完成192次更新和300次Dev生成；动作63/75，完整语义33/75，
仍有3条基座正确动作退化，重载通过但没有晋升候选，不接管生产。
V3相应为60/75、35/75、4条退化。V4比V3新增完整正确5条、丢失7条。

共同55条动作正确且schema合法的Dev中，V4方向错误10→7条，但条件错误13→19条。
步骤级条件误填由3→16处，漏填11→10处。这支持排查非空条件加权偏置，
但V4联合改变多个字段，不能据此认定单一因果。

## 本轮固定项

使用同一个已批准V3数据发布，Train254/Dev75、329条，原3条缺口继续隔离。
manifest SHA256：`59e8913f1a6e7d108c53547e324525eb51325673bb78fa0cef33a5245295f1d8`。
prompt SHA256：`a8a8e68c0d7ed0d37123e89ab026583a21974fae071814ae5cbc4c14b267268a`。
仍为固定Qwen3.5-2B、语言q/v LoRA r8、417792参数、3 epochs、lr5e-5、累计4、192更新，
同样的Train组平衡、梯度检查点、生成、评分和基座逐条不退化门槛，不读新Final Test。

仅增加显式参数`--action-field-loss`：action值token权重4，条件、方向、禁止、null、证据、
JSON语法与EOS均为1，prompt为0。与`--semantic-field-loss`互斥，旧V4默认策略保留可复现。
字段边界、归一化和assistant尾部logits计算沿用V4；不是新加推理规则或关键词动作分类。
比较对象为V3普通loss和V4联合字段loss，训练loss定义不同，不能直接比较数值大小；
验证loss仍为原未加权token CE。结果仍须看配对动作/整条语义/退化案例，拒绝只看总分晋升。

运行目录：`artifacts/semantic_sft/semantic_text_lora_v5_20261102_01/`，不覆盖V1–V4。
先完成真实Train254条动作-only token掩码预检及两端测试，再固定源码并检查GPU6空闲、生产READY。
源码和数据实际启动身份在私有launch/job.json中留档，准备文档不是训练完成或性能证明。

## 同时准备但不入本轮训练的材料

生成器：`experiments.semantic_sft.batches.boundaries_v2.build`。
9条AI构造开发草稿、4个待复核组：

- 静止目标由本车通过 / 让移动目标先通过。
- 就地停车 / 靠边停车。
- 各步方向独立、保留最后保持车道任务。
- 无条件 / 共享条件 / 不同步骤独立条件。

本机审核入口：`artifacts/semantic_sft/boundaries_v2_20261102/REVIEW.md`。
`near_neighbors.json`列出旧Train/Dev最近文本及组，精确排除通过不代表近义组已独立。
全部保持DRAFT、label=null、reviews=[]、UNASSIGNED，不是新的独立Test，也不是正式Teacher数据。
必须由负责人审核标签及跨批分组；若与旧Dev同组，应保留开发/回归角色，不能以批准为由搬入Train。
未批准、未并入冻结发布、未改变本轮数据哈希。

效果和新Final Test尚未验证，不部署、不签正式Gate；所有修改限实验目录，生产与7B历史保留。
