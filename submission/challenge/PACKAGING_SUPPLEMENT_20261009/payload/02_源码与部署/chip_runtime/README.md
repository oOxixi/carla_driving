# nash-p CPU/BPU SDK 推理交接工程

本目录是 GitHub 发布的源码 overlay，必须先将 `payload/` 内文件按相对路径覆盖到**完整交接材料根目录**。相邻 `02_源码与部署/source` 的原预处理/Adapter、`05_B3性能与评测` 的 HBM/BC 及参考报告均不在此次源码发布中。仅克隆补丁不能独立运行。发布保留 `validation_case_input/request.json`，按要求排除四个 `.f32` 二进制；本机原校验记录保留，可用完整材料重新执行 `--prepare` 生成张量。

本目录把现有 CPU 预处理和 ManeuverPlan 解码接到地平线 J6 的真实 hbDNN/UCP SDK。代码已写好；本次机器没有可用 J6 板卡、OE SDK 头文件/动态库与 Arm 交叉编译器，**没有完成 SDK 编译、HBM 外部张量属性读取或实板运行**。没有使用模拟 SDK、虚构输出或 ONNX CPU 回退。Python 语法、真实请求的 CPU 张量导出已在本机校验；记录见 `validation.json`。

模型使用交接包已有的 `05_B3性能与评测/03_BPU工具原报告/student_v0_v3.hbm`；`.bc` 是参考中间产物，不交给 hbDNN 加载。编译报告记录目标 nash-p、HBDK 4.11.11、BPU 单核，OE 3.9.1、horizon_tc_ui 3.5.16 作为构建基线。HBM 文件指纹见 `model_identity.json`。报告中的性能估算不等同于本工程实板成绩。

## 实际调用链与支持范围

`ModelRequest JSONL → 原 StudentPreprocessor（CPU）→ 四个 float32 特征张量 → hbDNN/UCP（BPU）→ 十个有效输出张量 → 原 StudentPlanAdapter（CPU）→ ManeuverPlan V2 JSONL`。

预处理直接导入相邻 `../source/challenge/student/preprocess.py`，解码直接导入 `../source/challenge/planner/student_adapter.py`。文字编码、图像 letterbox/ImageNet 归一化、缺图补零、目标特征、约束掩码、必须停车、目标引用及模型输出语义保留原实现。请求和规划 schema 位于 `../source/interfaces/`。请求内 `rgb_ref` 按 Python 进程工作目录解析，与现有运行时一致。

| 输入名 | shape | SDK 外部元素要求 |
|---|---|---|
| rgb | 1×3×224×224 | float32 / NONE |
| text_tokens | 1×32 | float32 / NONE |
| targets | 1×8×14 | float32 / NONE |
| state | 1×64 | float32 / NONE |

输出 shape 在 `student_board.py:OUTPUTS` 和 C++ `kOutputs` 中固定为原十头契约。HBM 实际 tensor name、rank、shape、type、quantiType、stride、alignedByteSize 都在初始化时由 SDK 获取并检查；按名字绑定，拒绝未知/重复名字。桥接仅支持固定 batch=1、DDR featuremap、**外部 float32 / NONE**、有效正 stride。模型内部 INT8 运算与外部 float32 IO 是不同概念；本次未读取 HBM 的真实外部 IO，不能据此断言它一定兼容。如 `--describe` 报外部类型或 shape 不匹配，必须停止，不能将 INT8 数据直接按 float32 解读。本工程暂不实现外部整数张量量化、NV12/pyramid/resizer 或动态 shape；需采用保留 float32 外部边界的模型编译配置，或针对实测属性实现并核对量化路径。

SDK 工程通过 `hbDNNInitializeFromFiles` 常驻加载 HBM、`hbDNNGetModelNameList/GetModelHandle` 选择单模型；多模型 HBM 必须用 `--model-name` 指定。使用 `hbUCPMallocCached` 按 `alignedByteSize` 分配单个 `sysMem`。输入先清零 padding，再将紧凑张量每个有效元素按 SDK **字节 stride** 复制；输入写完后 `HB_SYS_MEM_CACHE_CLEAN`。`hbDNNInferV2` 创建任务、`hbUCPSubmitTask` 以 `HB_UCP_BPU_CORE_ANY` 提交、`hbUCPWaitTaskDone(task,0)` 等待完成，再释放 task。输出读取前执行 `HB_SYS_MEM_CACHE_INVALIDATE`，按有效 shape 和 stride 去除 padding，写出紧凑 little-endian f32。错误直接退出，模型与分配内存正常路径/异常路径均释放。

单进程每次只处理一个在途请求，BPU 任意核由 UCP 调度；相同 HBM 与 tensor 缓冲区驻留复用，不并发覆盖。等待参数 0 保证不在任务仍运行时复用/释放 DMA 内存；当前实现未添加任务 deadline、优先级或实时抢占策略。文件桥接用于可复现交接，含磁盘 IO 开销。`--metrics` 向 stderr 写 `model_only_ms`（C++ InferV2 开始至 WaitTaskDone 返回）与 `planner_e2e_ms`（Python 收到请求至解码完成），两者不混用。`--trace` 使用 Python 单一时钟记录八阶段，inference 段包括进程通信与文件传输；不得把它当 model-only 延迟。

## 构建与板端启动

在 Ubuntu/OE 开发环境中，使用 **OE 3.9.1 同包** 的 SDK、Arm GNU Toolchain 12.2.Rel1 与匹配的板端 BSP：

```bash
cd /path/to/交接包/02_源码与部署/chip_runtime
export OE_DIR=/path/to/horizon_j6_open_explorer_v3.9.1
export ARM_TOOLCHAIN_BIN=/path/to/arm-gnu-toolchain-12.2.rel1-x86_64-aarch64-none-linux-gnu/bin
bash build.sh
```

CMake 必须找到 `samples/ucp_tutorial/deps_aarch64/ucp/include/hobot/dnn/hb_dnn.h`、`hobot/hb_ucp.h`、`hobot/hb_ucp_sys.h`，链接同包 `libdnn.so` 与 `libhbucp.so`。缺文件直接失败，不替换成空壳头文件。将交接包相关目录和编译出的 `build_arm/student_hbdnn` 传到板端；将同 BSP/OE 所需动态库及其依赖放入 `chip_runtime/lib`，用 `ldd build_arm/student_hbdnn` 检查。原工程依赖文件不会由本目录修改。

若板端具备 Python 3.10+、aarch64 NumPy/PyTorch/Pillow，可直接运行全链路：

```bash
python3 -m pip install -r requirements.txt
export LD_LIBRARY_PATH="$PWD/lib:${LD_LIBRARY_PATH:-}"
python3 student_board.py --worker build_arm/student_hbdnn \
  --model '../../05_B3性能与评测/03_BPU工具原报告/student_v0_v3.hbm' --describe
bash launch_board.sh < requests.jsonl > plans.jsonl 2> runtime_metrics.log
# 加入八阶段trace（JSON计划增加trace字段）
bash launch_board.sh --trace < requests.jsonl > plans_with_trace.jsonl 2> runtime_metrics.log
```

`--describe` 真实加载 SDK/HBM 并输出各 tensor 的 shape/stride/aligned size。Python 额外输出模型 SHA256 和交接基线版本；这些版本是配置记录，不是从板端 SDK 查询得到。先确认该命令成功再推理。默认输出 stdout 只有每行一个 ManeuverPlan；日志、错误和指标走 stderr。板端没有 PyTorch 时可采用下述分段流程，BPU 核心只依赖 C++ SDK。

## 分段离线复现：PC CPU → 板端 BPU → PC Adapter

1. PC 上从同包 source 使用真实示例请求导出四个张量：

```bash
python3 student_board.py --prepare ../source/interfaces/examples/model_request.json --tensor-dir case_input
```

输出 `rgb.f32`、`text_tokens.f32`、`targets.f32`、`state.f32` 和原始 `request.json`。格式是 little-endian float32、C contiguous，无文件头、无 padding；分别 602112、128、448、256 字节。保留真实图像引用时，应先准备可读取的 RGB 图片；原示例不存在的图片按原预处理补零。

2. 把 `case_input` 和 HBM 复制到板端，运行一次真实 SDK 推理（路径不能含 tab/换行）：

```bash
export LD_LIBRARY_PATH="$PWD/lib:${LD_LIBRARY_PATH:-}"
./build_arm/student_hbdnn student_v0_v3.hbm --describe > sdk_tensors.json
printf 'RUN\t%s\t%s\nQUIT\n' "$PWD/case_input" "$PWD/case_output" | \
  ./build_arm/student_hbdnn student_v0_v3.hbm --worker > sdk_run.log
```

worker 首行 `READY`，成功请求返回 `OK<TAB>infer_start_ns<TAB>infer_end_ns`；`case_output` 含十个按输出名命名的 `.f32`。`OK` 仅在 SDK 成功、缓存同步和所有输出落盘后返回。数值为 C++ steady_clock 时间，仅使用差值。

3. 把 `case_output` 取回 PC，调用既有解码器：

```bash
python3 student_board.py --decode case_input/request.json --tensor-dir case_output > maneuver_plan.json
```

全链路实板验证需保留 `sdk_tensors.json`、`sdk_run.log`、十个真实输出和最终计划，再按已有 schema 校验。这里提供具体工程和运行命令；尚未生成这些板端证据，因此不声称 A4 实板部署验收已通过。

## API 核对来源

仅参考地平线官方手册，2026-10-08 核对。C++ API 路径/链接库、缓存、任务生命周期与官方 J6 UCP 文档保持一致：

- [模型推理应用开发指导](https://doc.oe.horizon.auto/3.8.1/guide/model_deployment/board_deployment/runtime_dev.html)
- [基础示例：padding/quanti/sys_mem](https://doc.oe.horizon.auto/en/guide/model_deployment/board_deployment/basic_sample.html)
- [hbDNNInferV2](https://doc.oe.horizon.auto/en/guide/api_reference/ucp_api_reference_all/bpu_sdk_api_reference/function_interface/model_inference.html)
- [RGB 模型板端构建、头文件和库目录](https://doc.oe.horizon.auto/en/guide/samples/model_deployment_guidance_examples/rgb_resnet18_deployment_guidance.html)
- [HBM tensor model_info](https://doc.oe.horizon.auto/en/guide/tools_guide/dnn_tools/hrt_model_exec/model_info.html)
- [板端延迟统计口径](https://doc.oe.horizon.auto/en/guide/model_deployment/board_evaluation.html)

官方公开手册存在不同版本路径，最终函数签名以实际 OE 3.9.1 包头文件为准；本次缺少该包，SDK 编译尚未核验。
