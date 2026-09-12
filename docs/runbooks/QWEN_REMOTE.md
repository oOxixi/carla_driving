# 正式 Qwen 2B 远程服务

## 唯一正式模型

正式 CARLA 闭环统一使用：

| 字段 | 固定值 |
|---|---|
| profile | qwen3.5-2b |
| Hugging Face model | Qwen/Qwen3.5-2B |
| exact revision | 15852e8c16360a2fea060d615a32b45270f8a8fc |
| 已核验 artifact SHA-256 | 4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa |
| Qwen 协议 | planner_v2 / ManeuverPlan V2 |
| 视觉输入 | 224 x 224，64 visual tokens |

旧的 Qwen3-VL GPTQ INT4 与 FP8 配置只保留为 RTX 5070 历史诊断基线，
不得用于新的正式场景证据，也不得与上表模型的成绩合并。

## 启动顺序

先以固定 revision 启动 vLLM，并确认服务器上的模型 artifact 指纹与上表一致。
随后启动仓库的严格 Planner V2 服务：

```bash
export QWEN_MODEL_REVISION=15852e8c16360a2fea060d615a32b45270f8a8fc
export QWEN_MODEL_ARTIFACT_SHA256=4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa

python -m qwen_service.server \
  --host 127.0.0.1 \
  --port 18000 \
  --vllm-base-url http://127.0.0.1:8000/v1 \
  --vllm-model Qwen/Qwen3.5-2B \
  --qwen-mode planner_v2 \
  --image-max-side 224
```

生产模型若未显式提供正确 revision 和 artifact 指纹，服务会拒绝启动。健康接口
同时返回 model、revision、artifact、模式和 production-ready 状态，正式脚本会逐项
核对，不再只检查“端口能连通”或名称中是否包含 2B。

## 严格预检

```bash
python -m runtime.healthcheck \
  --qwen-url http://127.0.0.1:18000 \
  --carla-host 127.0.0.1 \
  --carla-port 2000 \
  --require-qwen \
  --require-carla \
  --output artifacts/review/live_health.json
```

完整的静态加在线验收可运行：

```bash
python tools/validate_judge_readiness.py --require-live
```

## 决策边界

- 每条有效语音事件都经过 Qwen；不存在本地意图快路径。
- Qwen 只生成高层 ManeuverPlan，不允许输出 throttle、brake、steer。
- 显式语音目标在视觉拼图中优先，随后才按距离和置信度选择关注目标。
- token 与 logprob 必须对应；无法对应时失败关闭，不借用其他 token 的置信度。
- 目标缺失、目标歧义、响应非法、超时或低置信度均失败关闭。
- 最终低层控制仍只由 A/B/C/D 控制链和 SafetySupervisor 产生。

## 历史 RTX 5070 资料

`metrics/reference_5070/`、`README_REPRO.md` 和
`tools/run_qwen3vl_2b_vllm_cu132.sh` 是旧 GPTQ/FP8 诊断包。它们用于解释历史原始
记录，不代表当前 Qwen3.5-2B 的正式准确率、CARLA 完成率或 A800 结果。
