# CARLA-Language-Benchmark v1

这是冻结的语言指令结构回归集，共 6192 条。它用于检查指令 schema、动作本体、
ID 唯一性和数据校验和，不单独构成比赛正式准确率结果。

正式准确率必须使用 `metric_policy.json` 指向的 ASR 与多模态冻结验证材料；这些
材料未冻结前，禁止依据本目录报告准确率。

## 内容

- `datasets/final_benchmark/`：6192 条规范化语言指令。
- `baseline/freeze_p0/dataset_checksum.json`：冻结数据的记录数与 SHA256。
- `baseline/freeze_p0/metric_policy.json`：可报告指标的边界。
- `tools/`：合并、规范化和审计脚本。

## 使用

```python
import json

with open(
    "datasets/final_benchmark/CARLA_language_benchmark_v1_normalized.json",
    encoding="utf-8"
) as f:
    data = json.load(f)

print(data[0]["template"])
print(data[0]["expected_action"])
```

运行审计：

```bash
python CARLA_Language_Benchmark/tools/audit_global_benchmark_v1.py \
  CARLA-Language-Benchmark/datasets/final_benchmark/CARLA_language_benchmark_v1_normalized.json
```
