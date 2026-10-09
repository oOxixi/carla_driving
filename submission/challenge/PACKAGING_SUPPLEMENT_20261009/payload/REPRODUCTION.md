# 挑战赛道运行入口

完整环境、请求接口、真实 RGB 输入示例、Docker 构建和导出命令见根目录 README.md。当前运行入口与模型身份见 99_交付清单/MODEL_SELECTION.json。

从本包根目录启动：

```text
python 02_源码与部署/scripts/launch_student.py --mode http --variant full_int8 --port 8100
```

常驻 JSONL 输入示例：

```text
python 02_源码与部署/scripts/launch_student.py --mode serve --variant full_int8 --input 02_源码与部署/source/examples/delivery_request.jsonl
```

原始性能与评测脚本保持在 02_源码与部署/source/challenge 下，运行时从 source 目录启动，模型参数按根目录 MODEL_SELECTION.json 给出的实际路径传入。历史案例和 RGB 的仓库相对位置已经保留。

运行模式、环境与日志口径分开记录：X86 模型和规划链以 B3 现有官方镜像原始日志为准；BC/HBM 是地平线编译实体；BPU 性能是工具预估。本次只整理文件和入口，没有运行新的模型测试或测量。指定芯片 SDK 源码已补，未做 SDK 编译/实板推理；Docker 镜像实体仍需有 Docker 的机器导出。

83 场景工具以 `02_源码与部署/source` 为源码根；场景与 health 衔接已补齐。新 CPU 850 例回放入口、依赖及证据范围见 `06_评测说明与冻结方案/final_results/OFFLINE_850.md`。
