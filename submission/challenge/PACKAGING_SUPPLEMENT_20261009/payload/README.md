# 挑战赛道材料整理说明

当前为待补齐的材料整理目录，尚未形成最终交付包。按用户要求，成员缺件补全前不生成压缩包；完整缺件见 99_交付清单/仅剩成员缺件.md。

本包将当前鲁棒 V3 权重、Adapter V3.1、量化模型、历史数据与 RGB、B3 性能和评测材料整理为可查阅的交付目录。已原样纳入团队提供的《挑战赛道提交报告_轻量化模型的车规级部署.docx》，本次没有改写报告。总 README、创新要点、量化选型、数据与指标说明及 X86 启动和 Docker 构建材料均已补齐。应用指标终版、指定芯片工程和演示入口已补齐，自建 Student 镜像 tar 已补，最终 Linux 加载/启动、官方 OE 原镜像、实际演示与其他原始输出仍按实体材料表收取。

## 阅读入口

| 目录 | 内容 |
| --- | --- |
| 01_技术报告 | 团队提交报告原件、报告与附件对照、素材与引用索引、创新要点、A1 原始交接 |
| 02_源码与部署 | 当前 Student 源码、历史数据与 RGB、常驻/HTTP 启动器、Docker 构建和导出脚本 |
| 03_训练与模型 | 当前 A3 鲁棒 V3 训练交接、A2 FP32 / Full INT8 / Mixed Top-3 及量化报告 |
| 04_量化与编译输入 | OpenExplorer 配置与 1200 个校准张量、A2 反馈原件 |
| 05_B3性能与评测 | X86 性能日志、BPU 工具报告与 HBM/BC、评测与衰减对比 |
| 06_评测说明与冻结方案 | 数据说明、指标定义、历史 ASR 实跑与 250 条音频、既有冻结与诊断原件 |
| 07_演示材料 | 真实演示录制脚本与收件位置 |
| 08_申报与官方要求 | 原始评分细则与备用技术素材；申报表队长已完成，待原文件归档 |
| 99_交付清单 | 模型选择、逐文件清单、来源索引、剩余成员缺件 |

## 模型选择

默认 X86 入口使用 Full INT8：已有完整 83 场 FP32/INT8 配对结果。FP32 为浮点参考，Mixed Top-3 保留为备选。这个默认值只决定打包运行入口，不把候选改成已通过最终验收的模型。完整文件路径与 SHA 位于 `99_交付清单/MODEL_SELECTION.json`。

A1 原始交接中的 `student_v0_fp32.onnx` 是随机初始化的结构分析样例，独立放在 A1 材料目录，不能作为实际模型入口。当前 A3 交接已经替换原急交包中的旧训练交接。

## 运行环境

已有 X86 报告对应官方镜像 `openexplorer/ai_toolchain_ubuntu_22_j6_cpu:v3.9.1`，Python 3.10.12、Torch 2.8.0+cpu、ONNX Runtime 1.19.0。复现既有测量应使用该环境；A1 的结构分析环境和 A3/A2 的训练/导出环境分别以原件中的环境记录为准。

本机直接运行需要 Python、Torch、ONNX Runtime、NumPy、Pillow、jsonschema、PyYAML。官方镜像内额外依赖见 `02_源码与部署/docker/requirements-runtime-extra.txt`。训练用 `challenge/requirements.txt` 与已有实测环境不同，不能用它覆盖官方环境的 Torch/NumPy 版本。

## 启动 X86 Student

在本包根目录执行：

```text
python 02_源码与部署/scripts/launch_student.py --mode http --variant full_int8 --port 8100
```

该服务提供 `POST /infer`，默认返回 ManeuverPlan V2；请求中应提供 ModelRequest V1，包括文本、目标、场景状态与正确的 `rgb_ref`。`GET /health` 返回服务状态与已有统计。CARLA runner 应使用 `--qwen-service-url http://127.0.0.1:8100 --qwen-mode planner_v2`。

切换浮点参考：`--variant fp32`；切换备选：`--variant mixed_top3`。

常驻 JSONL 模式与包内真实 RGB 请求示例：

```text
python 02_源码与部署/scripts/launch_student.py --mode serve --variant full_int8 --input 02_源码与部署/source/examples/delivery_request.jsonl
```

预期每条输入输出一个结构化计划 JSON，包含 `schema_version=2.0`、`plan_type=MANEUVER_SEQUENCE`、`steps`、目标与完成条件；不是油门/制动向量。示例来源记录位于同目录的 `delivery_request_source.json`，仅作为运行输入。

只打印启动命令可使用 `--dry-run`。已有实测数字不由该选项产生。

## 构建并导出 Docker

锁定依赖与实际导出流程已经补齐，详见 `02_源码与部署/docker/README.md`。在已有官方基础镜像和 Docker 的机器执行：

```powershell
& '.\02_源码与部署\docker\build_and_export.ps1'
```

Linux 执行 `bash 02_源码与部署/docker/build_and_export.sh`。完整成功的输出在 `02_源码与部署/docker/exports/<时间>/`，包含真实镜像 tar、image manifest/inspect、实际依赖版本、日志和 SHA256。后续已通过真实 Linux runner 构建自建运行时，并本地附加私有模型生成 Student tar；官方 OE 基础镜像与最终 Linux 加载/启动仍待补。

## 芯片与演示工程

`02_源码与部署/chip_runtime` 已补 SDK C++ 常驻推理、CPU 预处理和原 Adapter 桥接、CMake/交叉编译及启动脚本。当前工程尚未做 SDK 编译和实板推理，支持范围与严格 IO 检查见该目录 README。

`07_演示材料/scripts` 已补当前 Student 启动、已有音频/现场麦克风输入、CARLA 摄像头实录和同次日志收集。运行依赖真实 CARLA/语音环境，不拼接旧视频作为新运行证据。

## 数据与评测入口

历史数据发布版位于 `02_源码与部署/source/challenge/dataset/releases`，治理原件位于 `.../governance`，既有 RGB 冻结快照位于 `.../challenge/hil/frozen`。在 source 目录运行原始评测脚本，可保持案例的仓库相对路径。

850 例结构化计划一致率、83 场闭环、47 个共有场景衰减属于不同指标，定义和分母见 `06_评测说明与冻结方案/指标与结果说明.md`。既有结果和版本清单来自 B3 原件；不以计划一致率替代真实语音识别准确率。

新 240 例冻结方案与采集入口已保存，属于团队额外补采，不作为官方固定样本数要求。当前可复算指标见 `06_评测说明与冻结方案/final_results/RESULTS.md`；已有 CPU 利用率和 BPU 口径说明见 `05_B3性能与评测/异构利用率口径`。真正需要收取的实体文件见 `99_交付清单/需要成员交给你的实体材料.md`。

历史合成语音 ASR 原始输出、250 条 MP3 与转写真值已收入 `06_评测说明与冻结方案/历史ASR实跑证据`；该附录明确使用历史 GPU 条件，当前模型的应用指标前后对照按成员收件表汇总。

## 2026-10-09 再次补齐

已恢复原源码缺失的 167 个场景文件，修复验收入口与 Student 健康响应的衔接，并增加独立 CPU controller Dockerfile/Compose。原模型、预处理与 Adapter 字节保持不变。部署改动见 `02_源码与部署/部署补齐说明_20261009.md`。

已在独立依赖目录中并行执行真实离线回放，FP32/Full INT8 各 850/850 成功、0 错误。新原始记录与指标见 `06_评测说明与冻结方案/final_results/offline850_comparison_20261009T024659_050722Z/RESULTS.md`；这是 Python3.12/Windows 本机 CPU 新回放，不覆盖官方镜像历史测量、不包含 ASR/CARLA，也不是正式 B2 Gate。

现有 ASR LoRA/配置身份已导出，缺失基座/VAD/级联权重仍需真实前端运行环境提供。最新剩余收件见 `99_交付清单/仅剩成员缺件.md`。

<!-- DOCKER_RECEIPT_20261009_START -->
## 本次 Docker 实体代补

自建 Student tar 与两类实际日志已归档，使用说明见 `02_源码与部署/docker/本次Docker交付_20261009.md`。运行时阶段实际完成 Docker build/run/inspect/save；最终带模型 archive 尚未 Linux load、启动或推理。Debian11 公共 Python base 不等同 OE 官方工具链。
<!-- DOCKER_RECEIPT_20261009_END -->
