# 本机"教师"服务试跑：路线 A 不成立（B3，2026-10-08）

目标：把 Teacher（Qwen）也在同一台笔记本上跑起来，从而把"教师 vs 学生"的对比从
跨机器（教师行来自 A800 采集运行）升级为同机同条件。**结论：在当前硬件上不可行**，实测证据如下。

## 做了什么

1. 确认本机可用性：RTX 4060 Laptop **8 GB** 显存；WSL2 内 `nvidia-smi` 可见 GPU、`libcuda` 在位；
2. 在 WSL 建 venv 并安装 **torch 2.6.0+cu124（CUDA 可用）+ transformers 5.19 + qwen-vl-utils + jsonschema**；
3. 下载三份权重：`Qwen2.5-VL-3B-Instruct`（7.0 GB，匹配仓库加载器 `Qwen2_5_VLForConditionalGeneration`）、
   `Qwen3-VL-2B-Instruct-GPTQ-Int4`（2.1 GB，匹配循环 profile）、`Qwen3-VL-2B-Instruct`（4.1 GB）；
4. 用仓库自带的 `qwen_service --model-path ... --qwen-mode planner_v2` 起服务 → **READY**，GPU 占用 **6.43 GB**；
5. 用真实 canonical 请求（取自学生轮的逐请求日志）做 4 次冒烟推理。

## 实测结果（不可行的两点）

| 项 | 结果 |
|---|---|
| 单次计划生成延迟 | **58.2 s / 42.3 s / 48.1 s / 47.8 s** |
| 原因 | 3B FP16 权重约 6.2 GB，8 GB 显存下加载器把**部分层 offload 到 CPU**（日志："Some parameters are on the meta device because they were offloaded to the cpu"），每次推理都混合 GPU/CPU |
| 严格解析 | **0 / 4 通过**，错误 `MODEL_OUTPUT_MUST_BE_BARE_JSON_OBJECT` |
| 原因 | 3B FP16 指令模型不能稳定输出严格要求的"裸 JSON"计划（团队自己用的是 **Qwen2.5-VL-7B-AWQ**） |
| 对闭环的影响 | CARLA 循环是 `--realtime`、决策 TTL 12–15 s、每场 35 s → **42–58 s 的计划无法驱动循环** |

顺带记录两个接口事实（对以后同机复现有用）：
1. 服务要求 `rgb_ref` **相对于 image_root**（绝对路径会被拒：`rgb_ref must be relative when image_root is configured`）；
2. 仓库的本地权重加载器**只支持 Qwen2.5-VL 架构**，与循环 profile 里的 Qwen3-VL 不通用（Qwen3 权重会报
   `Qwen3VLVisionConfig ... fullatt_block_indexes`）。

## 这对衰减结论意味着什么

已有的**同口径场景级衰减**（47 个共有场景：教师 macro **92.12%**、学生 macro **74.47%**、相对衰减 **19.16%**）
**继续保留"跨机器"这一注脚**——教师行来自 A800 采集运行。要消掉它，需要下列之一：

- **A2**：换成 4-bit AWQ 权重（团队同款 7B-AWQ 或 3B-AWQ）——依赖 `autoawq/gptqmodel`，与 torch 2.6 的兼容性有风险，且 4-bit 下每请求仍要生成 ~200 token，延迟可能仍在几十秒；
- **B（推荐）**：改走**单 token 约束选择**路径（循环的 `--qwen-remote` A–E / `qwen_service --vllm-base-url`）——只需 1 个 token，已下好的 **2B INT4 可整块放进显存**，延迟约 1 s；代价是它走"选择式"而不是"整份计划 JSON"，与冻结的 `teacher_plan` 生成路径不同，必须在材料里声明；
- **C**：维持现状（跨机器口径），等 A800/vLLM 资源可用时再补同机。

**B3 建议**：若要继续推进同机教师，选 **B**；否则维持 C，并在材料里保留跨机器注脚。
