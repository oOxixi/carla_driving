# 第二组成员 B 交接文档（Qwen 模型与 GPU 部署，2026-08-02）

## 1. 范围与结论

| 项目 | 内容 |
|---|---|
| 角色依据 | 7 月 30 日四人方案中的 B：Qwen 模型与 GPU 部署 |
| 上游基线 | `team/new` / `c95fac6` |
| 正式复现设备 | NVIDIA A800 80GB，主办方答疑为 CUDA 13.2 |
| 正式候选 | `Qwen/Qwen3.5-2B` BF16 + vLLM 0.26.0 |
| 模型 revision | `15852e8c16360a2fea060d615a32b45270f8a8fc` |
| 当前状态 | 实现与复现脚本完成；尚未在 A800 实测，不能标记性能验收通过 |

7 月 24 日旧清单中的 B 是横向控制，当时本成员对应 C；本交接只按 7 月 30 日的新 B 角色说明。

## 2. 本次关键调整

旧路线把重点放在 3B INT4、Marlin 和 Qwen3-VL-2B-FP8。重新按 A800 复现设备检查后，主线改为 BF16：A800 显存足够，FP8 在 Ampere 上不是原生 W8A8 默认路径，量化不应先于真实瓶颈优化。

最大的延迟浪费已经移除：

- 模型不再生成 20～48 Token 的完整 JSON，只在 `A/B/C/D/E` 中输出一个代码。
- vLLM 请求固定 `structured_outputs.choice`、`max_tokens=1`、`temperature=0`、`logprobs=true`、non-thinking。
- logprob 转为模型置信度；低于 0.60 时闭锁为 `STOP + requires_confirmation=true`。
- `target_speed_mps` 从中英文语音数字确定性换算；`target_track_id` 继续只从真实感知目标绑定。
- 红灯、TTC≤2 秒、碰撞和安全模块停车建议会在代码侧覆盖模型。
- 最终输出继续走已有严格 Schema，模型仍不能产生 throttle/brake/steer。

## 3. 视觉与运行配置

远端后端生成固定 256×256 拼图：上半部分保留完整场景，下半部分放最多两个按距离/置信度排序的目标裁剪；没有有效目标框时放道路关注区域。Qwen3.5 的合并视觉单元为 32×32，因此该尺寸对应 64 个视觉 Token。

A800 脚本固定：BF16、单卡、`max_model_len=2048`、`max_num_seqs=1`、prefix cache、最多一张图。脚本会拒绝非 A800、错误 revision、错误 vLLM 版本和无 BF16 支持的环境。

## 4. 核心文件

| 文件 | 作用 |
|---|---|
| `integration/qwen_remote_backend.py` | vLLM 单代码请求、logprob、256×256 场景/目标拼图 |
| `integration/qwen_vl_adapter.py` | typed choice、速度解析、目标绑定、安全覆盖、严格 Schema |
| `integration/carla_runner.py` | Qwen3.5/vLLM 默认模型、端点、1 Token 和 256 尺寸 |
| `tools/run_qwen35_vllm_a800.sh` | A800/vLLM/BF16/revision 预检和服务启动 |
| `tools/run_qwen_latency_gate.py` | 5 次预热、10 次测量、P95 300ms 早停 |
| `requirements-qwen-vllm.txt` | 正式 vLLM 依赖版本 |
| `docs/QWEN_REMOTE_OPENAI_COMPATIBLE.md` | 最短复现步骤 |
| `qwen_service/` | 旧 Transformers/AWQ 兼容服务，不是正式主线 |

## 5. 最短复现步骤

```bash
uv pip install -r requirements-qwen-vllm.txt --torch-backend=auto
hf download Qwen/Qwen3.5-2B \
  --revision 15852e8c16360a2fea060d615a32b45270f8a8fc \
  --local-dir models/Qwen3.5-2B
printf '%s\n' 15852e8c16360a2fea060d615a32b45270f8a8fc \
  > models/Qwen3.5-2B/.model_revision
QWEN_MODEL_PATH=models/Qwen3.5-2B bash tools/run_qwen35_vllm_a800.sh
```

服务 READY 后另一个终端只运行延迟门禁：

```bash
python -m tools.run_qwen_latency_gate \
  --image artifacts/runtime/qwen_test.jpg \
  --output artifacts/B_role_validation/qwen35_a800_latency_gate.json
```

退出码 2 / `EARLY_STOP` 表示 P95 大于 300ms，此时停止，不跑正确率集合。退出码 0 才运行已有冻结正确率集合。

## 6. 本次最小验证

本机只验证代码边界，没有启动 Qwen3.5 真实模型，也没有把 RTX 5070 数据写成 A800 结论：

```text
Qwen3.5 定向套件（adapter/boundary/remote/CARLA helpers/service/gate）：94 passed in 1.44s
WSL bash -n tools/run_qwen35_vllm_a800.sh：passed
python -m tools.run_qwen_latency_gate --help：passed
git diff --check：passed
```

## 7. 历史证据如何处理

- 7B/RTX 3090 的 320 条集合正确率证据仍可作为能力参考，但 P95 2479.581ms，延迟失败。
- 3B-AWQ/RTX 5070 热请求约 1260.042ms，已经早停，不补跑其正确率集合。
- 已下载的 Qwen3-VL-2B-FP8 可保留为兼容回退，不作为 A800 默认模型。
- `qwen_service/model_benchmark.json` 和 `latency_report.json` 是旧模型证据，不代表 Qwen3.5 A800 已验收。

## 8. 剩余唯一性能门槛

1. 在真实 A800 上完成 5 次预热和 10 次测量，保存门禁 JSON。
2. 只有 P95≤300ms 才跑冻结正确率集合；基础要求目标仍为至少 98%。
3. 正确率通过后做一次 30 分钟稳定性测试。
4. 将 A800 的驱动、torch CUDA runtime、vLLM、模型 revision、P50/P95/max 和峰值显存写入最终 metrics，不使用本地 RTX 5070 替代。
