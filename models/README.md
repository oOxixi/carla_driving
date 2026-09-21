# 本地模型目录

`models/` 只用于放置本机或服务器下载的大模型文件。除本说明外，该目录已被
`.gitignore` 排除，不能把权重、Hugging Face 缓存、checkpoint 或临时转换产物提交到
GitHub。

模型与权重的完整生命周期、身份字段和晋级门禁见
[`docs/architecture/modules/MODEL_AND_WEIGHT_LIFECYCLE.md`](../docs/architecture/modules/MODEL_AND_WEIGHT_LIFECYCLE.md)。

## 当前正式模型角色

| 角色 | 固定身份 | 当前状态 |
|---|---|---|
| B1 Teacher | `Qwen/Qwen3.5-2B` @ `15852e8c16360a2fea060d615a32b45270f8a8fc` | 模型 artifact 已固定；B2 Benchmark 仍待完成 |
| A1 Student 结构 | `student-v0-r3-fp32` / `student-v0-r3-structure-20260911` | 结构与随机初始化 ONNX 已就绪 |
| A3 Student FP32 权重 | 与 A1 相同 `model_id/config_id` | 只有候选基线，尚无正式 Gate 通过清单 |
| A2 INT8 | 必须从 Gate 通过的 FP32 权重派生 | 尚未交付 |
| A4/J6P Runtime | 必须绑定 INT8/FP32 产物身份和 Runtime SHA | 尚未完成正式板端交付 |

Teacher 的权威身份在：

- `challenge/teacher_baseline_manifest.json`
- `challenge/teacher_pinned_manifest.json`
- `challenge/teacher_pinned_manifest_v4.json`

Student 的权威结构在：

- `challenge/student_config.json`
- `challenge/model_structure.json`
- `challenge/flops_report.json`
- `challenge/A1_MODEL_INTERFACE.md`

## 本地放置约定

下面只是便于运维的推荐布局，代码不依赖文件夹名称，正式运行必须显式传入路径：

```text
models/
├── teacher/
│   └── Qwen3.5-2B/
│       └── 15852e8c16360a2fea060d615a32b45270f8a8fc/
└── student/
    ├── fp32/
    └── int8/
```

Teacher 下载目录必须保留原始配置、tokenizer、权重分片和 Hugging Face revision 信息。
不要把不同 revision 的文件覆盖到同一目录，也不要用文件夹名代替 manifest 核验。

训练生成的 checkpoint、候选权重和报告写入 `artifacts/`，不是 `models/`。只有完成审核后
才可将待部署权重复制到受控的服务器模型目录；复制后必须重新核验 SHA256。

## Teacher 指纹核验

```bash
python -m challenge.dataset.teacher_model_fingerprint \
  --model-dir /absolute/path/to/Qwen3.5-2B \
  --model-id Qwen/Qwen3.5-2B \
  --revision 15852e8c16360a2fea060d615a32b45270f8a8fc \
  --output artifacts/b1_teacher_pinned/teacher_model_manifest.json
```

正式 Teacher artifact fingerprint 必须为：

```text
4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa
```

模型 ID、revision 和 fingerprint 任一不一致都必须停止采集或训练，不能通过改文档消除。

## Student 权重使用规则

仓库中的 `challenge/student_v0_fp32.onnx` 是固定 seed 的随机初始化结构冒烟产物，只能
验证 ONNX、算子、Shape 和运行时工具链。它不代表 A3 训练结果，也不能用于准确率、闭环
能力或性能申报。

真实 Student 后端只有同时收到以下两项才可能 production-ready：

1. 纯 `state_dict` FP32 权重；
2. 与权重 SHA256、`model_id`、`config_id`、Git SHA、数据版本一致，且
   `gate_status=A3_FP32_GATE_PASSED` 的权重 manifest。

只提供权重而没有 Gate 清单时，`StudentBackend` 可以加载文件用于诊断，但健康检查必须
返回未就绪。仓库当前没有真实的 Gate 通过权重或清单。

## 旧模型路线边界

`tools/run_qwen3vl_2b_vllm_cu132.sh`、`tools/run_qwen_latency_gate.py` 和旧复现脚本中的
Qwen3-VL-2B GPTQ/FP8 配置属于基础赛道历史诊断路线，不是挑战赛道 B1 Teacher 身份。
挑战赛道数据采集、蒸馏和模型证据统一使用上面固定的 `Qwen/Qwen3.5-2B`，不得混用旧
模型 ID、revision 或延迟数字。

## 禁止事项

- 禁止提交大型模型、训练 checkpoint 或 Hugging Face 缓存。
- 禁止用 `Qwen-2B`、`2B` 等简称代替正式模型身份。
- 禁止把随机初始化 ONNX 表述成已训练 Student。
- 禁止没有 manifest 就将权重标记为 production-ready。
- 禁止从 Reserved/Frozen Test 选权重或调参。
- 禁止用 A3 Gate 替代 B2 独立准确率评测或 B3/A4 板端验收。

