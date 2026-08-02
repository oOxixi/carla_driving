# B 角色 Qwen 模型卡

## 正式复现候选

- 模型：`Qwen/Qwen3.5-2B`
- revision：`15852e8c16360a2fea060d615a32b45270f8a8fc`
- 许可证：Apache-2.0
- 推理：vLLM 0.26.0，BF16，non-thinking，单卡 A800，batch 1
- 输入：固定 256×256 场景/目标拼图，64 个合并视觉 Token
- 输出：`A/B/C/D/E` 五选一，最多 1 Token；最终 Schema 由确定性适配器组装
- 当前状态：代码和复现脚本已完成，尚无 A800 实测延迟/正确率，不能标记验收通过

选择 BF16 是因为 A800 有足够显存，而 FP8 在 Ampere 上不是原生 W8A8 主路径。量化只在 BF16 的 A800 实测仍接近但未达到延迟门槛时做一次对照，不作为默认配置。

## 验收顺序

先执行 5 次预热和 10 次延迟测量。P95 大于 300 ms 时早停；P95 不大于 300 ms 后才运行冻结正确率集合；正确率通过后才运行一次 30 分钟稳定性测试。

## 历史参考与回退

- `Qwen2.5-VL-7B-Instruct` 在 RTX 3090 的 320 条冻结集上联合正确率、目标关联和 fail-closed 均为 100%，但 P95 为 2479.581 ms，延迟失败。
- `Qwen2.5-VL-3B-Instruct-AWQ` 在 RTX 5070/WSL2 可运行，热请求约 1260.042 ms，延迟失败；未运行其冻结正确率集合。
- `Qwen3-VL-2B-Instruct-FP8` 权重只作为兼容性回退，不是 A800 主线。

旧数据保留在 `qwen_service/model_benchmark.json`、`qwen_service/latency_report.json` 和 `artifacts/B_role_validation/`，不得覆盖新的 A800 门禁结论。
