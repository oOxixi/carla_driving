# 7B与2B真实语义对照（2026-11-03）

用户明确要求忽略延迟、真实测试7B。不切线上服务，不重训，不合并adapter，不改7B旧代码。
本轮为纯文本已知Dev比较，不是RGB能力、真实路况决策、闭环或独立Final Test成绩。

## 模型与对照

- 当前2B：Qwen/Qwen3.5-2B，revision 15852e8c16360a2fea060d615a32b45270f8a8fc。
- 微调对照：同一2B加V5第3轮LoRA，原角色仍为拒绝晋升的诊断权重，不因本次比较升级。
- 7B：Qwen/Qwen2.5-VL-7B-Instruct，官方API核验revision cc594898137f460bfe9f0759e9844b3ce807cfb5。

这是不同代模型的任务表现比较，不是严格隔离参数量的消融。
服务器直连官方站超时，固定上述官方revision通过hf-mirror.com下载；镜像只是传输路径，
不把文件指纹冒称官方数字签名。完整本地artifact指纹和各文件哈希另记入报告，使用BF16原始权重而非量化版。
7B新权重只放实验artifacts/models目录，旧2B模型/环境和7B历史源码不移动、不删除。

## 固定评测协议

使用同一semantic_text_sft_v3_20261102的75条Dev；原Train、标签和Test保护集不改。
相同system及user文本、无few-shot或标签输入、各自原生chat template、2B关闭thinking，7B无另加思考模式。
不同模型分词和模板天然不同，不声称输入token ID相同。
贪心、num_beams=1、max_new_tokens=1536、repetition_penalty=1.0、无grammar、无重试、无答案修补、eager attention、BF16。
7B原配置重复惩罚为1.05，本实验明确覆盖为1.0；重新核对2B原始配置为默认1.0，避免解码参数混杂。
评分仍为原score_text，逐条保留原始输出、EOS完整性、提示哈希、标签哈希、分项和严格整条正确率。

2B的两个arm复用V5已完成的真实生成：首先核对数据manifest、75条唯一ID、当前原始输出重评分、
以及实际2B tokenizer生成的每条prompt token哈希。复用与文件哈希写入报告，不冒充本次重跑。
7B的所有75条重新真实推理；无模拟替代。比较整条语义、原始动作序列、条件、方向、禁止、确认及逐条退化。
最终结论必须等75条结束；软件测试、下载或模型加载完成均不是准确率结果。

## 入口与保护

`python -m experiments.semantic_sft.compare_7b`；参数包括model-manifest、reference-run-dir、release-dir、token-audit、gpu-index、output-dir。
原生产GPU0禁止；使用启动时复验空闲的GPU6和实验venv，不启动或重配生产vLLM。
如果单卡BF16因显存不足失败，保留错误证据，不能暗中切成量化或更改协议后混报。
模型下载清单、启动记录、日志和逐条结果位于artifacts/semantic_sft/seven_b_comparison_20261103及新输出目录。
V6训练继续保持未启动。
