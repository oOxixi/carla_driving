# 文本排除清单：已完成部分与测试集负责人交接

## 当前真实状态

已核对GitHub challenge提交`2da949be62eccade91e62dc081e5776e652e485a`：

- `challenge/dataset/governance/b1_closeout_v1/independent_validation_v1/`发布了240例冻结的Independent Validation。
- 其README明确写明**不是B1指定的Frozen Test**。现有proxy prospective benchmark仍是WAITING_FOR_FROZEN_CASES，case_manifest_path为空。
- 已从这240例的`model_request.source_text`生成补充排除清单，去重后62个规范化文本哈希。
- 本次29条已审核指令及新增12条草稿，与此清单的完全匹配重合为0；不是语义改写独立性的证明。
- 清单角色是INDEPENDENT_VALIDATION，不能满足正式FROZEN_TEST门槛。代码会拒绝用它冒充Test。

文件在本机及服务器独立工作区：
`artifacts/semantic_sft/known_holdout_exclusions_20261101/exclusion_registry.json`。
旁边report记录来源commit、案例数、唯一文本数及重合编号；不含Test标签或RGB。

## 谁可以提供

用户本人、B2或用户指定的测试集负责人都可以提供并确认真实来源；不要求B2签字，也不是比赛强制角色限制。
此前提到B2仅依据团队分工。关键是集合来源可追溯、角色明确且训练/调参/选模使用历史透明，而不是提供者的称呼。
生成器publisher填写实际提供人或团队，不冒用B2。若尚无测试集，可另建候选集，经负责人确认范围与隔离后冻结。

## 负责人需要补充什么

用户已选择由本项目另建Test候选：当前12条在`artifacts/semantic_sft/test_candidate_v1_20261101/review_sheet.md`。
这些题还未冻结，预期标签需用户审核，且须确认与训练材料的语义模板关系，不能提前签发FROZEN_TEST清单。

请用户本人或指定负责人给出**最终冻结Test**的以下信息：

1. 测试集版本，以及冻结manifest所在仓库的精确40位commit。
2. 每条测试样本真正送入模型的完整`source_text`，不需要Teacher答案、标签或图片。
3. 明确确认它是FROZEN_TEST，而不是Development Val、Independent Validation、Calibration或预留候选池。
4. 原始案例数和冻结清单身份，便于核对是否遗漏。若最终Test尚未建立，应如实说明，不能拿Validation改名。

提供者可以在自己的环境生成哈希，只交付`exclusion_registry.json`与真实发布声明，不交出Test答案。
工具中的publisher字段是来源说明，不是数字签名，也不会凭空认证发布人的身份。
这里指团队可管理的冻结测试集，不是要求获取赛事方尚未公开的隐藏测试。
如果团队根本还没有指定Frozen Test，可由用户或指定负责人建立并冻结它；不能伪造官方隐藏Test文本，也不能仅为过门槛给Validation改名。

## 生成方法

提供者先导出JSONL：每行包含真实`sample_id`和`source_text`。嵌套数据应取真实模型请求的source_text，
不能把场景名称、NLU分类、模板名或Teacher回答当成指令。不要为匹配训练数据而改写测试文本。

在本分支根目录运行，尖括号内容必须替换为实际值，不能复制成假清单：

```bash
python -m experiments.semantic_sft.build_exclusion_registry \
  --input <最终Test指令导出.jsonl> \
  --publisher <真实发布人或团队标识> \
  --test-version <实际冻结Test版本> \
  --source-revision <冻结manifest的40位commit> \
  --role FROZEN_TEST --frozen \
  --output-dir artifacts/semantic_sft/test_exclusion_<新批次>
```

算法固定为：Unicode NFKC → casefold → 删除全部空白 → UTF-8 → SHA256。
工具输出排序去重的text_sha256列表、原始行数、唯一文本数和输入文件SHA256，不输出原句/标签/图片。
输入为空、字段错误、角色或revision不完整会失败，不自动猜字段或签发空清单。

单纯文本哈希不能发现“不要左转”和“别向左拐”这类同义改写。仍要结合B2确认的group_id进行语义近重复审核。

## 收到正式Test清单后

```bash
python -m experiments.semantic_sft.prepare preflight \
  --input artifacts/semantic_sft/split_preview_20261101_verified/split_preview.jsonl \
  --external-protected-registry <负责人确认的FROZEN_TEST清单.json> \
  --supplemental-protected-registry artifacts/semantic_sft/known_holdout_exclusions_20261101/exclusion_registry.json \
  --output-dir artifacts/semantic_sft/formal_preflight_<新批次>
```

两种角色分开校验、合并用于排除；补充Validation清单不会让“正式Test清单缺失”错误消失。
实际重合样本先隔离并审计，不修改Test，也不能给训练句换个ID绕过检查。
规模、来源、审核、分组和mask也必须通过，不能仅凭零重合就启动正式训练。

## 已运行的训练不是正式成绩

GPU1已执行真实Qwen3.5-2B + LoRA的独立合成协议单元训练：2个训练样本、2次更新，1个合成验证样本。
输入是SYNTHETIC_PIPELINE_UNIT标识的JSON单元任务，不是驾驶指令，不使用29条业务样本或任何新草稿。
417792个LoRA参数可训练，24个adapter张量发生更新；保存/重载后logit最大差为0。
这只验证安装、前向、反向、优化器、保存和重载链路，不证明驾驶语义正确率、泛化或正式Gate。

参考实现依据：[PEFT官方快速入门](https://huggingface.co/docs/peft/main/en/quicktour)、
[Qwen3.5官方Transformers文档](https://huggingface.co/docs/transformers/main/en/model_doc/qwen3_5)。
