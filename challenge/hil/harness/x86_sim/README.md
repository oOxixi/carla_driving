# X86 仿真测试脚本（无板端）

> ⚠️ 这套脚本用于**替代条件下的可行性演练**（A1 随机初始化结构 + 自建校准集 + X86 仿真运行时），
> 产出的数字不是最终测试结果。

这套脚本在 OE 3.9.1 CPU 容器里跑，用于"不接 J6P 板卡也能做的检查"。
结果与口径见 [`../../x86_simulation_scope.md`](../../x86_simulation_scope.md) 与
[`../../evidence/x86_simulation_20260924/`](../../evidence/x86_simulation_20260924/)。

## 挂载约定

脚本里的路径按下面这套挂载写死；换机器时改这一段即可。

| 宿主 | 容器内 | 用途 |
|---|---|---|
| `D:\nana\oe\horizon_j6_open_explorer_v3.9.1-py310_20260821` | `/open_explorer` | OE 工具链与 samples |
| `D:\nana\oe\work` | `/work` | 工作区（模型、产物、日志、证据） |
| `D:\nana\oe\dataset` | `/data/horizon_j6/data` | 数据集（当前为空） |

关键目录：模型 `/work/student/student_v0_fp32.onnx`；未校准产物 `/work/student/.hb_compile/`；
校准产物 `/work/student/.hb_compile_cal/`；日志与证据 `/work/x86_sim/{logs,evidence}/`。

## 前置

```bash
# X86 版 hrt_model_exec（OE 包自带源码，不需要外网下载）
pip install cmake
cd /open_explorer/samples/ucp_tutorial/tools/hrt_model_exec
bash build_x86.sh                          # 产出 output_shared_J6_x86/
export HB_UCP_SIM_PLATFORM_TYPE=nash-p     # 否则加载 nash-p 产物会报 march 不匹配
```

## 脚本

| 脚本 | 作用 |
|---|---|
| `run_x86_sim.sh` | 一键：`model_info` → 导出 `.bin` → `infer --enable_dump` → 一致性 + 耗时 |
| `make_bins.py` | 把 B3 `dump-tensors` 的 `.npy` 按 manifest 顺序转成 raw float32 `.bin` |
| `sim_consistency.py` | `HBRuntime` 跑 `.hbm`/`.bc`，与 onnxruntime 浮点参考逐头算余弦 |
| `compare_dumps.py` | 把 CLI dump 按 **stride 去填充**后与浮点参考比对（`stride[-2]` 是行 pitch） |
| `run_hb_verifier.sh` | `hb_verifier`：浮点 ONNX ↔ int8 `.bc`（须按 input_names 顺序传 4 个文件） |
| `build_cal_dirs.py` | 把 `dump-tensors` 的 30 例张量组织成 `cal_data_dir` 需要的 4 个目录 |
| `cal_config.yaml` | 带校准的 PTQ 编译配置（`march: nash-p`、`march`/`cal_data_dir`/`O2`） |
| `check_calibrated.sh` | 对比未校准/已校准的阈值分布，并对校准产物重跑 `hb_verifier` |
| `run_calibrated_infer.sh` | 对校准产物跑 CLI `infer` + dump 对照 |
| `collect_evidence.sh` | 汇总 `logs/` 为文本证据（剥离 ANSI、按需裁剪）到 `evidence/` |
| `cal_config_d3w2.yaml` | 用 **B1 签名 D3 Wave2 train 64 例**校准的 PTQ 配置（2026-09-25） |
| `cal_config_gap.yaml` | 用 **B1 定向补采（targeted gap）train 128 例**校准的 PTQ 配置（2026-09-26） |
| `batch_verify.sh` | 对一个 dump set 逐例跑 `hb_verifier`（浮点 ONNX ↔ int8 `.bc`）；第 4 个参数是并行度（容器 20 核时用 8 合适） |
| `summarise_verify.py` | 把批量 `hb_verifier` 日志汇总成逐头 min/p05/p50/mean/max 分布 |
| `run_d3w2_verify.sh` | 一键：D3 Wave2 批量一致性 + 分布汇总 |
| `run_d3w2_cli_check.sh` | D3 Wave2 产物在 CLI（X86 仿真）路径上的单例互证 |
| `thresholds_report.py` | 对比多次编译的量化阈值分布（是否退化为默认 1.0） |
| `collect_d3w2_evidence.py` | 汇总 D3 Wave2 轮的证据（编译日志、分布、阈值、CLI 互证） |
| `collect_gap_evidence.py` | 汇总定向补采轮的证据（编译日志、阈值对照、三个分布摘要） |
| `../release_check/verify_b1_release.py` | B1 发布完整性独立复核（按签名声明逐项校验；`--eol auto` 处理 CRLF） |

## 典型用法

```bash
python3 build_cal_dirs.py /work/cal_dumps /work/cal 30      # 先由 dump-tensors 产出 cal_dumps
cd /work/student && hb_compile -c /work/x86_sim/cal_config.yaml
bash check_calibrated.sh
bash run_calibrated_infer.sh
bash collect_evidence.sh
```

## 注意

- dump 的读法必须按 `stride[-2]` 去掉行填充，否则 `behavior_logits`(14→16)、
  `target_pointer_logits`(9→16)、`target_lane_logits`(6→8) 会算出假低相似度；
- 不要用 `hb_compile --fast-perf` 做接口对照——它会按 NV12 重建输入（`rgb_y`/`rgb_uv`）；
- `hb_verifier` 当前只支持 `onnx↔bc`，`onnx↔hbm` 会直接报不支持。

## 批量规模参考（2026-09-25 实测）

| 场景 | 命令要点 | 规模与耗时 |
|---|---|---|
| D3 Wave2 val | `batch_verify.sh /work/dumps_d3w2 <bc> <logdir> 1` | 56 例 ≈ 4 分钟（单进程） |
| D2 v1.1 val 全量 | `batch_verify.sh /work/dumps_d2 <bc> <logdir> 8` | **539 例 ≈ 21 分钟**（8 进程；容器 20 核，load 会到 ~39，说明已饱和） |

长稳对照提示：`cli soak --duration-minutes 1` 做同刻 A/B，比跨会话比较绝对吞吐可靠——
2026-09-21 与 2026-09-25 两次 30 分钟长稳的吞吐差 5.5×，1 分钟对照证明来自主机状态。
