# 可提交数据集

本目录只保存能够随源码独立校验的小型数据和 schema，不保存运行时采集目录。

| 目录 | 内容 | 用途边界 |
|---|---|---|
| `language_v1/` | 中文驾驶命令 JSONL | 语言解析回归 |
| `multimodal_v1/` | 多模态 schema、数据卡模板和格式示例 | 只验证格式，不代表真实媒体集 |
| `qwen_proxy_v1/` | 小型 Qwen 动作/目标代理样例 | 接口回归，不代表官方准确率 |
| `repro/` | 10 条冻结延迟输入清单和 10 张内容唯一的 RGB 帧 | 四模态延迟链复现输入 |

语音音频由 `voice_group/test_samples/` 管理；6192 条语言 schema 回归集位于
`CARLA-Language-Benchmark/`。大规模 RGB、点云、运行日志和派生压力集必须生成到
`artifacts/` 或由外部数据存储管理。

可复核命令：

```bash
python -m pytest -q integration/tests/test_qwen_four_modal_stress_set.py
python CARLA_Language_Benchmark/tools/audit_global_benchmark_v1.py \
  CARLA-Language-Benchmark/datasets/final_benchmark/CARLA_language_benchmark_v1_normalized.json \
  --checksum CARLA-Language-Benchmark/baseline/freeze_p0/dataset_checksum.json
```

本地代理集、合成音频和短时诊断均不得表述为官方隐藏集或真实道路成绩。
