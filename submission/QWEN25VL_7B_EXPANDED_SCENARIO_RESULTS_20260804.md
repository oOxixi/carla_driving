# Qwen2.5-VL-7B 新增指令与多场景测试总结

日期：2026-08-04

模型：Qwen2.5-VL-7B-Instruct，BF16

推理服务器：远端 NVIDIA GeForce RTX 3090 24 GB

代码基线：`94eea04 Release CARLA-Language-Benchmark v1 frozen baseline`

## 1. 结论

服务器网络问题已解决，Qwen2.5-VL-7B 已在远端 RTX 3090 上稳定启动，并完成三组测试：固定输入延迟门禁、6192 条新增指令全量测试、320 条视觉/感知扰动生产链路回归。

核心结果如下：

| 测试 | 结果 | 判定 |
|---|---:|---|
| 固定图延迟门禁，5 次预热 + 10 次测量 | P95 `96.25 ms` | 通过 300 ms 门禁 |
| 新增指令全量测试 | `5721/6192 = 92.39%` | 总体较高，但不能视为全场景通过 |
| 新增指令 20 类宏平均 | `75.23%` | 长尾类别仍有明显缺陷 |
| 新增指令严格单码输出 | `6192/6192 = 100%` | 通过 |
| 320 条非 ASR 多模态回归 | 完整契约 `320/320 = 100%` | 准确率门槛通过 |
| 320 条多图 Qwen 延迟 | P95 `416.09 ms` | 未通过 300 ms 模型门禁 |

因此，当前路线已经证明：

1. 网络和远端部署问题可以稳定解决；
2. 7B 模型能可靠输出严格动作码；
3. 普通行驶、转弯、变道、速度、停车和紧急动作分类表现很好；
4. 导航异常、缺失目标、复合指令、遮挡和确认策略仍需专项改进；
5. 现有生产适配器只有 5 种动作，而新增基准有 11 种动作，尚不能直接把全量测试结果等同于生产链路覆盖；
6. 320 条多模态回归只覆盖同一类 `SLOW_DOWN` 决策的视觉和目标绑定扰动，不是 11 种动作的真实 CARLA 闭环测试。

综合判断：服务器与测试体系已经跑通，但完整 11 动作能力尚未达到可直接部署状态。

## 2. 网络问题与解决方法

### 2.1 现象

最初通过域名连接时，SSH 在认证前被关闭：

```text
kex_exchange_identification: Connection closed by remote host
```

本地 DNS 返回 `198.18.0.0/15` 范围的地址。这是代理/TUN 常用的 fake-IP 范围，不是服务器真实公网地址。直接连接域名或 fake-IP 都会在 SSH 密钥交换阶段失败。

### 2.2 定位

排查本机历史配置后发现，之前同类问题的有效处理方式是：

- 强制 IPv4；
- 让 SSH 绑定无线物理网卡 `wlp0s20f3`，绕开代理 TUN；
- 通过独立 DoH 查询得到服务器真实 IPv4；
- 禁用本机 SSH 配置污染，直接连接真实地址。

成功连接采用的形式为：

```bash
ssh -F /dev/null -4 \
  -o BindInterface=wlp0s20f3 \
  -o ConnectTimeout=20 \
  -p 47458 root@<真实IPv4>
```

模型服务只监听远端 `127.0.0.1:8000`，本地通过 SSH 端口转发访问，没有把推理 API 暴露到公网。

### 2.3 安全处理

- 登录密码没有写入仓库、脚本、报告或结果文件；
- API 凭据没有写入本文档；
- 报告没有固化服务器真实公网 IP；
- 推理服务绑定在远端 loopback 地址。

## 3. 远端环境

远端证据采集时间：`2026-08-04T14:17:21Z`。

| 项目 | 实测值 |
|---|---|
| 操作系统 | Ubuntu 22.04 容器，Linux 5.15 |
| GPU | NVIDIA GeForce RTX 3090 |
| 显存 | 24576 MiB |
| 测试后显存占用 | 23292 MiB |
| 远端驱动 | 595.71.05 |
| Python | 3.11.14 |
| PyTorch | 2.11.0+cu130 |
| CUDA runtime | 13.0 |
| Transformers | 5.14.1 |
| vLLM | 0.26.0 |
| 模型精度 | BF16 |
| 模型目录实际大小 | 16 GB |
| 权重分片 | 5 个 safetensors 文件 |
| 模型层数 / hidden size | 28 / 3584 |

服务启动配置：

```text
host=127.0.0.1
port=8000
served_model_name=qwen2.5-vl
max_model_len=4096
gpu_memory_utilization=0.9
trust_remote_code=true
```

注意：`local-modelscope-snapshot-20260208` 是本次运行使用的本地快照标识，不是经过上游仓库核验的 commit revision。

## 4. 测试设计

### 4.1 固定图延迟门禁

使用现有生产适配器、真实 RGB、单 Token 约束输出。先预热 5 次，再测量 10 次。该测试用于快速早停，不包含正确率测试。

固定输入会受 vLLM 前缀缓存和多模态缓存影响，因此只能作为热路径门禁，不能代表混合图像生产流量。

### 4.2 6192 条新增指令全量测试

数据源：

```text
CARLA-Language-Benchmark/datasets/final_benchmark/
CARLA_language_benchmark_v1_normalized.json
```

数据包含 20 类场景、11 种期望动作。为避免修改当前生产接口，本次增加了隔离评测工具：

```text
tools/run_qwen_expanded_instruction_benchmark.py
```

评测约束：

- 模型输入只包含 `template` 和 `scene_constraints`；
- `id`、`category`、`semantic_intent`、`expected_action`、`expected_parameters`、`safety_policy` 全部对模型隐藏；
- 温度为 0；
- 最大输出 1 Token；
- 使用 A 到 K 的 11 个结构化选择；
- 并发数为 8；
- 输出每条样本的预测、置信度、Top 候选、延迟和错误状态；
- 不改动五动作生产适配器。

这项测试的准确名称是“中文指令 + 结构化场景动作分类”。它没有给模型真实 RGB，也没有启动 CARLA actor，所以 exposure、occlusion、detector_error 等类别验证的是模型对结构化事实的理解，不是实际视觉鲁棒性。

本次只评估动作类别，不评估 `expected_parameters`。例如 `unit_conversion` 的 100% 只表示模型选择了 `SET_SPEED`，不表示速度数值换算正确。

### 4.3 320 条生产链路多模态回归

场景类别共 8 类，每类 40 条：

- baseline；
- exposure_low；
- exposure_high；
- motion_blur；
- partial_occlusion；
- detector_false_positive；
- detector_miss；
- detector_bbox_shift。

链路为：

```text
冻结中文转录 -> 真实 NLU -> 真实/增强 CARLA RGB
-> 结构化原始 CARLA LiDAR 摘要 + 车辆状态
-> 真实 Qwen7B -> 严格边界 -> D 安全仲裁 -> 最终控制
```

源清单声明 10 个合成音频文件，但当前分支实际缺少全部 10 个文件，320 条数据验证错误均为 `missing audio`。由于向第三方 TTS 发送评测文本未获明确授权，未通过外部服务重新合成音频。本次新增 `--transcript-source provided` 模式，显式跳过 ASR，只使用清单中的冻结转录运行真实 NLU 和后续链路。

因此这组结果不是 ASR 证据，继承的 `audio_to_final_control` 指标名在本次运行中实际表示“provided transcript 到最终控制”。

当前 `cases_v2.jsonl` 中 seed 28/31 的文本已经是“距离约 28/26 米的行人”，与 `far_ahead` 感知关系一致；本次发现的阻塞是音频文件缺失，不是旧版“右侧相邻车道”语义冲突。

## 5. 详细结果

### 5.1 固定图延迟门禁

| 指标 | 结果 |
|---|---:|
| 测量次数 | 10 |
| mean | 94.16 ms |
| P50 | 94.99 ms |
| P95 | 96.25 ms |
| max | 96.44 ms |
| 门槛 | 300 ms |
| 判定 | PASS |

报告同时记录实际推理 GPU 为远端 RTX 3090，并单独保留本地客户端 RTX 4060 Laptop 信息，避免把客户端显卡误写成推理硬件。

### 5.2 新增指令总体结果

| 指标 | 结果 |
|---|---:|
| 总样本 | 6192 |
| 成功解析 | 6192 |
| 正确 | 5721 |
| 错误 | 471 |
| 严格输出率 | 100% |
| 动作准确率 | 92.39% |
| 20 类宏平均准确率 | 75.23% |
| wall time | 125.40 s |
| 吞吐 | 49.38 条/s |
| 请求 mean | 160.70 ms |
| 请求 P50 | 155.58 ms |
| 请求 P95 | 231.40 ms |
| 请求 P99 | 272.20 ms |
| 请求 max | 501.38 ms |

6192 个任务一次性加入本地异步队列，因此结果文件中的 `queue_wait_ms` 包含整批调度积压，P95 约 118 秒；它不是在线单请求延迟，不能用于实时控制判断。实时参考应使用固定门禁或顺序混合图测试。

### 5.3 按场景类别

| 类别 | 正确/总数 | 准确率 |
|---|---:|---:|
| navigation_error | 7/45 | 15.56% |
| missing_target | 18/100 | 18.00% |
| compound | 23/65 | 35.38% |
| occlusion | 27/72 | 37.50% |
| dense_target | 33/65 | 50.77% |
| safety_conflict | 36/60 | 60.00% |
| detector_error | 44/72 | 61.11% |
| following | 353/500 | 70.60% |
| exposure | 58/80 | 72.50% |
| weather_failure | 50/60 | 83.33% |
| ordinary_synonym | 461/462 | 99.78% |
| ambiguous_target | 100/100 | 100% |
| emergency | 750/750 | 100% |
| lane_change | 750/750 | 100% |
| negation | 6/6 | 100% |
| ordinary_instruction | 1500/1500 | 100% |
| parking | 250/250 | 100% |
| speed_control | 500/500 | 100% |
| turning | 750/750 | 100% |
| unit_conversion | 5/5 | 100%* |

`*` 未验证数值参数。

总体准确率被 1500 条 ordinary_instruction 等大类明显拉高，所以宏平均 75.23% 更能反映长尾场景状况。

### 5.4 按动作

| 期望动作 | 正确/总数 | 准确率 |
|---|---:|---:|
| REQUEST_CONFIRMATION | 161/288 | 55.90% |
| STOP | 292/326 | 89.57% |
| KEEP_LANE | 2383/2623 | 90.85% |
| AVOID_OBJECT | 252/276 | 91.30% |
| SET_SPEED | 592/619 | 95.64% |
| TURN_LEFT | 380/387 | 98.19% |
| TURN_RIGHT | 377/383 | 98.43% |
| CHANGE_LANE_LEFT | 377/379 | 99.47% |
| CHANGE_LANE_RIGHT | 380/382 | 99.48% |
| EMERGENCY_STOP | 525/527 | 99.62% |
| START | 2/2 | 100% |

按安全策略：

| 策略 | 正确/总数 | 准确率 |
|---|---:|---:|
| confirmation | 185/343 | 53.94% |
| normal | 5000/5289 | 94.54% |
| override | 536/560 | 95.71% |

最需要优先修复的是确认策略，而不是普通动作识别。

### 5.5 主要错误模式

1. `KEEP_LANE -> SET_SPEED` 共 169 条，其中普通跟车 147 条。模型把“根据前车速度跟随”理解为速度控制，而数据标签统一定义为保持车道。
2. missing_target 有 82/100 错误。虽然场景明确包含 `target_available=false`，模型仍经常输出 STOP、EMERGENCY_STOP、SET_SPEED 或 KEEP_LANE，而不是 REQUEST_CONFIRMATION。
3. navigation_error 只有 7/45 正确。结构化导航冲突与期望标签之间的规则不够清晰，模型经常选择 STOP 或 EMERGENCY_STOP。
4. compound 有 42/65 错误。模型容易选择时间顺序中的第一动作或更保守动作，与数据集的单标签选择规则不一致。
5. occlusion 有 45/72 错误。“减速接近部分遮挡目标”的期望标签常为 STOP，但模型按自然语义输出 SET_SPEED。
6. safety_conflict 中 24 条 `KEEP_LANE` 被输出成 STOP 或 EMERGENCY_STOP，模型安全行为偏保守。
7. dense_target 中“多个同类目标”经常被模型当成可继续行驶，而没有请求确认。

正确样本的平均选中 Token 置信度为约 0.785，错误样本为约 0.512。置信度具有一定区分度，可用于后续校准，但不能直接用未经验证的阈值替代安全规则。

### 5.6 数据质量观察

官方结构审计结果为：

```text
records=6192
errors=0
```

这表示 Schema 完整，不表示所有语义都无冲突。本次额外检查发现：

- 模型实际输入只有 3802 个唯一组合，2390 条是重复输入；
- 相同“指令 + 场景”输入没有发现互相冲突的期望动作；
- 只有 879 个唯一指令模板；
- 64 条指令写“红灯”，结构化场景的信号灯却为 Green，期望动作仍为 STOP；
- 部分 compound、navigation_error、occlusion 标签不完全符合自然语言直觉，需要冻结更明确的单动作标注规则；
- 后续训练/验证/测试切分必须按模型输入指纹分组，不能让重复输入跨 split 泄漏。

### 5.7 320 条多模态生产链路回归

| 指标 | 结果 |
|---|---:|
| READY | 320/320 |
| 真实 ASR | 未运行 |
| NLU valid | 320/320 |
| 可回答目标样本 | 280 |
| 动作 + 目标联合准确率 | 280/280 |
| 确定性目标绑定 | 280/280 |
| 目标缺失安全闭锁 | 40/40 |
| 完整契约 | 320/320 |
| 准确率门槛 | PASS |

8 个类别均为 40/40 完整契约通过。

Qwen 原始动作码 320 条全部为 `C=SLOW_DOWN`。目标 ID 不由模型生成，而是严格适配器根据语音语义和感知候选确定性绑定：280 条为 `CORRECTED_UNIQUE`，40 条为 `ABSENT_FAIL_CLOSED`。因此这组 100% 结果主要证明目标绑定和安全闭锁，不证明多动作分类能力。

多图延迟：

| 阶段 | mean | P50 | P95 | P99 | max |
|---|---:|---:|---:|---:|---:|
| provided transcript + NLU | 0.12 ms | 0.10 ms | 0.15 ms | 0.16 ms | 3.73 ms |
| Qwen + 图像处理/边界 | 298.49 ms | 348.43 ms | 416.09 ms | 451.14 ms | 651.63 ms |
| Qwen 后控制/安全 | 0.09 ms | 0.09 ms | 0.11 ms | 0.13 ms | 0.14 ms |
| provided transcript 到最终控制 | 298.70 ms | 348.66 ms | 416.32 ms | 451.30 ms | 655.47 ms |

准确率门槛通过，但多图 Qwen P95 超过 300 ms，延迟门槛不通过。

## 6. 生产接口覆盖缺口

当前生产适配器的动作码只有：

```text
A START
B STOP
C SLOW_DOWN
D SET_SPEED
E EMERGENCY_STOP
```

新增基准要求 11 种动作：

```text
START
STOP
KEEP_LANE
SET_SPEED
EMERGENCY_STOP
TURN_LEFT
TURN_RIGHT
CHANGE_LANE_LEFT
CHANGE_LANE_RIGHT
AVOID_OBJECT
REQUEST_CONFIRMATION
```

因此 TURN、CHANGE_LANE、AVOID_OBJECT、REQUEST_CONFIRMATION 等结果目前只存在于隔离评测工具，尚未进入生产控制契约。不能把 6192 条测试的 92.39% 写成生产链路 11 动作覆盖率。

## 7. 建议的后续修复顺序

### P0：上线前必须处理

1. 冻结统一的 11 动作生产 Schema，或明确建立 11 动作到现有控制动作的安全映射；同时补齐控制层执行和安全仲裁测试。
2. 对 `target_available=false`、`ambiguity_reason`、传感器不可用等事实增加确定性确认/闭锁规则，不只依赖模型分类。
3. 明确 compound 的单标签规则：选择第一动作、最终动作、主动作还是最高安全优先级动作，数据生成器和提示词必须一致。
4. 重审 navigation_error、occlusion、safety_conflict 标签，修复信号灯文本和结构化状态冲突。
5. 增加参数评测，至少覆盖目标速度、单位换算、目标车道、距离和目标 ID；当前动作码测试无法验证这些值。
6. 按“指令 + 场景”指纹去重或分组切分，避免 2390 条重复输入造成评测膨胀或数据泄漏。
7. 补齐 10 个音频文件或使用获授权的本地/外部 TTS 重新生成，之后再运行真实 ASR 全链测试。

### P1：性能与鲁棒性

1. 用顺序混合图像重新做 7B 模型延迟门禁，目标 P95 不超过 300 ms；固定图 96 ms 不能替代多图 416 ms。
2. 分析 256×256 montage、提示长度、视觉 Token 和 vLLM 多模态缓存策略，比较 7B 与已验证 3B 路线。
3. 对错误样本做置信度校准，评估低置信度转 REQUEST_CONFIRMATION 的准确率、召回率和误闭锁代价。
4. 为 20 个类别各建立真实 CARLA RGB/传感器场景，而不是只使用结构化场景描述。
5. 在真实 CARLA actor 上分别执行转弯、变道、绕障、确认和紧急动作，记录碰撞、越线、控制延迟与完成率。

## 8. 可复现命令

以下命令省略真实 API 凭据。

新增指令全量评测：

```bash
QWEN_API_KEY='<secret>' conda run --no-capture-output -n carla312 \
  python -m tools.run_qwen_expanded_instruction_benchmark \
  --base-url http://127.0.0.1:18000/v1 \
  --model qwen2.5-vl \
  --concurrency 8 \
  --server-gpu-name 'NVIDIA GeForce RTX 3090' \
  --server-gpu-memory-mib 24576 \
  --output artifacts/B_role_validation/qwen25vl_7b_expanded_full_6192_20260804.json
```

非 ASR 多模态生产链路回归：

```bash
QWEN_API_KEY='<secret>' conda run --no-capture-output -n carla312 \
  python -m tools.run_four_modal_full_chain \
  artifacts/four_modal_0728/stress_set \
  --cases-file cases_v2.jsonl \
  --transcript-source provided \
  --base-url http://127.0.0.1:18000/v1 \
  --model qwen2.5-vl \
  --output artifacts/B_role_validation/qwen25vl_7b_multimodal_provided_transcript_320_20260804.json
```

定向代码测试：

```bash
conda run --no-capture-output -n carla312 python -m pytest -q \
  --confcutdir=. \
  integration/tests/test_four_modal_provided_transcript.py \
  integration/tests/test_qwen_expanded_instruction_benchmark.py \
  integration/tests/test_qwen_four_modal_stress_set.py \
  integration/tests/test_qwen_latency_gate.py
```

结果：`9 passed`。

## 9. 证据文件

- `artifacts/B_role_validation/qwen25vl_7b_3090_latency_gate_20260804.json`
- `artifacts/B_role_validation/qwen25vl_7b_expanded_full_6192_20260804.json`
- `artifacts/B_role_validation/qwen25vl_7b_expanded_full_6192_20260804.records.jsonl`
- `artifacts/B_role_validation/qwen25vl_7b_expanded_smoke_20260804.json`
- `artifacts/B_role_validation/qwen25vl_7b_multimodal_provided_transcript_320_20260804.json`
- `artifacts/B_role_validation/four_modal_source_validation_20260804.json`

主要证据 SHA-256：

| 文件 | SHA-256 |
|---|---|
| 固定图延迟门禁 | `68c23e182a47d67b1a7da4e712e2cb43e12fe27a37543ce291e4d23075b80def` |
| 6192 条汇总 | `ceb8b370558da4dc987270d0d4a83d450265b196b9fca052b0508c138c7bd36b` |
| 6192 条逐条记录 | `867dcaaa0fb2b3517efad0f256f47917bd05bcd23847c603d8fbf4e181837f1e` |
| 320 条非 ASR 多模态报告 | `e77c832f882100d19eabeb80396e7b00bca297ca23ad43e14b3f9bf1e5770b54` |

数据集 SHA-256：

```text
d05feb10cf4019dc26ff98a1821f09d304f4612f44006cedb2a69e91babf5213
```
