# 7B首次真实比较与协议控制（2026-11-04）

## 已完成的零约束实验

固定Dev75、相同system/user文本、原生模板、贪心、1536 tokens、BF16/eager、重复惩罚1.0。
2B两组复用并核验V5历史真实输出，7B重新逐条真实推理；不修补答案。

| 指标 | 2B原始 | 2B+V5 | 7B原始 |
| --- | --- | --- | --- |
| JSON合法 | 75/75 | 74/75 | 1/75 |
| schema合法 | 73/75 | 70/75 | 0/75 |
| 原始动作序列正确 | 45/75 | 66/75 | 0/75 |
| 严格整条正确 | 0/75 | 34/75 | 0/75 |

7B输出为75/75完成请求、73/75在EOS内完成。此处0分主要反映协议遵循失败，不能解释为不具备任何语义理解。
原始证据：`artifacts/semantic_sft/seven_b_dev_20261103_02/`；首次分词接口错误在_01保留，0条生成不计入准确率。
后续仅剥离单个围栏的只读诊断发现51条带单围栏，剥离后43条能解析、32条仍失败，
可解析steps反复使用e而不是action，并有嵌套steps、遗漏和错绑；不能仅删除围栏就宣布修复。
剥离诊断不是新主成绩，不重命名e、不补步骤、不修改旧评分。

## 文件和基础运行核验

7B五个权重分片SHA256均与官方revision的LFS记录一致。
tokenizer.json、tokenizer_config.json、vocab.json、merges.txt、chat_template.json、config.json、generation_config.json
这7个文件的Git blob SHA1也分别与官方revision一致，未发现下载损坏或文件混版。
Tokenizer与AutoProcessor渲染模板相同，编解码回环精确；基础英文JSON/算术可生成。
中文JSON探针在eager下出现action→a，SDPA下该探针字段正确，但两者均会添加围栏。
这说明存在协议/数值路径敏感性，不能仅凭几个单元探针认定eager有bug或已证明模型整体正常。
探针不属于Dev/Test业务正确率；原环境未安装/升级依赖，生产未切换。

## 下一阶段：相同语法约束、三组全部重新真实推理

使用已有xgrammar，对所有模型仅约束原TASK_SCHEMA，固定canonical字段顺序，不包含期望动作、正确步数、
原文目标/条件候选或评分标签。不允许把人工答案塞进grammar，也不在生成后修复动作。
系统提示、原始指令、数据、解码参数与主评分不变；新增变量明确为JSON结构约束。
原始2B、2B+V5、7B各重新推理75条，共225条，不复用零约束成绩混作受约束结果。
7B先测，再加载同一2B基座+V5，分别关闭/开启adapter；同一隔离GPU，旧服务不变。

入口：`python -m experiments.semantic_sft.protocol_control --gpu-index 6 --output-dir <新目录>`。
结果仍须看动作、条件、目标、禁止、确认和整条匹配；schema合规不等于语义正确。
本轮只作Dev协议控制，不是独立泛化成绩、闭环证明或正式Gate，不自动部署。

### 运行兼容修复

首批grammar_control_20261104_01发现any_order=True在当前复杂schema上接受重复键/遗漏action。
用实际编译器直接喂非法字符串复现；any_order=False拒绝同一字符串。已中断_01，证据保留且不作准确率结论。
新控制使用any_order=False及与SFT一致的canonical属性顺序；同一schema语义限制不变。
增加真实编译器正反例测试，完成生成若仍违反schema则中止实验，不能继续把故障算成模型答错。
