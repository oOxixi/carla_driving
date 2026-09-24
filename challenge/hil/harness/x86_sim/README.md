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
