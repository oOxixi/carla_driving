# 850 例当前模型离线原始输出补采

6 个冻结队列共 850 条案例、931 个 Teacher 步，现有包内对应 RGB 文件齐全，逐条 SHA-256 与案例记录匹配。`offline_850_input_inventory.json` 记录输入核对结果，没有模型推理结果。

2026-10-09 两个 variant 已按下述入口真实执行，各 850/850 成功。新运行分别为 `offline850_new_cpu_fp32_20261009T024659_050722Z` 与 `offline850_new_cpu_full_int8_20261009T024659_043721Z`，比较表见 `offline850_comparison_20261009T024659_050722Z`。本次使用独立 vendor：ORT 1.19.0、numpy 1.26.4；Torch 2.6.0+cu118、Pillow 10.4.0、jsonschema 4.23.0。仍未执行 ASR/Teacher/CARLA，不替代历史同次基准。

现有 `source/challenge/hil/harness/x86_sim/teacher_student_decay.py` 依赖原机器 `dumps_*` 输入，只保存聚合统计。新增 `collect_offline_850.py` 直接读取冻结案例和 RGB，严格禁止预处理器将缺图替代为零图，并保存当前 FP32/INT8 的逐例原始十头输出和解码计划。

先检查输入与模型身份（只用标准库，不执行模型）：

```bash
python collect_offline_850.py --variant fp32 --preflight-only
python collect_offline_850.py --variant full_int8 --preflight-only
```

真实 CPU 推理需要 Python 3.12 环境、numpy、torch、Pillow、jsonschema、onnxruntime。可以在两个独立进程运行：

```bash
python collect_offline_850.py --variant fp32 --ort-threads 1
python collect_offline_850.py --variant full_int8 --ort-threads 1
```

若使用工作区独立依赖，可加 `--dependency-root /path/to/vendor`。对两路已保存结果复算用 `summarize_offline_850.py --fp32-dir <FP32新运行目录> --int8-dir <INT8新运行目录>`，不重新执行模型。

默认从脚本位置寻找完整材料包，允许 `--package-root /path/to/package`。输出仅保存在本目录独立的 `offline850_new_cpu_<variant>_<UTC>/` 子目录，含 Student 原始输出 JSONL、计划 JSONL、保存 Teacher 标签 JSONL 和模型/输入/源码/环境哈希清单；错误逐例保留，不能被省略或计为通过。

这是新的一轮 CPU 离线补采：没有 ASR 或 CARLA 执行，Teacher 标签来自既有记录，并非新运行 Teacher；不替代旧 B3 同次实验，也不属于未见独立 B2 Gate。输入里已经暴露的 Teacher 标签不能用来修模型。推理耗时仅为当前 CPU 模型调用，不是语音端到端时延。
