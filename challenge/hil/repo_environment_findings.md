# B3 验证过程中发现的仓库环境问题

> 记录人：B3（独立实测）　核对版本：`challenge` @ `64577ea0`　日期：2026-09-18
>
> 按团队约定，B3 **不修改已有文件**。本文件只记录现象、证据与建议修法，是否修复由
> 仓库维护者决定；每一条都附带 B3 的实际绕行方式，便于他人复现。

## F1. `scripts/run_scenario_runner.ps1` 的 PYTHONPATH 指向错误层级

**现象**：按该脚本运行 ScenarioRunner 会在 import 阶段直接失败。

```
ModuleNotFoundError: No module named 'agents'
```

**根因**：第 15 行

```powershell
$env:PYTHONPATH = "$repoRoot\CARLA_0.9.16\PythonAPI;$ScenarioRoot;$repoRoot"
```

CARLA 的 `agents` 包实际位于 `PythonAPI\carla\agents\`，脚本却指向它的**父目录**。

**证据**（同一 venv、同一份 ScenarioRunner，仅改 PYTHONPATH）：

| PYTHONPATH | `import carla` | `import agents` |
|---|---|---|
| `<CARLA>\PythonAPI`（脚本现状） | 通过 | 失败：`ModuleNotFoundError` |
| `<CARLA>\PythonAPI\carla` | 通过 | 通过 |

**影响范围**：仅限该脚本（手工入口）。它被 `README.md:146` 引用，但**没有任何自动流程
调用它**；主流程 `scripts/run_official_scenes.ps1` 与 Linux 的 `.sh` 脚本走的是
`python -m integration.carla_runner`，那条路径不 import `agents`/`srunner`，因此不受影响
（已用 S01 场景实测通过，见 `evidence/carla_smoke_20260918/`）。

**失败模式**：fail-fast、非零退出、错误信息明确，**不会产生静默错误数据**。

**建议修法**（一行）：

```powershell
# 现状（会导致 agents 找不到）
$env:PYTHONPATH = "$repoRoot\CARLA_0.9.16\PythonAPI;$ScenarioRoot;$repoRoot"

# 建议（指向包含 agents 的那一层）
$env:PYTHONPATH = "$repoRoot\CARLA_0.9.16\PythonAPI\carla;$ScenarioRoot;$repoRoot"
```

**B3 绕行**：直接调用 `external/scenario_runner/scenario_runner.py`，自行设置正确的
`PYTHONPATH`；或改用 `integration.carla_runner`（主流程路径）。

## F2. ScenarioRunner 钉死的 `numpy==1.24.4` 无法在 Python 3.12 上安装

**现象**：

```
Collecting numpy==1.24.4 (from -r external/scenario_runner/requirements.txt (line 2))
  Getting requirements to build wheel: error
  AttributeError: module 'pkgutil' has no attribute 'ImpImporter'
```

**根因**：numpy 1.24 早于 Python 3.12（1.26 才支持），只能源码构建，而构建在 3.12 上失败。
其余 6 个钉死版本（`py-trees`、`Shapely`、`xmlschema`、`opencv-python`、`antlr4`、
`networkx`）都可用。

**影响范围**：任何想按 ScenarioRunner 官方 `requirements.txt` 安装的环境。它是外部仓库
的约束，不是本仓库的问题，但会影响复现步骤。

**B3 绕行**：在独立 venv 中用 `numpy==1.26.4` 替代，并把 `contourpy` 降到 `1.3.3`
以避免 numpy 2.x ABI 冲突（`opencv-python==4.7.0.72` 是按 numpy 1.x 编译的，
与 numpy 2.x 不兼容，会报 `numpy.core.multiarray failed to import`）。

## F3. CARLA 路径假设与本机实际路径不一致

**现象**：`docs/setup/CARLA.md` 写 `D:\CARLA_0.9.16\CarlaUE4.exe`，
`scripts/run_scenario_runner.ps1` 写 `$repoRoot\CARLA_0.9.16\PythonAPI`，
两者都不存在于本机；实际 CARLA 安装在 `D:\CARLA_Latest`。

**影响范围**：所有需要 CARLA Python API 的脚本（主流程 `integration.carla_runner`
本身只 import `carla`，因此只要解释器能 import carla 就不受影响）。

**B3 绕行**：在仓库根建立 junction，使脚本预期的路径可用（`CARLA_0.9.16/` 已被
`.gitignore` 覆盖，对版本库零改动）：

```powershell
New-Item -ItemType Junction -Path "<repo>\CARLA_0.9.16" -Target "D:\CARLA_Latest"
```

## F4. `run_scenario_runner.ps1` 使用 PATH 上的 `python`

**现象**：脚本用 `$pythonExe = (Get-Command python -ErrorAction Stop).Source`，本机解析到
**Python 3.10**，而 CARLA 0.9.16 的 wheel 是 **cp312**，3.10 下没有 `carla` 模块。

对比：`scripts/run_official_scenes.ps1` 会先尝试 `py -3.12` 并校验版本，做法更稳。

**影响范围**：仅该脚本。除非用户的 `python` 恰好指向装了 carla 的解释器，否则也会失败
（即使修好 F1）。

**B3 绕行**：显式使用 `py -3.12`（本机已装 `carla 0.9.16`），或在 venv 中激活后调用。

## F5. 接入 Qwen 时 `--realtime` 不可省，否则请求会因 deadline 过期被拒

**现象**：不带 `--realtime` 跑带 Qwen 的 CARLA 闭环时，Qwen 请求失败、车辆全程保持 HOLD、
场景判定 FAILED。

**证据**（同一条命令，仅差 `--realtime` 一个参数）：

| 运行 | 服务端日志 | runner 日志 | 场景 |
|---|---|---|---|
| 不加 `--realtime` | `POST /infer → 408` | `TIMED_OUT` / `QWEN_TIMEOUT` | FAILED（`target_speed_kph`） |
| 加 `--realtime` | `POST /infer → 200` | `SLOW_READY` → `PLAN_COMPLETE` | **SUCCEEDED 25/25** |

**根因**：服务端返回的是 **408 `REQUEST_EXPIRED`**（不是 504 模型超时），即请求到达时它自己的
`deadline_ns`（提交时刻 + 300 ms）已经过期。不加 `--realtime` 时主循环满速运行抢占 GIL，
Qwen 工作线程拿不到时间片，导致 HTTP 请求发出过晚。

**影响范围**：任何手工调用 `integration.carla_runner` 并接入 Qwen 的场景。官方脚本
`scripts/run_official_scenes.ps1` 本身就带 `--realtime`，因此官方路径不受影响。

**B3 绕行**：按官方参数加 `--realtime`。附带价值：这次失败顺带验证了 **fail-closed 的真实
行为**——Qwen 超时后编排器没有放行推进，而是落到 HOLD 并保持制动（brake 0.55）。

**建议**：若希望不带 `--realtime` 也能用于快速冒烟，需要在文档里明确这一约束，或说明
`--qwen-timeout-ms` 与运行模式的关系。

## F6（信息）B3 为 CARLA 准备的环境

| 项 | 值 |
|---|---|
| venv | `D:\nana\carla_env`（Python 3.12.9，26 个包，296 MB） |
| CARLA 客户端 | `0.9.16`（用 `D:\CARLA_Latest\PythonAPI\carla\dist` 里的 cp312 wheel） |
| 关键替代 | `numpy 1.26.4`（替代钉死的 1.24.4）、`contourpy 1.3.3`、`opencv-python 4.7.0.72` |
| ScenarioRunner | `external/scenario_runner` @ `94ff3b8af752bad2b9d464ad5105868906aa34c0` |
| 依赖一致性 | `pip check` → No broken requirements found |
| 冻结清单 | `D:\nana\carla_env\requirements-frozen.txt` |

该环境与产出 B3 证据的解释器（系统 `py -3.12`）**完全隔离**：后者仍是
`numpy 2.4.6` / `torch 2.6.0+cpu` / `onnxruntime 1.27.0`，未受任何影响。

## F7. Windows 上 `shlex.split` 会吞掉 `--board-command` 的反斜杠路径

**现象**：`python -m challenge.hil.cli run --adapter board --board-command "C:\tools\python.exe -m a4_runtime --trace" ...`
在 Windows 上稳定失败，表现为 `RUNTIME_EXIT`（子进程根本没起来），而把命令换成不带路径的
`py -3.12 script.py` 又正常，容易误判成"板端 Runtime 有问题"。

**根因**：`shlex.split()` 默认 POSIX 模式，反斜杠是转义字符，`C:\tools\python.exe` 被切成
`C:toolspython.exe`。这是 B3 适配器自身的缺陷，不是被测对象的问题。

**修复**：`runtime_adapter.split_command()` 在 Windows 下改用 `shlex.split(posix=False)`
并手工去掉外层引号；POSIX 平台仍走原路径。已加单元测试。

**对 A4 的影响**：A4 的板端命令在 Linux/J6P 上不受影响；此修复只影响 B3 在 Windows 上的
预验证与冒烟。

## F8. 合规的板端 trace 曾让适配器直接抛异常

**现象**：让被测命令按 `a4_runtime_contract.md` §3 输出完整 8 点 trace（含
`input_arrival`）时，B3 的 board 适配器抛 `StageOrderError: stage already marked:
input_arrival`，运行中断；而不输出打点时反而"正常"。

**根因**：适配器在驱动子进程前先自己打了 `input_arrival`，解析出 Runtime 的打点后又逐个
`mark()`，与宿主打点冲突；`plan_ready` 同理。这是"越遵守契约越报错"的反向缺陷。

**修复**：Runtime 的自身打点优先，宿主只在 Runtime 未提供时补 `input_arrival`/`plan_ready`；
未知阶段名忽略并记入 `ignored_stages`；时间戳非单调改为抛 `AdapterError`（可读错误而不是
栈回溯）。已加 4 个单元测试，并用完整 8 点 trace 的假板端命令跑通一次 `run`，八段延时全部
由 Runtime 打点推导。

**记录**：该缺陷属于 `docs/architecture/modules/B3_HIL_J6P_INDEPENDENT_VALIDATION.md` §16
"Board adapter 覆盖不完整"一类，修复只在 `challenge/hil/` 内。

## F9. Windows PowerShell 5.1 会把无 BOM 的 UTF-8 `.ps1` 当 ANSI 解析

**现象**：B3 新写的 CARLA 入口脚本（含中文注释）用 `powershell -File` 执行时报
`Unexpected token ')'`，而同一份文件在 PowerShell 7 下语法正确（用 `Parser::ParseFile`
零错误）。

**根因**：Windows PowerShell 5.1 对**没有 BOM** 的 `.ps1` 按系统 ANSI 代码页解码，中文注释
被解成乱码字节，其中某些字节恰好破坏了引号/括号配对。这不是脚本逻辑问题，是编码问题。

**修复**：B3 的 `.ps1` 一律**只用 ASCII**（注释与提示语用英文）。Python 文件不受影响
（Python 3 源码默认 UTF-8）。

**影响范围**：任何给 5.1 用户运行的脚本。仓库已有脚本目前恰好都是 ASCII，所以此前没暴露。

## F10（B3 自身缺陷）长稳把"自己的记账"当成了"运行内存漂移"

**现象**：第一轮 30 分钟长稳（`b3-soak-20260921T120731Z-c99d80d6`）报告
`rss_drift_kib = 60595`（59.2 MiB，比例 18.6%），RSS 从 315 MiB 单调涨到 380 MiB，
而且后半段比前半段涨得更快——看起来像泄漏。

**根因**：`stability.run_soak` 把每次迭代的记录、每个延迟值、每个 RSS 采样全部留在内存里
（101,510 次迭代 → 约 40–60 MiB），直到运行结束才由 `write_soak_files` 写盘；
而"漂移"正是拿这些内存里的数值算出来的。于是**被测量的是 harness 自己的账本**，
不是被测 Runtime。

**修复**（`challenge/hil/stability.py`）：

1. 支援 `row_path`：逐次记录**边跑边写** `stability_logs/soak.jsonl`，内存只保留计数；
2. 延迟只保留有界聚合：首/末窗口各 2000 个样本 + 20000 样本蓄水池（用于整体分位，
   超出时在汇总里标 `overall_percentiles_bounded=true`）+ 精确最大值；
3. **漂移改用监控线程的 1 Hz RSS 序列**（`memory_during_soak.csv`，按时间有界），
   不再每次迭代采样；汇总新增 `memory_drift_source` 与 `memory_drift_window_samples`。

**验证**：同机同配置下 60 秒流式长稳漂移为 **266 KiB**（原方法在同等迭代量下会累计约
1.7 MiB 的账本），证明修复后测的才是运行时内存。

**影响**：2026-09-21 第一轮 30 分钟长稳的漂移数字**作废**，不得作为"漂移受控"的依据；
`soak_summary.json` 的 `drift_note` 已写明新口径。

## F11（环境前提）本机不满足官方 OE 工具链的 "原生 Ubuntu + Docker" 要求

**背景**：赛事通知要求挑战赛道统一在 J6P 上部署调试、最终以 docker 镜像提交，并指向地平线
官方文档（`doc.oe.horizon.auto`）与 OE 下载页（`oe.horizon.auto/download/oe`）。官方
"安装前准备/软件安装"给出的开发机要求是 **原生 Ubuntu 22.04 + Docker ≥20.10.10**
（GPU 版另需 NVIDIA Container Toolkit ≥1.16.2）。

**2026-09-23 对本机实测**：

| 项 | 官方要求 | 本机 | 差距 |
|---|---|---|---|
| 系统 | 原生 Ubuntu 22.04 | Windows 11（build 26200） | 不满足；WSL 未安装 |
| Docker | ≥20.10.10 | 未安装 | 不满足 |
| NVIDIA Container Toolkit | ≥1.16.2（GPU 版） | 无 | 仅 GPU 版需要 |
| GPU | CUDA 12.8、驱动 ≥550.163.01 | RTX 4060 Laptop 8 GB、驱动 580.88 | 驱动够新，显存偏小 |
| 内存 / CPU | ≥16 GB / i3 以上 | 23.7 GB / Intel 13 代 | 满足 |
| 磁盘 | — | C 32.5 GB / D 45.3 GB 可用 | 偏紧，WSL 数据盘需放 D |

**B3 的落地方案**：WSL2 + Ubuntu 22.04 + Docker + **CPU 版 OE 镜像**
（`openexplorer/ai_toolchain_ubuntu_22_j6_cpu`）——量化、编译、X86 仿真这条链不需要 GPU
直通，避开 8 GB 显存与 Container Toolkit 限制。分步命令见
`challenge/hil/pc_deployment_plan.md`。

**顺带记录**：OE 下载页需要登录（点"立即下载"提示"请先登录后再访问此页面"）；官方 **用户手册
本身公开可读**，板端评测/资源评估/X86 仿真的口径都能直接引用，不需账号。

## F12. Windows 检出会把 B1 发布包的文本哈希全部改掉（CRLF），字节级校验在本地假失败

**现象**：B1 交付 D3 Wave2 release（`challenge/dataset/releases/d3_wave2_safe_short_v1/`）后，
B3 在**本机**独立复核它的完整性：`b1_release_lock.sha256` 列的 11 个文件里 **10 个哈希不匹配**，
再加上 `B1_SIGNED_PASS.json` 里 3 个摘要，共 **13 处失败**；但 **374 张图片全部通过**。

**根因**：不是数据损坏，是**行尾转换**。本机 `core.autocrlf=true`，而仓库 `.gitattributes`
没有给 `challenge/dataset/releases/**` 固定 `eol`，所以文本文件在 Windows 检出时被改写成 CRLF；
B1 的摘要是在 **LF** 内容上计算的。把内容 CRLF→LF 归一化后，逐个哈希与 lock **完全一致**：

| 文件 | lock 中的 sha256 | LF 归一化后 |
|---|---|---|
| `README.md` | `367881f8df5d0579…` | ✅ 一致 |
| `rgb_mapping.json` | `d5c2b8dcc508b189…` | ✅ 一致 |
| `train_addition.jsonl` | `a547e379ad340503…` | ✅ 一致 |
| `val_addition.jsonl` | `59f524d2aa5fca39…` | ✅ 一致 |

（`hard_negative_addition.jsonl` 是 0 字节，原始哈希也匹配，所以归一的只有 10 个。）

**影响**：任何在 Windows 上做字节级哈希校验的消费方——B3 的发布复核、B4 的复现链、
B2 的独立验证、以及"本地校验通过再打包"的流程——**都会看到假失败**；反过来若摘要在
Windows 上生成、在 Linux 上校验，同样会假失败。图片等二进制文件不受影响。

**绕行**：校验前对文本内容做 CRLF→LF 归一。B3 已把这条固化进
`challenge/hil/harness/release_check/verify_b1_release.py`：默认 `--eol auto`（归一后比对，
并单独报出"只有归一后才匹配"的文件数），`--eol raw` 保留严格字节比对。
两种模式都跑过：`auto` = PASS / 0 失败；`raw` = FAIL / 13 失败。

**归属**：仓库级或发布级（给发布目录在 `.gitattributes` 里固定行尾，仓库里已有先例——
`CARLA-Language-Benchmark/...json text eol=crlf`、`metrics/reference_5070/** text eol=crlf`
都是为字节级校验显式 pin 的）。B3 只记录事实与绕行，不改别人的发布流程。
