# 多模态驾驶数据集规范 v1

本目录定义比赛自建数据集的统一交换格式。目标是让 CARLA、公开数据集适配结果、语音组输出、Qwen 决策结果和最终验收证据使用同一条可追溯记录。

## 1. 目录约定

```text
datasets/carla_multimodal_v1/
  dataset_card.json
  records/
    train.jsonl
    val.jsonl
    test.jsonl
  splits/
    train_sequences.txt
    val_sequences.txt
    test_sequences.txt
  sequences/<sequence_id>/
    manifest.json
    rgb_front/<frame_id>.jpg
    lidar_roof/<frame_id>.npy
    audio/<command_id>.wav
    qwen_raw/<request_id>.json
  annotations/
    label_map.json
    annotation_guideline.md
  evidence/
    capture_log.jsonl
    quality_report.json
```

仓库只提交 schema、小样例、清单和生成脚本。真实图像、点云、音频、模型权重及大日志应放在版本化数据存储中，提交时提供 URI、许可证和 SHA-256 清单。

## 2. 一行一条样本

`records/*.jsonl` 每行对应一个决策时刻，主键为 `sample_id`。同一语音指令可关联连续多帧，但必须共享 `command_id`，并通过 `sequence_id` 和时间戳保持顺序。

必备信息：

- 来源、版本、许可证和采集配置；
- CARLA frame、仿真时间及同步状态；
- RGB 前视帧和传感器存在性；
- ASR 原文、规范化文本、置信度、指令意图与参数；
- 自车状态、环境、感知目标及稳定 `track_id`；
- 期望高层动作、实际模型动作、安全仲裁结果和最终控制；
- 各阶段延迟、任务结果和质量标记；
- Git 提交、配置哈希、CARLA/模型版本和标注版本。

完整字段见 `schema.json`，最小合法记录见 `examples/sample.jsonl`。

## 3. 数据级别

| level | 用途 | 最低模态 |
|---|---|---|
| `command_only` | 语音/NLP 单元测试 | 文本或音频、期望意图 |
| `perception` | RGB/点云感知训练与验证 | RGB，建议 LiDAR，目标标注 |
| `decision` | 多模态高层决策 | RGB、文本/音频、自车状态、目标、期望动作 |
| `closed_loop` | CARLA 闭环验收 | `decision` 全部字段、模型输出、安全仲裁、控制和任务结果 |

最终评分证据只接受 `closed_loop`；其他级别不能替代真实闭环结果。

## 4. 切分与防泄漏

1. 按 `sequence_id + scenario_id + seed` 分组切分，禁止按帧随机切分。
2. 同一路线、天气、演员布局和同义指令变体应归入同一分组。
3. 建议初始比例为 70%/15%/15%，最终以覆盖度而不是固定比例为准。
4. `test` 标签冻结后不得参与提示词、阈值或控制参数调优。
5. 主办方隐藏评测集不进入本目录；本地测试只能称“隐藏集代理测试”。

建议覆盖基础、进阶、挑战三级难度，以及普通话/方言、噪声、否定、组合、歧义、目标不存在、传感器过期、模型超时和非法 JSON 等困难负样本。

## 5. 标注与质量门槛

- 两名标注者独立标注 `expected.actions`、目标对象和是否需要确认；冲突由第三人复核。
- 所有媒体路径必须是数据集根目录下的相对路径，不允许绝对路径或 `..`。
- 时间戳使用纳秒整数；延迟统一使用毫秒。
- `eligible_for_score=true` 仅在同步有效、必需媒体存在、标注已复核且无严重质量标记时设置。
- 模型自由文本只能存入 `qwen_raw` 证据；控制链只消费受限高层动作。
- 安全仲裁覆盖模型动作时，同时保存 `requested_action`、`final_action` 和 `override_reason`。

## 6. 验证

```powershell
python tools/validate_multimodal_dataset.py `
  datasets/multimodal_v1/examples/sample.jsonl
```

真实数据集增加 `--check-files --dataset-root <数据集根目录>`。验证器检查必填字段、ID 唯一性、路径安全、时间值、动作空间和跨 split 的 sequence 泄漏。

## 7. 从采集清单构建

`tools/build_multimodal_dataset.py` 接收一行一帧的规范化采集 JSONL，
校验 RGB/LiDAR/音频相对路径，计算媒体 SHA-256，并按
`sequence_id + scenario_id + seed` 确定性写入三个 split：

```powershell
python tools/build_multimodal_dataset.py capture.jsonl `
  --dataset-root D:/carla_capture `
  --output-root D:/carla_multimodal_v1 `
  --sequence-id town03_d03_seed0 `
  --scenario-id D03_front_vehicle_brake `
  --seed 0 --difficulty advanced --map Town03 `
  --git-commit 6eb269a `
  --config-sha256 <64位配置SHA256>
```

输出包括 `records/{train,val,test}.jsonl`、三个 sequence 清单和
`evidence/quality_report.json`。之后必须把三个 split 一起校验，才能发现跨文件泄漏：

```powershell
python tools/validate_multimodal_dataset.py `
  D:/carla_multimodal_v1/records/train.jsonl `
  D:/carla_multimodal_v1/records/val.jsonl `
  D:/carla_multimodal_v1/records/test.jsonl `
  --check-files --dataset-root D:/carla_capture
```
