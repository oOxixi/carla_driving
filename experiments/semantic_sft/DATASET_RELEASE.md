# 内部语义SFT首版冻结发布

版本：`semantic_text_sft_v1_20261101`。这是Qwen语义适配的文本监督，不是B1 Teacher多模态数据、
CARLA闭环成绩或challenge Student/A3权重。语料来自构造文本与负责人审核，不能当作真实路况分布。

## 已冻结内容

| 项目 | 实际结果 |
| --- | --- |
| 标签批准 | 原41条保留；新增216条由负责人在明确范围确认后批准，共257条 |
| Train / Val | 206 / 51；两侧覆盖6类及14种动作；未用模型成绩选择分组 |
| 分组 | 保留旧集合；新批按已确认计划整组分配，Train/Val组交集0 |
| 隔离 | 3条旧契约缺口原字节保留，不进入训练或验证 |
| Test | 内部语义Test 12条独立冻结，Train/Val文本与组ID无交集；不导入其标签 |
| 补充排除 | 已知240例Independent Validation的62个唯一文本哈希，完全匹配重合0 |
| 全量token检查 | 257/257通过，最长374 tokens，prompt loss屏蔽、assistant结束token正常，无截断 |

语义分组由负责人确认，工具只验证ID、哈希和结构，不能机器证明近义独立。
TURN_LEFT/TURN_RIGHT的Train各只有5个动作实例、Val各3个，仍属弱覆盖；不能因总数量够而预先宣称效果好。

## 文件与审计证据

以下路径均相对独立实验仓库根目录；本机及tiaozhansai均保留同一发布包。

`artifacts/semantic_sft/releases/semantic_text_sft_v1_20261101/`

- `reviewed_rows.jsonl`：257条标签、审核记录、分组及冻结集合。
- `train.jsonl`、`val.jsonl`：仅system/user/assistant聊天监督及必要样本ID；只有assistant参与loss，无图像。
- `quarantine.jsonl`：原3条未批准隔离材料，字节不变。
- `approval_receipt.json`：新216条的真实确认范围、原答复、登记时间、逐条源/标签哈希；不是数字签名。
- `test_exclusion_registry.json`、`supplemental_exclusion_registry.json`：实际不同角色的保护清单。
- `manifest.json`、`report.json`：输入和交付文件SHA256、静态审计、模型版本与未训练声明。

Train SHA256：`537b52976d435d53d732a9b6581641b86327f05eea6eb958370db9ebae5e43df`。
Val SHA256：`ff59bc2f852892bd54d1c34a7ecbeffd001e96d5e6042e0de641252da497ee06`。

全量token诊断：`artifacts/semantic_sft/frozen_257_token_audit_20261101/report.json`，input SHA绑定本发布的reviewed_rows。
服务器复验：`artifacts/semantic_sft/frozen_257_preflight_20261101/`。原草稿、旧41条快照及Test文件没有覆盖。
真实审批及完整语料保留在私有artifact，不随源码直接上传GitHub。

## 复现发布

先有真实负责人批准记录，不能由此命令生成审批：

```bash
python -m experiments.semantic_sft.release \
  --previous artifacts/semantic_sft/approved_cumulative_20261101/split_preview.jsonl \
  --approved-batch artifacts/semantic_sft/expansion_v2_approved_20261101/review_queue.jsonl \
  --planned-groups artifacts/semantic_sft/expansion_v2_20261101_review03/planned_groups.json \
  --quarantine artifacts/semantic_sft/approved_cumulative_20261101/quarantine.jsonl \
  --approval-receipt artifacts/semantic_sft/expansion_v2_approved_20261101/report.json \
  --test-registry artifacts/semantic_sft/frozen_test_v1_20261101/exclusion_registry.json \
  --supplemental-registry artifacts/semantic_sft/known_holdout_exclusions_20261101/exclusion_registry.json \
  --dataset-version semantic_text_sft_v1_20261101 \
  --output-dir artifacts/semantic_sft/releases/<新复现目录>
```

审核、数量、同组隔离或来源预检失败会在创建发布目录前拒绝，不静默丢弃问题样本，不改旧集合凑门槛。
发布目录不可覆盖；若数据变更，需重新审核并新立版本，不按Val/Test结果修改旧冻结版本。

## 还不能宣称什么

当前data_ready_for_tokenization=true，业务训练尚未开始，ready_for_training仍为false。
仍缺业务训练入口、完整训练与保存重载验证及独立语义性能评测。
原先选定的物理GPU1在本轮检查已被其他任务占用；不与其共享、不停止其他进程，启动前重新检查资源。
已有合成协议smoke只证明训练链能运行，不是本发布上的效果成绩。生产服务、基础权重与7B历史方案不变。
