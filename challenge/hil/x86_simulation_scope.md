# X86 仿真测试范围与实测记录（2026-09-24）

> ⚠️ **本文全部结果均为"替代条件下的可行性演练"，不是最终测试结果。**
> 被测量的是替代对象（A1 随机初始化结构的 ONNX、自建校准集、X86 仿真运行时），
> 而不是正式被测对象（A3 真实权重、A2 官方 INT8 产物、A4 契约 Runtime、J6P 硬件）。
> 结论只能用于回答"这条测量链能不能跑、跑出来说不说得通、缺陷是否可复现"，
> **不能当作 J6P 性能/精度达标证据**；等正式输入与硬件到位后必须在同一口径下原样重跑。

> 本文回答一个问题：**在"不做 J6P 板端开发、只做 X86 仿真"这个口径下，B3 能测什么、
> 已经测出什么、哪些数字不能当成结论。**
>
> 全部数字来自 `challenge/hil/evidence/x86_simulation_20260924/`，复现脚本在
> `challenge/hil/harness/x86_sim/`。

## 0. 结论（先看这三条）

1. **X86 仿真链已打通并实测**：编译/算子预检 → 产物结构 → 三路数值一致性 → 推理功能，
   四个环节都在 PC（WSL2 + Docker + OE 3.9.1 CPU 镜像）上跑出可核验产出。
   其中 `hb_verifier`、`HBRuntime`、`hrt_model_exec` **三条独立路径给出完全相同的逐头数字**，
   互相不再打架。
2. **校准集是低余弦的根因，且我们自己补上了**。首次编译未给校准数据，
   `quant_info.json` 里 40 个阈值有 38 个是默认 `1.0`；用仓库冻结请求集自建 30 例校准后，
   阈值变成 21 个不同量级（0.347–50），十头余弦从 **0.793–1.000 提升到 0.9991–1.000**。
3. **X86 仿真不能给出任何 J6P 性能结论**：BPU 占用、DDR/ION、绑核调度、板端延迟/FPS、
   功耗与结温都测不到；X86 上的 `.bc`/`.hbm` 跑的是指令级模拟，比原生浮点慢 74× 到数千倍，
   数值只能用于**功能与定点误差**判断，不能外推为板端速度。

## 1. 用了哪些工具、跑出什么

### 1.0 正式条件 vs 本轮替代条件（先看这张表）

本轮是**可行性演练**：用替代对象把测量链路跑通，不是对正式被测对象的正式测量。

| 项 | 正式要求 | 本轮替代条件 | 对结论的影响 |
|---|---|---|---|
| 被测模型权重 | A3 真实 FP32 权重 + `weights_manifest.json`（`A3_FP32_GATE_PASSED`） | A1 结构 `challenge/student_v0_fp32.onnx`，随机初始化（seed 20260911） | 只能验证工具链，不能给精度结论；结论等级锁在 `DIAGNOSTIC_ONLY` / `X86 PRE-VALIDATED` |
| 量化产物 | A2 官方 INT8 产物 + 校准配置与校准集说明 | B3 自行 PTQ：先用冻结冒烟输入 30 例，2026-09-25 起改用 **B1 签名的 D3 Wave2 train 前 64 例** | 量化流程与 train/val 划分方法可用；仍不是 A2 的官方校准配置 |
| Runtime 入口 | A4 契约 Runtime（请求入口 + 打点 + describe + 常驻） | B3 自建适配器（inprocess / ONNX / 假板端命令） | 契约检查机制可用，A4 真实入口行为未验证 |
| 部署硬件 | J6P 板卡 + 功耗探针 | X86 仿真运行时（`HB_UCP_SIM_PLATFORM_TYPE=nash-p`） | 只能验数值与结构；延迟/占用/功耗/结温一律 `NOT_MEASURED` |
| Benchmark | B2 冻结 Seen/Variant/Unseen 清单与判据 | B3 自己的开发 val 快照（D2 v1.1 val 539 例；2026-09-25 起另有 D3 Wave2 val 56 例）与场景标签 | 分组统计机制可用，正式分组结论仍待 B2 |
| 结论用途 | 最终交付与达标判定 | **可行性演练：链路是否可用、数字是否可解释、缺陷是否可复现** | **不得作为最终测试结果或达标证据** |

环境：OE `v3.9.1`（`openexplorer/ai_toolchain_ubuntu_22_j6_cpu:v3.9.1`），
`hb_compile 3.5.16 / HBDK 4.11.11 / HMCT 2.8.4 / UCP 3.15.8`，
被测模型 `challenge/student_v0_fp32.onnx`（4 输入 / 10 输出 / opset 17）。

| # | 检查项 | 命令 | 结果 |
|---:|---|---|---|
| 1 | 编译与算子预检 | `hb_compile --model student_v0_fp32.onnx --march nash-p` | 25.5 s，**0 warning / 0 error**，opset 17→19，**59/59 节点落在 BPU（无 CPU fallback）**；产物 `student_v0_fp32.hbm` 23,644,904 B |
| 2 | 产物结构 | `hrt_model_exec model_info --model_file=*.hbm` | 4 输入 / 10 输出全部识别，含 valid shape、stride、aligned byte size（见 §3） |
| 3 | 内存口径 | `hb_model_info`（编译内置） | input 603,136 / output 2,560 / static 23,644,904 / dynamic 654,848 / temp 49,152，**min requirement 24,299,752 B** |
| 4 | 浮点↔定点一致性 | `hb_verifier -m onnx,bc -i rgb.npy,text_tokens.npy,targets.npy,state.npy` | 16 行余弦（6 层视觉骨干 + 10 个输出头），见 §2 |
| 5 | 仿真推理（CLI） | `hrt_model_exec infer --enable_dump=true` | 10 个输出头全部 dump；**Infer time 33,587 ms（未校准）/ 19,430 ms（校准）**——模拟耗时，不是性能 |
| 6 | 仿真推理（API） | `HBRuntime(model=...)` + `.run()` | `.hbm` 与 `.bc` 逐头余弦完全相同，见 §2 |
| 7 | 延迟对照（仅证明"不可外推"） | 同机同输入 n=30 | 浮点 ONNX 原生前向 mean 3.088 ms；int8 `.bc` 仿真 mean 228.0 ms → **慢 74×** |

工具清单里只有 `hrt_model_exec` 需要额外准备：OE 包自带源码
`samples/ucp_tutorial/tools/hrt_model_exec/`，用包内 gcc + `cmake` 跑 `build_x86.sh`
即可产出 `output_shared_J6_x86/`，**不需要另外下载**。

## 2. 逐头余弦：未校准 vs 已校准

输入为 B3 `dump-tensors` 产出的一个固定 case（`ACC_A01_lead_brake#0000`），
参考值为 onnxruntime 的浮点 ONNX 输出。三路工具（`hb_verifier` / `HBRuntime`(.hbm 与 .bc) /
`hrt_model_exec` dump）给出的数字**完全一致**，下表任取其一。

| 输出头 | 形状 | 未校准（thresholds 默认 1.0） | 已校准（30 例自建校准集） |
|---|---|---:|---:|
| `plan_length_logits` | (1,4) | 0.793460 | **0.999214** |
| `behavior_logits` | (1,4,14) | 0.876491 | **0.999411** |
| `target_pointer_logits` | (1,4,9) | 0.840000 | **0.999117** |
| `target_lane_logits` | (1,4,6) | 0.851552 | **0.999193** |
| `target_speed_mps` | (1,4) | 0.997520 | **0.999950** |
| `completion_type_logits` | (1,4,8) | 0.921171 | **0.999689** |
| `on_failure_logits` | (1,4,4) | 0.850498 | **0.999693** |
| `confidence` | (1,1) | 1.000000 | 1.000000 |
| `requires_confirmation_logits` | (1,1) | 1.000000 | 1.000000 |
| `replan_condition_logits` | (1,7) | 0.859126 | **0.999154** |

视觉骨干（`hb_verifier` 额外给出）：未校准 0.809–0.892；已校准 **0.9996–1.0000**。

### 2.1 2026-09-25：换成签名 D3 Wave2 数据，并按 train/val 分离复跑

上一节用的是 B3 自建的 30 例冒烟校准。B1 发布 `d3_wave2_safe_short_v1`（`B1_SIGNED_PASS`，
374 例严格正样本）后，这一环改成方法上站得住的划分：**train 前 64 例做校准、val 56 例做评估**，
数据全部来自签名发布；B3 先独立复核了发布完整性（11 个锁定文件、374 张图、318+56 行配对，
`PASS`，见 `repo_environment_findings.md` F12 关于 CRLF 的说明）。

56 例逐例 `hb_verifier`（浮点 ONNX ↔ int8 `.bc`），十头分布：

| 输出头 | min | p05 | p50 | mean | 低于 0.99 的例数 |
|---|---:|---:|---:|---:|---:|
| `plan_length_logits` | 0.9974 | 0.9979 | 0.9994 | 0.9993 | 0 |
| `behavior_logits` | 0.9992 | 0.9992 | 0.9994 | 0.9994 | 0 |
| `target_pointer_logits` | 0.9985 | 0.9987 | 0.9992 | 0.9991 | 0 |
| `target_lane_logits` | 0.9987 | 0.9989 | 0.9992 | 0.9992 | 0 |
| `target_speed_mps` | 0.9999 | 0.9999 | 1.0000 | 1.0000 | 0 |
| `completion_type_logits` | 0.9991 | 0.9993 | 0.9996 | 0.9995 | 0 |
| `on_failure_logits` | 0.9989 | 0.9990 | 0.9993 | 0.9994 | 0 |
| `confidence` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0 |
| `requires_confirmation_logits` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0 |
| `replan_condition_logits` | 0.9983 | 0.9984 | 0.9994 | 0.9992 | 0 |

视觉骨干 6 个中间张量最差 min 0.9995；**没有任何一例、任何一个头低于 0.99**。
CLI 路径（`hrt_model_exec infer --enable_dump`）在同一产物上给出同量级结果（min 0.9992），
三路互证依旧成立。逐例明细与脚本见
[`evidence/d3_wave2_calibration_20260925/`](evidence/d3_wave2_calibration_20260925/README.md)。

**这条提升只针对"数据条件"**：权重仍是 A1 随机初始化结构，结论等级不变（仍是可行性演练）。

**跨数据集复核**：把**同一个**产物（用 D3 Wave2 train 64 例校准）放到 **D2 v1.1 val 全量 539 例**上
再逐例跑一遍 `hb_verifier`，539/539 跑通，十头 **min ≥ 0.9949、p50 ≥ 0.9992，
同样没有任何一例低于 0.99**（骨干最差 min 0.9994）。即"用新数据的 train 校准、在原 D2 分布上评估"
的定点一致性同样成立，见 `evidence/d3_wave2_calibration_20260925/10_verify_d2_539.json`。

同时 B3 独立复核了 D3 Wave2 的 train↔val 关系：**`LOOKUP_SHORTCUT_PRESENT`**（val 的指令文本与
场景 id 100% 出现在 train，查表即可复现全部 56 例 teacher 计划）。这只是输入集的性质,
**不影响**上面的量化一致性读数（后者比的是同一输入下浮点与定点的一致性）。

### 2.2 2026-09-26：第三个数据集 + 产物×数据集交叉矩阵

B1 新发 `d3_targeted_gap_strict_v1`（660 严格正样本 / 280 闭环 run，**按 run 分组划分**），
B3 独立复核该 release（**PASS**：672 个锁定文件、660 张图、561+99 行配对全部通过；注意**签名格式变了**——
新版只声明 `release_manifest_sha256`，校验器已改为按声明逐项校验并区分
claimed / not_claimed / not_recomputable，声明了就必须匹配、没声明不算失败）。

查表探针：**88/99 = 88.9% 可查表命中 → 仍然 `LOOKUP_SHORTCUT_PRESENT`**（上一版是 100%）；
"按 run 分组"改善了划分但**不等价于"按模板/指令去重"**。

用该 release 的 train 128 例校准，并把**两个产物 × 三个数据集**拼成交叉矩阵（共 849 例次逐例 `hb_verifier`）：

| 校准产物 ↓ / 评估集 → | D3 Wave2 val（56） | Gap val（99） | D2 val（539） |
|---|---:|---:|---:|
| D3 Wave2 train 64 例 | min 0.9974 | min 0.9966 | min 0.9949 |
| Gap train 128 例 | min 0.9933 | min 0.9986 | 未跑 |

**全局最低 0.993331；低于 0.99 的"头×例"观测数为 0。** 校准分布与评估分布匹配时更紧
（gap→gap 0.9986 vs gap→d3w2 0.9933），代价约 0.004–0.006。证据见
[`evidence/d3_targeted_gap_20260926/`](evidence/d3_targeted_gap_20260926/README.md)。

**为什么未校准会掉到 0.79**：不是"量化本身不行"，而是**没有校准数据时阈值退化为默认值**。
`quant_info.json` 证据：

```
未校准 : layers=59 values=40 distinct=2  min=0.731059 max=1     values==1.0: 38/40
已校准 : layers=60 values=40 distinct=21 min=0.34664  max=50    values==1.0: 4/40
```

**这条对照本身不构成精度结论**：被测权重是 A1 的随机初始化结构（`gate_status = NOT_PROVIDED`），
校准集取自仓库冻结请求集（rgb 是真实 CARLA 帧，token/target/state 来自 B1 请求），
它证明的是"**工具链 + 校准流程可用，且误差量级可被解释**"，不是"模型精度达标"。

## 3. X86 上确实能观测到的板端相关约束

`hrt_model_exec model_info` 在 X86 上就能报出运行时的对齐与 stride，这是**板端约束的早期信号**
（真值仍需板端复测）：

| 输入 | valid shape | aligned byte size | stride |
|---|---|---:|---|
| `rgb` | (1,3,224,224) | 602,112 | (602112, 200704, 896, 4) |
| `text_tokens` | (1,32) | **256**（有效 128 B） | (128, 4) |
| `targets` | (1,8,14) | **512**（有效 448 B） | (512, 64, 4) |
| `state` | (1,64) | 256 | (256, 4) |

即：小张量按 256 B 对齐分配，`targets`/`behavior_logits` 一类非 16 B 对齐的行会被补齐
（`text_tokens`、`targets` 在 infer 时被日志明确标注 `will padding`）。**下游如果按紧凑布局读
dump，会读错数据**——B3 在联调时踩过一次，见 §5。

## 4. X86 仿真**不能**测的东西（一律记 `NOT_MEASURED`）

- BPU 占用率、DDR 带宽、ION/L2M 占用、绑核与异构调度；
- 板端延迟 / FPS / 吞吐，含 `perf` 类结果的绝对值；
- 平均与峰值功耗、结温、散热与 governor 行为；
- 板端专有约束的真值（NV12 stride 64 对齐、片上缓存行为等）；
- A4 板端 Runtime 的任何真实行为。

因此 B3 交付物里**不会出现"J6P 达标"字样**：没有完整板端证据链时报告名只会是
`j6p_unverified_report.md`，`claim_scope` 只降不升（见 `README.md` 第 10.2 节）。

## 5. 复现要点（踩过的坑）

1. **平台必须显式指定**：X86 运行时默认平台是 `nash-e`，加载 `nash-p`（J6P）产物会报
   `Model march incompatible! model march: nash-p, platform march: nash-e`。
   设 `HB_UCP_SIM_PLATFORM_TYPE=nash-p` 后 `model_info` / `infer` 正常。
2. **不要用 `--fast-perf` 做接口对照**：它会按 NV12 图像输入重建模型，产物输入变成
   `rgb_y`/`rgb_uv`，与我们的 4 输入 featuremap 模型对不上；要对照请用验证模式产物或自写 config。
3. **读 dump 必须按 stride 去填充**：行 pitch 取 `stride[-2]`（不是元素 stride `stride[-1]`），
   `behavior_logits`(14→16)、`target_pointer_logits`(9→16)、`target_lane_logits`(6→8) 三头
   不去填充会得到 0.1–0.5 的假低相似度。
4. `hb_verifier` 要按 `input_names` 顺序传 **4 个文件**；传目录会报 "requires 4 input files"，
   `onnx↔hbm` 组合当前不支持（只能 `onnx↔bc`）。
5. 容器重建后 `cmake` 需要重装（`pip install cmake`），`hrt_model_exec` 的 X86 产物也要重编。

## 6. 复现命令（容器内）

```bash
# 0) 准备：case 输入 → .bin；校准集
python3 /work/x86_sim/make_bins.py /work/dumps/ACC_A01_lead_brake_0000 /work/x86_sim/bins
python3 /work/x86_sim/build_cal_dirs.py /work/cal_dumps /work/cal 30

# 1) 未校准编译（对照）        2) 带校准 PTQ 编译
hb_compile --model student_v0_fp32.onnx --march nash-p
hb_compile -c /work/x86_sim/cal_config.yaml

# 3) 一致性：onnx ↔ bc
hb_verifier -m student_v0_fp32.onnx,<bc> -i rgb.npy,text_tokens.npy,targets.npy,state.npy

# 4) X86 仿真推理 + dump 对照（需 HB_UCP_SIM_PLATFORM_TYPE=nash-p）
bash /work/x86_sim/run_x86_sim.sh              # 未校准产物
bash /work/x86_sim/run_calibrated_infer.sh     # 校准产物
```

完整脚本：`challenge/hil/harness/x86_sim/`（含 `cal_config.yaml`）。

## 7. 与板端的关系

本轮结论**只覆盖"PC 端可离线完成的部分"**。等到有 J6P（或等价的云板卡）时，
需要原样重跑一遍并额外补齐：BPU/DDR/ION 遥测、绑核与调度、板端延迟与 FPS、
功耗与结温、≥30 分钟板端长稳、以及交付配置下的多轮重复。
这些项目前在 B3 交付物里统一标 `NOT_MEASURED`，不作为本轮交付的阻塞项。
