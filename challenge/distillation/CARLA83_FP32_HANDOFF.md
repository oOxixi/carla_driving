# Student FP32：CARLA 83 场仿真交接

状态：项目 83 场 CARLA 仿真通过 3% 线。不是官方独立基准、实板或量化版成绩；不要将历史 Features16 BC/HBM 与本轮 FP32 混为同一候选。

| 指标 | Teacher | Student FP32 |
| --- | ---: | ---: |
| 场景通过 | 76/83 | 74/83 |
| 加权完成率（基础/进阶/挑战 30/40/30） | 92.17% | 90.83% |
| 碰撞 / 红灯违规 / 严重路线偏离 | 0 / 0 / 0 | 0 / 0 / 0 |

166/166 次有效判定。相对衰减 `(Teacher − Student) / Teacher = 1.4467%`。剩余两个绕障场景差异未做场景特判，不阻断项目仿真过线。

## 版本绑定

- CARLA 0.9.16；使用 `scenarios/acceptance_suite/matrix.json` 的 83 个场景、原 seed、RGB/LiDAR、低分辨率诊断 profile、感知超时 1.5 s、看门狗 4 s。没有测 ASR、正式时延或实板。
- Teacher `Qwen/Qwen3.5-2B` revision `15852e8c16360a2fea060d615a32b45270f8a8fc`，fingerprint `4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa`。Teacher 是独立服务：从 `fix/teacher-baseline-refresh` 取规划器 Git `95e97b00def8ec36f12937da34ce8bb9082c4a04`，以 `planner_v2` 启动；不要拿本分支 Student 使用的 HTTP 服务模块替代该来源。
- Student：`student_post_turn_explicit_dev.onnx`，精度 FP32，预处理契约 `explicit-v2`，ONNX SHA256 `e8e4cb0f500a848b0462015d7f80f7716316aa5364cd3494526c72724d04a63c`。从已授权的服务器实验产物取得模型并校验哈希，Git 不随附权重。
- 工作树内容来自作业 38 的执行快照、Student 服务快照和服务器干净基础 checkout `ca353478af8130bf5d2f9622cade4c25284776da` 的依赖文件。`integration/second_group_runtime.py` 在服务器验收原件的 SHA256 是 `011b2049b4e76d0d5097d43a6c0060fd367a148c24e9873c65e1ce85d21d5100`。场景输入和计分脚本与基线作业 36 相同。

从仓库根目录运行 Student 的 Planner V2 测试入口（依赖 CPU ONNX Runtime、PyTorch、Pillow 等；`--root` 是运行时双方共享的 RGB 证据根）：

```bash
python -m challenge.distillation.turn_phase_student \
  --model /path/to/student_post_turn_explicit_dev.onnx \
  --root /path/to/run-evidence --port 18337
```

CARLA 入口 `python -m integration.carla_runner`，每个角色用独立 `--qwen-service-url`、共同的 `--qwen-mode planner_v2 --perception-mode sensors --scenario-facts-mode perception`。原始服务器批次的隔离脚本为 [run_paired_closure_screen.sh](run_paired_closure_screen.sh)，其默认路径对应早期快照，复跑修复版须显式绑定 `CLOSURE_RUNTIME_SCOPE`；不是生产启动脚本。汇总入口 [summarize_paired_closure.py](summarize_paired_closure.py) 与 [summarise_student_loop.py](../hil/carla/summarise_student_loop.py) 一同放在运行目录，未集齐 166 份可核验判定时不输出衰减结论。

## 证据

`tiaozhansai` 作业 38：`artifacts/numeric_speed_conditioned_20261112/paired_full83_fix.uTXN9EMh/`。`paired_report.json` SHA256 `03051c55c13ad00207d27d5e04cb922e9f11629621afa978f49a49972608f64e`。该目录另有场景 SHA、运行快照 SHA 和逐场原始日志，不随本次 Git 提交发布。参见[基线与修复经过](FULL_CARLA83_PAIRED_20261115.md)和[历史量化候选交接](FEATURES16_CANDIDATE_HANDOFF.md)。
