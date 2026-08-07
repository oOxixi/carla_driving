# CARLA 语音多模态作品独立复现包设计

日期：2026-08-04
目标分支：`carla_driving_rstar`
参考更新：`team/8.4-xky-3B` / `94eea04`

## 1. 目标

在本机 RTX 5070 8GB 上完成可运行、可记录、可打包的完整链路：

```text
固定音频或实时语音
  -> ASR/NLU
  -> RGB/LiDAR/车辆状态/环境状态
  -> Qwen 高层决策
  -> 目标绑定与安全仲裁
  -> CARLA 车辆控制
  -> 指标、逐帧日志和演示证据
```

最终产物必须能迁移到 A800 80GB / CUDA 13.2 环境，在不修改代码、不源码编译、不重新下载主模型、不修正路径的前提下，立即完成环境预检、服务启动、延迟门禁、正确率测试、CARLA 闭环测试和稳定性测试。

RTX 5070 用于证明链路和作品包可复现；A800 用于产生正式性能结论。RTX 5070 数据不得写成 A800 验收结果。

## 2. 成功标准

### 2.1 RTX 5070 开发验收

- `image.tar` 可在清理宿主机 Python、venv 和模型路径依赖后加载。
- 一个入口脚本能启动 CARLA、控制器和 Qwen 服务。
- 固定 WAV 能贯通 ASR、四模态决策、安全控制和 CARLA Actor。
- 基础操控、复杂避障、应急响应至少各有一个物理闭环场景。
- 所有运行生成统一 run ID、环境清单、分阶段延迟、逐帧日志、场景摘要和失败原因。
- 6192 条语言基准能够完成 Schema/标签审计；正式准确率只使用冻结验证集。
- Notebook、README、PDF 和演示视频引用同一 Git commit、镜像 digest 和模型 revision。

本机不要求把 A800 的正式延迟门槛作为打包阻塞条件，但必须完整暴露真实结果，不得用固定图片热门禁代替动态闭环延迟。

### 2.2 A800 正式复现验收

在已安装 Docker 和 NVIDIA Container Toolkit 的 Linux 主机执行：

```bash
docker load -i image.tar
./run.sh preflight --profile a800
./run.sh evaluate --profile a800
```

复现过程不得访问开发机路径，不得依赖本机 Hugging Face 缓存。输出至少包括：

- 指令解析延迟，目标 `P95 <= 50 ms`；
- 完整端到端延迟，目标 `P95 <= 150 ms`；
- 语音指令语义理解准确率，目标 `>= 95%`；
- 多模态语义—动作完整契约准确率，目标 `>= 98%`；
- 三类场景任务完成率，目标 `>= 90%`；
- 指标接近门槛后运行的 30 分钟稳定性结果。

`P95 > 300 ms` 是内部节省测试时间的早停线，不是正式通过线。正式满分线始终是端到端 `P95 <= 150 ms`。

## 3. 作品包结构

```text
作品名称-学校/
├─ image.tar
├─ docker-compose.yml
├─ run.sh
├─ stop.sh
├─ README.md
├─ config/
│  ├─ common.env
│  ├─ rtx5070.env
│  └─ a800.env
├─ weights/
│  ├─ model_manifest.json
│  ├─ SHA256SUMS
│  └─ download_fallback.sh
├─ datasets/
│  ├─ frozen_validation/
│  └─ CARLA-Language-Benchmark/
├─ scenarios/
│  ├─ basic/
│  ├─ obstacle/
│  └─ emergency/
├─ samples/
│  ├─ audio/
│  └─ commands.jsonl
├─ notebooks/
│  └─ reproduce.ipynb
├─ metrics/
│  ├─ README.md
│  └─ reference_5070/
├─ docs/
│  └─ 技术方案.pdf
└─ demo/
   └─ carla_closed_loop.mp4
```

`image.tar` 是一个 Docker archive，可以同时保存多个镜像；用户只需执行一次 `docker load`。

## 4. 镜像边界

### 4.1 `carla-simulator:0.9.16`

- 固定 CARLA 0.9.16 和所需地图。
- 以无界面/offscreen 方式运行。
- 对 Docker 内部网络暴露 CARLA RPC 和流式端口。
- 不包含控制器、Qwen 或比赛指标逻辑。

### 4.2 `carla-controller:<git-commit>`

- 包含 ASR/NLU、传感器桥、ScenarioRunner Agent、车辆状态、目标绑定、A/B/C/D 控制与安全仲裁。
- 包含冻结场景、语言基准审计和指标聚合工具。
- 只通过 OpenAI-compatible API 调用 Qwen，不包含模型权重和 vLLM。
- 统一写入挂载的 `/output/runs/<run_id>/`。

### 4.3 `qwen-vllm-cu132:<model-profile>`

- 固定 CUDA 13.2 用户态、PyTorch、vLLM 和模型 revision。
- 默认镜像内置 2B INT4 主模型权重，不依赖现场网络。
- 启动时校验模型配置、revision、逐文件 SHA256 和实际量化内核。
- 只提供健康检查和 OpenAI-compatible `/v1` 服务。

三个镜像通过 Docker Compose 内部网络通信。容器不能挂载开发机 venv、Hugging Face 缓存或 `F:\carla_driving_rstar` 绝对路径。

## 5. 模型配置

| profile | 用途 | 默认性 | 环境 |
|---|---|---|---|
| `qwen3vl-2b-int4` | 2B GPTQ INT4/Marlin 主路线 | 默认 | RTX 5070、A800 |
| `qwen3vl-2b-fp8` | Qwen 官方权重对照 | 可选 | A800 实测决定是否保留性能路线 |
| `qwen25vl-3b-bf16` | `8.4-xky-3B` 能力对照 | 可选 | A800/大显存 GPU，不用于 5070 默认包 |

主包只内置 `qwen3vl-2b-int4` 权重。FP8 和 3B 使用固定 revision、清单和下载脚本；若提交包容量允许，可额外归档为可选镜像，但不能增大默认启动复杂度。

所有报告必须记录实际模型、revision、量化方法、注意力后端、CUDA Graph 模式和实际启用的线性内核。配置名称不能替代运行日志证据。

## 6. `8.4-xky-3B` 选择性整合

### 6.1 纳入

- `integration/scenario_runner_agent.py`：官方 ScenarioRunner `--agent` 接口。
- `integration/carla_runner.py` 中基于场景内容和 expected contract 推断行为的通用化逻辑。
- `tools/run_four_modal_full_chain.py` 的分阶段计时和远端 OpenAI-compatible 后端。
- P50/P95/P99/max 指标及统一完整契约统计。
- `CARLA-Language-Benchmark` 的 6192 条语言样本、冻结协议和审计工具。
- 目标标签一致性修复方法、修复来源记录和不可删除失败样本规则。
- ScenarioRunner 未知场景 ID、目标缺失、安全冲突和数据修复回归测试。

### 6.2 不直接纳入

- 不把默认模型改回 Qwen2.5-VL-3B。
- 不把默认服务端口改为 8002；容器内部端点通过服务名和环境变量配置。
- 不使用 CUDA 13.0 的 3B 启动脚本作为正式 A800 启动入口。
- 不提交只有报告结论、没有原始 JSON/日志的 3B 性能证据。
- 不把离线 320 条回放描述为物理 CARLA 闭环。
- 不把合成 TTS 音频描述为真人方言或 50 dB 噪声证据。

### 6.3 共享代码冲突处理

共享模块不得硬编码某个模型的默认值。模型名、revision、端口和后端参数从 profile 注入。

3B 分支对提示词的字段裁剪、目标缺失确认和末尾复核规则，需要分别在 2B INT4、2B FP8 的同一冻结集上回归。只有准确率不下降且延迟不恶化的模型无关改动才能进入共享默认提示词；其余内容放入模型专用 prompt profile。

## 7. 一键入口

```bash
./run.sh preflight --profile rtx5070
./run.sh smoke --profile rtx5070
./run.sh evaluate --profile rtx5070
./run.sh demo --profile rtx5070
./run.sh stability --profile rtx5070
./stop.sh
```

入口脚本负责：

1. 校验 Docker、NVIDIA runtime、GPU、驱动、磁盘和镜像 digest；
2. 校验权重 manifest、revision 和 SHA256；
3. 创建唯一 run ID 和输出目录；
4. 启动 Qwen、CARLA、控制器并等待健康检查；
5. 执行指定模式；
6. 无论成功或失败都写入最终状态、退出阶段和错误原因；
7. 正常停止容器，不删除原始日志。

`smoke` 只跑一条固定音频和一个最短 CARLA 场景。`evaluate` 先运行延迟门禁，再运行冻结正确率与三类场景。`stability` 不会由 `evaluate` 自动触发，只有指标接近正式门槛后才由操作者显式执行。

## 8. 数据与指标

### 8.1 冻结数据

- 6192 条语言基准用于语言覆盖和 Schema 审计，不直接等同于 6192 个物理 CARLA 场景。
- 正式模型 A/B 比较必须使用相同 validation split、seed、指标、延迟定义和证据格式。
- 不允许删除失败样本、修改期望动作或在看到结果后调整计分口径。
- 小类别如否定、单位转换必须在冻结前补足或单独报告置信区间，不能由大类样本数量掩盖。

### 8.2 每次运行输出

```text
/output/runs/<run_id>/
├─ run_manifest.json
├─ environment.json
├─ model_manifest.json
├─ metrics/
│  ├─ asr_semantic_accuracy.json
│  ├─ multimodal_contract_accuracy.json
│  ├─ service_latency.json
│  ├─ end_to_end_latency.json
│  ├─ scenario_completion.json
│  └─ stability.json
├─ logs/
│  ├─ controller.jsonl
│  ├─ qwen_server.log
│  ├─ carla.log
│  └─ errors.jsonl
└─ media/
   └─ demo.mp4
```

`run_manifest.json` 固定记录：Git commit、镜像 digest、模型 revision、配置 profile、随机种子、测试集 hash、开始/结束时间和最终状态。

### 8.3 延迟阶段

- `asr_nlu_ms`：音频输入完成至结构化语义输出。
- `sensor_fusion_ready_ms`：本帧所需视觉、点云、车辆和环境数据齐备时间。
- `qwen_service_ms`：请求发出至动作码返回。
- `post_qwen_control_ms`：目标绑定、安全仲裁至最终控制生成。
- `end_to_end_ms`：所有输入信号接收完成至最终轨迹/控制可用。

每个阶段记录 mean、P50、P95、P99 和 max。固定图片热门禁单独标记为诊断项，不能写入正式端到端指标。

## 9. 错误处理

- 权重、镜像、revision 或 CUDA 版本不匹配：预检失败，不启动评测。
- Qwen 未在限定时间 READY：保存服务日志，终止本次 run。
- A800 优化内核启动失败：保留失败日志并切换 `safe` 内核 profile；报告必须记录回退。
- 语音、视觉或目标无效：按现有安全边界 fail-closed，不伪造成功动作。
- P95 超过 300 ms：标记 `EARLY_STOP`，不运行耗时正确率和稳定性集合。
- CARLA/ScenarioRunner 异常退出：保存最后帧、Actor 状态和退出码，不删除运行目录。

## 10. 测试策略

### 10.1 代码级

- profile 解析、manifest、hash、run ID 和指标 Schema 单元测试。
- 2B/3B 模型配置不能改变共享安全边界的回归测试。
- 未知 ScenarioRunner 场景 ID 和 evaluator-owned Actor 测试。
- 缺失目标、视觉无效、ASR 失败、Qwen 超时和容器服务失败测试。

### 10.2 5070 集成级

- 从 `docker load` 后的镜像启动，禁止读取宿主机 venv 和模型缓存。
- 固定 WAV 完整链 smoke。
- 三类代表物理场景各一次。
- 动态 RGB、多目标、目标缺失和安全冲突冻结集。
- Notebook 从现有 metrics 生成表格和结论。
- README 在新终端按原文复现，不使用开发者记忆中的额外步骤。

### 10.3 A800 实机级

- `preflight` 后先运行 5 次预热和 10 次门禁。
- 分别记录 `safe` 与 `optimized` profile；正式结果只引用实际稳定 profile。
- 门禁通过后运行冻结准确率和三类物理闭环。
- 达到或接近正式线后运行 30 分钟稳定性。
- 将 A800 结果加入 metrics，不覆盖 5070 参考结果。

## 11. 文档和展示一致性

- README、Notebook、技术方案 PDF、视频和 metrics 使用同一 release manifest。
- README 给出输入、输出、命令、预期文件和失败排查，不复制长篇技术方案。
- Notebook 只完成环境展示、最短样例、指标读取和结果验证，不承担环境安装。
- PDF 解释架构、数据、压缩、车规适配、安全边界和指标，不伪造正式设备结果。
- 视频必须显示语音/文本输入、CARLA 画面、动作决策、车辆响应和场景结果。

## 12. 非目标

- 不在打包阶段重新训练或微调大模型。
- 不为了包装材料重复运行已经有可靠证据的无关测试。
- 不承诺 RTX 5070 指标等于 A800 指标。
- 不把语言模板数量等同于物理场景数量。
- 不把 Qwen 动作码直接连接到油门、刹车或方向盘，最终控制继续经过 D 安全仲裁。
