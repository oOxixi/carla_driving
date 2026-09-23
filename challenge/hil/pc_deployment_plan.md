# PC 端部署作业单（地平线 OE 工具链 / J6 挑战赛道）

> 来源：地平线官方用户手册（公开可读，无需登录），2026-09-23 抓取。
> - [安装前准备](https://doc.oe.horizon.auto/guide/env_install/pre-installation_preparation.html)
> - [软件安装](https://doc.oe.horizon.auto/guide/env_install/software_installation.html)
> - [X86 仿真](https://doc.oe.horizon.auto/guide/model_compile/x86_simulation.html)
> - [板端评测](https://doc.oe.horizon.auto/guide/model_deployment/board_evaluation.html)
> - [板端资源评估](https://doc.oe.horizon.auto/guide/model_deployment/board_resource_evaluation.html)

**职责边界**：量化与编译属 A2/A4；B3 消费它们的产物做测量。本文件是 B3 为了"板卡/工具链
到位当天能直接开测"而整理的作业单，不替代 A2/A4 的部署交付。

## 1. 官方要求（原文口径）

| 项 | 要求 |
|---|---|
| 开发机系统 | **原生 Ubuntu 22.04** |
| CPU / 内存 | i3 以上 / ≥16 GB |
| GPU（GPU 版镜像） | CUDA 12.8、驱动 ≥550.163.01；推荐 3090 / 2080Ti / TITAN V / V100S / A100 |
| Docker | ≥20.10.10（建议 20.10.10） |
| NVIDIA Container Toolkit | ≥1.16.2（建议 1.17.8），仅 GPU 版需要 |
| 本地 PTQ 环境 | Ubuntu 22.04、Python 3.10、libpython3.10、python3-devel、gcc/g++ 12.2.1、graphviz |
| 本地 QAT 环境 | Ubuntu 22.04、CUDA 12.8、Python 3.10、torch 2.8.0+cu128、torchvision 0.23.0 |

镜像与启动（`{version}` 为 OE 版本号）：

```bash
# 离线镜像
docker load -i docker_openexplorer_xxx.tar.gz
# 在线：OE 包一级目录下自动拉取（CPU 版加 cpu 参数）
bash run_docker.sh data/ cpu

# CPU 镜像（做量化+编译+X86 仿真够用，不需要 GPU 直通）
docker pull openexplorer/ai_toolchain_ubuntu_22_j6_cpu:{version}
docker run -it --rm --network host \
  -v {OE包路径}:/open_explorer \
  -v ./dataset:/data/horizon_j6/data \
  openexplorer/ai_toolchain_ubuntu_22_j6_cpu:{version}

# GPU 镜像（QAT 训练需要）
docker pull openexplorer/ai_toolchain_ubuntu_22_j6_gpu:{version}
docker run -it --rm --network host --gpus all --shm-size=15g \
  -v {OE包路径}:/open_explorer -v {数据集路径}:/data/horizon_j6/data \
  openexplorer/ai_toolchain_ubuntu_22_j6_gpu:{version}
```

生成板端可执行程序用交叉编译器 `aarch64-none-linux-gnu-gcc/g++`（Arm GNU Toolchain
12.2.Rel1，随 OE 包交付）；X86 仿真程序用容器内 gcc/g++。

## 2. 本机差距（2026-09-23 实测）

| 项 | 官方要求 | 本机实测 | 结论 |
|---|---|---|---|
| 操作系统 | 原生 Ubuntu 22.04 | Windows 11（build 26200） | **不满足**；WSL 未安装 |
| Docker | ≥20.10.10 | 未安装（无 `docker` 命令、无 Docker Desktop 目录） | **不满足** |
| NVIDIA Container Toolkit | ≥1.16.2 | 无 | 仅 GPU 版需要；CPU 版可回避 |
| GPU | CUDA 12.8 驱动 ≥550.163.01 | RTX 4060 Laptop 8 GB，驱动 580.88（CUDA 13.0） | 驱动够新；**显存 8 GB 偏小**，GPU 版镜像不合适 |
| 内存 | ≥16 GB | 23.7 GB | 满足 |
| CPU | i3 以上 | Intel 13 代 | 满足 |
| 磁盘 | — | C: 32.5 GB / D: 45.3 GB 可用 | **偏紧**：OE 包 + 镜像通常几十 GB，WSL 数据盘必须放 D |

## 3. 推荐路径：WSL2 + Ubuntu 22.04 + Docker + **CPU 版镜像**

理由：本机是 Windows 笔记本（8 GB 显存），官方"原生 Ubuntu + GPU 镜像"路径不现实；而
量化→编译→X86 仿真这条链用 **CPU 版镜像**即可完成，且不需要 NVIDIA Container Toolkit。

```powershell
# 1) 管理员 PowerShell（可能需要重启）
wsl --install -d Ubuntu-22.04

# 2) 把 WSL 数据盘迁到 D（C 盘仅 32.5 GB）
wsl --export Ubuntu-22.04 D:\wsl\ubuntu2204.tar
wsl --unregister Ubuntu-22.04
wsl --import Ubuntu-22.04 D:\wsl\ubuntu2204 D:\wsl\ubuntu2204.tar
# 之后在 /etc/wsl.conf 里确认 default user，并检查 ~/.bashrc
```

```bash
# 3) WSL 内安装 Docker
sudo apt update && sudo apt install -y docker.io
sudo groupadd docker || true
sudo usermod -aG docker $USER && newgrp docker

# 4) OE 包放 D 盘，加载镜像（离线）或自动拉取（在线，CPU 版）
docker load -i /mnt/d/oe/docker_openexplorer_xxx.tar.gz
cd /mnt/d/oe/<OE包目录> && bash run_docker.sh data/ cpu

# 5) 进容器后：量化 -> 编译 -> X86 仿真
#    hrt_model_exec model_info / infer / perf；horizon_tc_ui 的 HBRuntime；hbdk API
```

## 4. 与 B3 测量口径的接口

1. **官方 Latency 定义 = B3 的 `model_only_ms`**（"输入数据准备完成 → 获得推理结果"；异步
   接口下为 `hbDNNInferV2` → `hbUCPWaitTaskDone`）。B3 的 `planner_e2e_ms`（T0→T7）是官方
   口径之外的完整链路延时，两者都要报，不能互相替代。
2. **板端资源评估**用 `hrt_ucp_monitor`（BPU/DSP 占用率、内存；默认每秒采样 500 次、每
   1000 ms 刷新），对应 B3 的 `utilization_raw.csv` 与 `memory_raw.csv` 的板端来源。
3. **板端评测**用 `hrt_model_exec`（`model_info` / `infer --enable_dump` / `perf
   --thread_num N --frame_count`）或 `hbm_infer` 的 X86+板端 RPC 模式（官方定位"更适合批量
   数据集评测"）。
4. B3 侧已有的对接点：`--adapter board` 的 CLI 契约、`contract` 的
   describe/batch/model-only 三条路径检查、`dump-tensors` 生成的固定输入张量。

## 5. 待确认事项

| 事项 | 说明 |
|---|---|
| OE 包下载 | 下载页需登录（2026-09-23 核对：应用内浏览器未登录，点"立即下载"提示"请先登录后再访问此页面"） |
| 磁盘空间 | C 盘 32.5 GB，需腾空间或把 WSL/Docker 数据放 D |
| 板卡 | 板端评测与 `hbm_infer` RPC 都需要板卡 IP；赛事通知称芯片资源仍在协调 |
| 是否改用原生 Ubuntu 机器 | 若团队有 Ubuntu 22.04 + NVIDIA GPU 的机器，可直接走官方 GPU 路径，省去 WSL 层 |

## 6. 安装进展（2026-09-23）

| 步骤 | 状态 | 事实 |
|---|---|---|
| WSL 应用 | **已完成** | 提权执行 `wsl --install --no-distribution`，安装 WSL 2.7.14.0（内核 6.18.33.2-2、WSLg 1.0.73.2） |
| `VirtualMachinePlatform` | **已启用，待重启生效** | `InstallState = 1`；安装日志明确"直到重新启动系统前更改将不会生效" |
| `Microsoft-Windows-Subsystem-Linux` | 未启用（不必要） | WSL2 走 VirtualMachinePlatform，无需 WSL1 组件 |
| 发行版 Ubuntu 22.04 | **已安装** | 重启后从 Ubuntu 官方 rootfs（`ubuntu-jammy-wsl-amd64-ubuntu22.04lts.rootfs.tar.gz`，325 MB）`wsl --import` 到 `D:\nana\wsl\ubuntu2204`；`Ubuntu 22.04.5 LTS`、内核 `6.18.33.2-microsoft-standard-WSL2`、Python 3.10.12（符合官方 PTQ 要求）；vhdx 约 1.9 GB，位于 D 盘 |
| systemd | **已启用** | `/etc/wsl.conf` 写入 `[boot] systemd=true`，`systemctl is-system-running` → `running`（systemd 249） |
| Docker | **已安装并运行** | Ubuntu 仓库包 `docker.io`，**Docker 29.1.3**（官方要求 ≥20.10.10）；`Storage Driver: overlayfs`；`Docker Root Dir: /var/lib/docker`（在 D 盘 vhdx 内）；WSL 默认分配 20 CPU / 11.54 GiB 内存 |
| OE 镜像拉取 | **受阻** | 本网络下 **Docker Hub 不可达**：`registry-1.docker.io`、`registry.hub.docker.com`、`hub.docker.com` 均超时（HTTP 000，134 s）；`archive.ubuntu.com` 正常（apt 可用）。官方在线路径 `docker pull openexplorer/ai_toolchain_ubuntu_22_j6_cpu:{version}` 因此失败 |
| 目标路径 | 已建立 | `D:\nana\wsl`（发行版）、`D:\nana\oe`（OE 包与镜像） |
| OE 包 | 未获取 | 下载页需登录；离线镜像 tarball 与 OE 包都在该页 |

**下一步的两种走法**（都需要用户侧动作）：

1. **离线镜像**（官方文档的离线路径）：在 OE 下载页取 `docker_openexplorer_*j6_cpu*.tar.gz` 与 OE 包，
   然后 `docker load -i ...`；不依赖 Docker Hub。
2. **经代理拉取**：启动代理客户端后，在 WSL 里让 Docker 走宿主机代理
   （`/etc/systemd/system/docker.service.d/http-proxy.conf` 指向宿主机 IP:端口），再
   `docker pull openexplorer/ai_toolchain_ubuntu_22_j6_cpu:{version}`。

镜像就位后即可用官方入门示例（ONNX 模型快速入门）验证工具链，再进入量化/编译/X86 仿真。

### 6.1 代理与镜像来源的实测结论（2026-09-23 晚）

| 测试 | 结果 |
|---|---|
| 宿主机代理 | Clash for Windows 运行中，`127.0.0.1:7890` 在 **Windows 侧可用** |
| WSL 用 `127.0.0.1:7890` | 不通（NAT 模式，localhost 指发行版自身） |
| WSL 用宿主 IP `172.24.32.1:7890` | 不通（Clash 仅监听 127.0.0.1，未开 Allow LAN） |
| 改 `.wslconfig` 用 `networkingMode=mirrored` | **失败**：`CreateInstance/CreateVm/ConfigureNetworking/0x8007054f`，WSL 回退到 `networkingMode None`（发行版完全没有网络接口）→ 已移除该配置，恢复 NAT；恢复后 `archive.ubuntu.com` 200 |
| 公共 Docker Hub 是否有 J6 镜像 | **没有**。`openexplorer` 命名空间仅 13 个仓库，最新为 `ai_toolchain_ubuntu_20_x5_cpu` 等 OE 2.x/X5 时代镜像，**不含 `ai_toolchain_ubuntu_22_j6_cpu/gpu`**（官方文档里的 `docker pull openexplorer/ai_toolchain_ubuntu_22_j6_cpu:{version}` 对本赛道不可用） |

**结论**：J6（OE 3.x）镜像只能从 **OE 下载页的离线镜像包**（登录后获取）导入，即
`docker load -i docker_openexplorer_*_j6_cpu*.tar.gz`。CPU 版足够完成量化/编译/X86 仿真，
且不需要 NVIDIA Container Toolkit。

**登录方式的实测**：OE 站的登录是**社区账号授权（SSO/OAuth）**，登录对话框只有两个入口
——"Horizon 您来自 地平线开发者社区，请点击授权" 与 "D-Robotics 请点击授权"。在应用内浏览器
里点 Horizon 授权会跳到 `developer.horizon.auto/info`（个人中心，说明社区登录有效），但
**登录态没有回到 OE 站**（再打开下载页仍提示"请先登录后再访问此页面"），疑似跨站 Cookie
被浏览器策略拦下。结论：**这一步需要由账号持有人在自己浏览器完成**，B3 侧的自动化只能从
"拿到文件"之后接手。

### 6.3 OE 3.9.1 资源清单与获取方式（2026-09-23 实测）

登录 OE 站后，`https://oe.horizon.auto/download/oe` 提供 3.9.1 全部 12 个文件；点每个文件的
"下载"会弹出一个对话框，里面直接给出 **wget 直链**（形如
`https://oe.horizon.auto/api/v1/downloads/<uuid>`，302 跳转到 `oss.oe.horizon.auto` 的
**限时签名地址**，无需 Cookie 即可下载）。本次需要的两个：

| 文件 | 用途 | 大小 |
|---|---|---|
| `docker_open_explorer_ubuntu_22_j6_cpu_v3.9.1.tar.gz` | 工具链集成开发环境 **CPU 版**（`docker load` 后即用） | 3.45 GB |
| `horizon_j6_open_explorer_v3.9.1-py310_20260821.tgz` | 天工开物工具链**全量开发包**（`run_docker.sh`、`package/host`、samples、交叉编译器） | 待测 |

其余 10 个（GPU 镜像、hbdk4_compiler/march 的 wheel、hbm_infer、hmct（+gpu）、
horizon_plugin_profiler/pytorch、horizon_tc_ui、文档包）按需另取；CPU 路线用不到 GPU 那两个。

下载落位：`D:\nana\oe\`（`docker load` 与 `run_docker.sh` 都从这里执行）。

### 6.4 PC 端部署完成记录（2026-09-23 22:20）

以下每一步都在本机实测通过，可作为"工具链可用"的证据（仍属 X86 预验证，不是板端结论）：

| 步骤 | 结果 |
|---|---|
| 下载 CPU 镜像 | `docker_open_explorer_ubuntu_22_j6_cpu_v3.9.1.tar.gz`，**3.455 GB**，`gzip -t` 通过 |
| 导入镜像 | `docker load` → **`openexplorer/ai_toolchain_ubuntu_22_j6_cpu:v3.9.1`**（磁盘 20.9 GB，耗时 1m45s） |
| 下载 OE 全量包 | `horizon_j6_open_explorer_v3.9.1-py310_20260821.tgz`，**2.59 GB**，`gzip -t` 通过；解包 8 分钟 |
| 启动容器 | `docker run -d ... sleep infinity`（按 `run_docker.sh` 的挂载方式：OE 包 → `/open_explorer`，数据集 → `/data/horizon_j6/data`） |
| 容器内版本 | Python 3.10.12；`hb_compile 3.5.16`、`hmct 2.8.4`、`hbdk 4.11.11`；`hb_model_info` / `hb_verifier` / `hb_analyzer` 均在 PATH |
| 示例初始化 | `samples/onnx_ptq/examples/classification/resnet50/00_init.sh` 从地平线 FTP 取到 ResNet50 ONNX + 校准集 |
| 模型验证（J6P） | `hb_compile --model resnet50.onnx --march nash-p` 通过（opset 10 → 19，optimize→calibrate→quantize） |
| 校准数据预处理 | `02_preprocess.sh` → `calibration_data_rgb/*.rgb.npy` |
| **模型编译（J6P）** | `hb_compile -c resnet50_config_j6p.yaml`（march 改为 `nash-p` 的副本）**成功**，4m58s → `resnet50_224x224_nv12.hbm`（26.3 MB，内存需求 26.35 MB），`HBDK hbm perf SUCCESS` |
| **X86 仿真推理** | `04_inference.sh quanti` 用 `resnet50_224x224_nv12_quantized_model.bc` 推理 `zebra_cls.jpg` → **top-1 `zebra`（label 340, prob 17.05）**，4s |

产物路径（容器内）：`/open_explorer/samples/onnx_ptq/examples/classification/resnet50/model_output/`
—— 含 `*.hbm`、`*_quantized_model.bc`、`*_ptq_model.onnx`、`*_quant_info.json`、`*_node_info.csv`、
profiling `*.html`。

容器仍在运行（名 `b3_oe391_cpu`），进入方式：

```powershell
wsl -d ubuntu2204 -u root -- docker exec -it b3_oe391_cpu bash -lc "source /etc/bash.bashrc; bash"
```

**磁盘提醒**：D 盘可用空间降到约 17 GB（镜像 20.9 GB + OE 包解包 ≈ 16 GB）。
两份安装包（`.tar.gz` 3.46 GB + `.tgz` 2.59 GB）在镜像已导入、包已解包后可以删除回收约 6 GB。

**尚未做的（需要外部条件）**：`05_evaluate.sh` 精度评估、`hrt_model_exec` 板端评测与
`hrt_ucp_monitor` 资源评估（需 J6P 板卡或 HiL&SiL 云板卡）、以及把 B3 自己的 Student
模型接进同一条链（需 A3 Gate 权重 → A2 量化产物）。

### 6.5 精度评估（2026-09-23 22:30）

**官方完整评估跑不了**：`05_evaluate.sh` 默认用 `common/data/imagenet/val/` + `val.txt`，
而 OE 包**没有随附 ImageNet val 集**（只有校准子集与 20 行标签文件），ImageNet 需自行到
image-net.org 注册下载。这一步的执行者应是 A2/A3（量化精度归口），B3 只做复算与核对。

**能做的替代评估**（把 `--image_path` 指向包内 `common/calibration_data/imagenet`，标签取
`common/test_data/val_piece.txt` 中在该目录里存在的条目，共 **20 张**）：

| 模型 | 输入布局 | top-1（20 张） | 耗时 |
|---|---|---|---|
| 浮点 `resnet50_224x224_nv12_original_float_model.onnx` | NCHW | **0.7500** | 4.4 s |
| 定点 `resnet50_224x224_nv12_quantized_model.bc`（X86 仿真） | NHWC | **0.7000** | 31.4 s |

差异 5 个百分点 = **1 张图**。样本量与代表性都不足（20 张、粒度 5%），而且这 20 张属于
**量化校准集**（不是独立验证集），因此这两个数字**只能说明"管线可用、量化影响可粗看"**，
不能作为精度结论，也不能进 B2 的评分表。

**下一步可做**：`hb_verifier -m <onnx>,<bc> -i <输入 dump>` 做逐张量的部署一致性检查
（X86 端即可跑，不需要板卡），这才是比 top-1 更敏感的量化影响指标。

### 6.2 官方"云上 J6 板卡"线索（可能免除实物板卡依赖）

来源：地平线开发者社区论坛帖《【征程6云上使用】已登录调度服务器，但分配板卡 10.8.0.2 SSH
连接超时》（`developer.horizon.auto/forum/13802`，2026-09-05，已解决）。

帖子把官方**云上开发板**的接入流程写得很清楚，可作为申请与使用时的核对清单：

1. 在申请页面提交使用申请，状态显示"完成账号创建"，获批**使用时段**（例：2026/09/05
   16:00–20:00）并分配**板卡 IP**（例：`10.8.0.2`；产品为天准 TADC-J6E/M）；
2. 登录 **SOCA 云平台**网页，从 *SSH access* 下载本账号 **PEM 私钥**（权限 `600`）；
3. 用网页给出的命令登录**调度服务器**（例：`52.80.174.119`）；
4. 在调度服务器内 `source /etc/environment`，再 `ssh root@<板卡IP>` 进入分配给自己的板卡；
5. 依据手册《**HiL&SiL平台使用手册-用户版本v1**》操作。

**对 B3 的意义**：板端评测（`hrt_model_exec`、`hrt_ucp_monitor`、UCP 推理）可以在**云上分配的
真实 J6 板卡**上执行，不必先有实物板卡。约束与注意事项：

- 申请与时段是**账号级**动作，必须由组员本人完成；私钥属敏感凭据，自行保管，不要提交到仓库；
- 该帖暴露的典型故障是"调度服务器 → 板卡"这一段 SSH 超时（本次已由平台修复），
  排障时先用 `ping`/`ssh -o ConnectTimeout=10 root@<板卡IP>` 区分是通道问题还是板卡未开机；
- 云上板卡的测试窗口有限，测量应一次性编排好（这正是 B3 已有 `--adapter board` 契约、
  `contract` 三条路径检查与 `dump-tensors` 的用处）。

重启后的执行顺序：

```powershell
# 1) 安装发行版（Store 版）后迁到 D
wsl --install -d Ubuntu-22.04 --no-launch
wsl --manage Ubuntu-22.04 --move D:\nana\wsl\ubuntu2204
# 或者：下载 Ubuntu 官方 WSL rootfs 后直接导入到 D，避免先占用 C 盘
# wsl --import ubuntu2204 D:\nana\wsl\ubuntu2204 <ubuntu-jammy-wsl-amd64-wsl.rootfs.tar.gz>
```
