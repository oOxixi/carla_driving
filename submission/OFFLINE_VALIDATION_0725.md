# 2026-07-25 本机离线验证记录

## 已实现

- 本地 Qwen2.5-VL checkpoint 适配器；
- 冻结 `QwenInputContext` 和严格高层 JSON 输出；
- 模型禁止输出油门、刹车和方向盘；
- `PENDING/TIMEOUT/STALE/ERROR` 不生成模型控制命令，由 watchdog 和 D 安全链降级；
- 14 条中文驾驶语言代理样本，七类各 2 条；
- 从规范化采集 JSONL 构建多模态 train/val/test；
- 媒体相对路径与 SHA-256、分组切分和跨 split 泄漏检查；
- CARLA-free RGB/LiDAR/Qwen/A-B-C-D 离线回放。

## 本次结果

```text
针对性新增功能测试：19 passed
全量回归：344 passed, 1 skipped
语言测试集：14 cases，7/7 categories，PASS
多模态最小样例：PASS
离线回放样例：2/2 frames，PASS
```

复现命令：

```powershell
python -m pytest -q

python tools/validate_language_testset.py `
  datasets/language_v1/commands.jsonl `
  --report artifacts/language_testset_report.json

python tools/validate_multimodal_dataset.py `
  datasets/multimodal_v1/examples/sample.jsonl

python tools/replay_acceptance.py `
  examples/replay_acceptance_sample.jsonl `
  --output artifacts/replay_report_0725.json
```

## 证据边界

- 本机没有提供真实 Qwen checkpoint，本次没有声称真实模型精度或延迟通过。
- Qwen 单帧真实模型入口已具备，需在模型机器执行
  `tools/run_qwen_vl_decision.py`。
- 离线回放不能替代 Ubuntu CARLA 的真实 RGB/LiDAR 闭环、三个代表场景录像和稳定性数据。
- 14 条语言样本是本地冻结代理集，不是主办方隐藏测试集。
