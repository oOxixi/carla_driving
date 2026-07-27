# 最终提交检查清单

## A. 代码冻结

- [ ] 明确最终分支、tag 和 40 位 commit SHA。
- [ ] `git status` 干净；没有临时脚本、账号、绝对路径或密钥。
- [ ] 全量 pytest 通过，输出保存为文本和 JSON/JUnit 证据。
- [ ] 场景 JSON 校验、数据集校验、离线回放验收均通过。
- [ ] requirements/环境版本已锁定，CARLA、Python、CUDA/驱动版本写明。
- [ ] 模型权重不直接混入代码仓库；提供来源、版本、许可证、SHA-256 和下载/放置说明。

## B. 客观验证证据

- [x] 基础、进阶、挑战三级场景均有真实 CARLA 单轮运行记录。
- [ ] 每个正式场景记录 map、seed、天气、命令、启动参数、commit 和配置哈希。
- [ ] 保存 RGB/点云/音频或 ASR 输入、模型输出、安全仲裁、最终控制和任务判定。
- [ ] 报告任务完成、碰撞、闯灯、越线、超时、最小距离。
- [ ] 报告动作准确率、目标关联准确率和安全覆盖正确率，给出分母而不只给百分比。
- [ ] 报告 mean/P95/P99/max 延迟、帧率、掉帧、超时、显存和持续运行时间。
- [ ] 失败运行不删除；标注环境故障、实现故障或数据问题。
- [x] 干净音频 250 条已在 RTX 5060 上实跑并生成逐条 JSON、逐语言 Markdown 和运行日志。
- [ ] 50 ± 1 dBA 音频需声级计校准后完成 250 条实跑。
- [x] 已接入 faster-whisper 条件复核和 Platt 校准；正式材料须分别标注 SenseVoice 原生覆盖 0% 与高风险条件复核覆盖 62%。

## C. 多模态数据集

- [ ] `dataset_card.json` 写明来源、用途、规模、切分、许可证、限制和已知偏差。
- [ ] train/val/test 按 sequence/scenario/seed 隔离，无相邻帧泄漏。
- [ ] 普通话、方言、噪声、同义、否定、组合、歧义和危险冲突均有样本。
- [ ] RGB、LiDAR、音频和状态使用统一时钟；保存最大时间偏差。
- [ ] 标签至少双人复核关键动作和目标关联。
- [ ] `tools/validate_multimodal_dataset.py` 对冻结 JSONL 通过。
- [ ] 数据与模型大文件另存，提交 SHA-256 manifest 和访问说明。

## D. 专家评审材料

- [ ] 1 页方案摘要：问题、核心结果、三项贡献、关键数字。
- [ ] 架构图：语音/RGB/LiDAR→融合/Qwen→安全仲裁→B/C 控制→CARLA。
- [ ] 接口表：ASRCommand、SceneState、Qwen 受限输出、DrivingIntent、VehicleControl。
- [ ] 失败与降级表：低置信度、目标不唯一、帧过期、模型超时、非法 JSON、CARLA 断连。
- [ ] 对比/消融：无视觉、无 LiDAR、无安全仲裁、规则路径与 Qwen 路径。
- [ ] 3–5 分钟视频可独立看懂，画面同步显示命令、目标、决策、覆盖原因、车速和延迟。
- [ ] README 从全新机器验证；提供预期输出和常见错误。
- [ ] 第三方许可证、引用、模型卡和数据集许可证齐全。

## E. 最终包建议

```text
submission_package/
  README_FIRST.md
  source_commit.txt
  environment/
  configs/
  reports/
    scoring_traceability.pdf
    test_summary.json
    latency_summary.json
    scenario_summary.json
  evidence/
    evidence_index.json
    representative_runs/
  dataset/
    schema.json
    dataset_card.json
    manifest.sha256
    small_examples/
  models/
    model_manifest.json
    download_instructions.md
  docs/
    architecture.pdf
    final_report.pdf
    slides.pdf
  demo/
    demo.mp4
    demo_script.md
  licenses/
```

## F. 提交前最后一次复核

- [ ] 所有报告中的数字可由原始日志重新计算。
- [ ] 所有证据路径存在且哈希一致。
- [ ] 材料没有把内部代理集写成官方评测集。
- [ ] 材料明确哪些信号来自真实传感器、地图/配置回退或模拟真值。
- [ ] 在另一台机器按 `README_FIRST.md` 完成一次冷启动复现。

