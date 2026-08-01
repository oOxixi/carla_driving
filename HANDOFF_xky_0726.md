# HANDOFF xky 0726

## 当前版本

- 主分支：`main`
- 今日功能提交：`1c108a0`
- `main` 已包含原 `7.25`、Day23 Qwen 完成分支及今天的全部本地更新。
- 阶段备份：
  - `without-modification`：原 `7.25`，提交 `65910fd`
  - `backup/7.25-next-original`：原始传感器探针阶段，提交 `84fc234`
  - `7.25-offline`：严格 Qwen/数据集离线流程阶段，提交 `bbfbedd`
  - `without-Qwen`：今天完整代码快照，与交接文件提交前的 `main` 同源

## 今日完成

- 修复 250 条标准语音文本解析，补齐自动化回归、安全边界、依赖、模型清单和许可证说明。
- 接入 SenseVoice + `faster-whisper small` 条件复核：
  - SenseVoice 保持主识别器，Whisper 不替换主文本；
  - 只复核速度、变道、转向、靠边和避障等关键控制；
  - 停车/紧急停车走快速安全通道；
  - 复核置信度与 SenseVoice 原生置信度分开记录；
  - 只有校准分数不低于 `0.90` 且关键控制语义冲突时新增确认门。
- 优先从本地 ModelScope snapshot 加载 SenseVoice 和 FSMN-VAD，断网时不再无意义访问模型站。
- 增加真实音频、合成噪声、Whisper 校准和一致性分析工具及运行证据。
- 按综合评分优化：普通话、台湾国语和关键控制优先，方言保留兼容但不强制全部走双模型。

## 验证结果

- 核心自动化测试：`372 passed, 1 skipped`。
- 250 条音频：
  - ASR 完全匹配：`95.60%`
  - 字符准确率：`99.24%`
  - 意图准确率：`99.60%`
  - 槽位准确率：`99.20%`
- 条件复核调用：`236 → 155`。
- 平均端到端延迟：`391.5 ms → 287.9 ms`，准确率不下降。
- 10 dB SNR 合成噪声测试：
  - 意图准确率：`97.60%`
  - 槽位准确率：`98.80%`
  - 该结果不是正式 `50 dBA` 证据。

## Qwen 状态

- Qwen 更新代码已在 `main`：
  - Day20/21/22 多模态决策链路；
  - Day23 固定提示词、高层动作协议和决策 trace；
  - 严格 JSON 边界、安全过滤、异步超时/覆盖；
  - 离线回放验收和多模态数据集校验。
- 远程 `feat/day23-qwen-finalization` 相对 `main` 没有未合入提交。
- Qwen2.5-VL-7B 权重、CUDA 环境和实验室服务器服务不放入 Git；仓库包含接入代码，不代表换机器后模型已自动部署。

关键位置：

- `integration/qwen_boundary.py`
- `integration/qwen_async.py`
- `integration/qwen_vl_adapter.py`
- `integration/day20/`
- `integration/day21/`
- `integration/day22/`
- `integration/tests/test_qwen_*.py`

## 语音关键位置

- 主入口：`voice_group/pipeline.py`
- 主识别/VAD：`voice_group/asr_vad.py`
- 条件复核：`voice_group/asr_cascade.py`
- 级联说明：`voice_group/CASCADE_ASR_EVAL_20260726.md`
- 真实音频评测：`tools/evaluate_voice_audio.py`
- 校准工具：`tools/calibrate_whisper_confidence.py`
- 运行证据：`artifacts/voice/`

## 队友下一步

1. 在实验室服务器启动真实 Qwen2.5-VL-7B 服务，运行 Qwen timeout、invalid、stale 和安全覆盖测试。
2. 用真人录音、声级计和固定播放/采集距离完成正式 `50 dBA` 语音测试，输出逐语言准确率和 mean/P95/P99/max 延迟。
3. Ubuntu CARLA 机器继续完成三个提交场景、RGB/LiDAR 和视频证据；Windows 合成噪声结果不可替代正式声学或 CARLA 证据。
4. 最终提交前根据 `submission/SUBMISSION_CHECKLIST_0725.md` 再跑完整测试并更新证据索引。

## 注意

- 不要提交虚拟环境、CUDA 安装包、Qwen/SenseVoice 大权重或 ONNX 大文件。
- `without-Qwen` 的含义是“未随仓库部署真实 Qwen 模型环境”，不是“仓库里没有 Qwen 接入代码”。
