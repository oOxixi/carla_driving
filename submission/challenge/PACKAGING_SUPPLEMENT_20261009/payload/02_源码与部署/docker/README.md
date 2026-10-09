# Student X86 Docker 一键构建与导出

2026-10-09 已恢复完整源码的场景文件，并补 Student 健康接口与独立 CPU controller 构建/compose 入口；见相邻 `../部署补齐说明_20261009.md`。Student 与 controller、GPU语音的依赖不混装。build 中的 `check_deployment.py` 检查场景和实际 imports，仍不跑模型评测。

本目录是 GitHub 发布的源码 overlay，必须先将 `payload/` 内文件按相对路径覆盖到**完整交接材料根目录**（该目录同时具有 `02_源码与部署/source`、`scripts` 与 `03_训练与模型`）。仅克隆这份补丁不能独立构建；本次发布不含原模型、镜像、数据或已有源码副本。从完整材料根目录执行下述命令，基础镜像和三份 ONNX 模型仍由完整材料提供。

Dockerfile 已补齐直接依赖约束与实际版本检查，采用官方 `openexplorer/ai_toolchain_ubuntu_22_j6_cpu:v3.9.1`。当前机器仍无可用 Docker CLI/服务和 WSL；后续通过 Linux runner 实际构建自建运行时并本地附加模型生成 tar，详见 `本次Docker交付_20261009.md`。官方 OE base 构建和最终 Linux 加载/推理尚未完成。脚本已完成，无需团队成员再写工程；只需在已有 Linux Docker 环境或启用 Linux 容器的 Windows Docker 环境运行。

B3 实测基线为 Python 3.10.12、torch 2.8.0+cpu、onnxruntime 1.19.0、NumPy 1.23.0、Pillow 9.3.0、jsonschema 4.25.1、psutil 7.2.1。Docker 构建首先验证前五项已在官方基础镜像匹配，错误即停止，避免隐式升级模型运行库；随后以 constraints 安装两个精确版本 extras 和 PyYAML。保留 NumPy 1.23.0、Pillow 9.3.0，不沿用 source 总开发 requirements 的 Pillow>=10 或 ORT>=1.20；该开发文件不是本运行镜像的安装输入。

PyYAML 原始环境没有确切版本记录，因此仅约束 `>=6,<7`。`requirements-runtime-lock.txt` 是**直接依赖约束**，不是带所有传递依赖哈希的完整锁；最终实际传递依赖由每次构建的 `runtime_freeze.txt` 保存。extras 安装使用 `--only-binary=:all:`，缺 wheel 或出现依赖冲突会停止，不悄悄源码构建。核心库复用、检查官方 base 的既有版本，不重新安装 NumPy。NumPy 1.23.0 [官方发布记录](https://numpy.org/news/)支持 Python 3.8–3.10；B3 原证据已记录其与 ORT 1.19.0 共存，本次未重新验证镜像。

先将官方 v3.9.1 CPU 基础镜像导入 Docker。脚本先检查 Docker 服务与**本地基础镜像**，记录其真实 image ID，以原官方 tag 构建。脚本不主动拉取基础镜像；缺少的小型 extras 仍可能需要网络。Dockerfile 只复制三份已确认 ONNX 模型，路径保持与 launch_student.py 一致；根 `.dockerignore` 排除训练权重、评测大目录和导出 tar。

Windows PowerShell（脚本含 UTF-8 BOM，兼容 5.1 中文路径）：

```powershell
& '.\02_源码与部署\docker\build_and_export.ps1'
```

Linux/WSL 的已有 Docker 环境：

```bash
bash '02_源码与部署/docker/build_and_export.sh'
```

任一 build/run/inspect/save 步骤失败立即停止；默认镜像名 `challenge-student-x86:20261008`，每次导出进入 `02_源码与部署/docker/exports/<时间>/`。完整成功才生成 `image_manifest.json`，记录 base/image ID、可用 RepoDigests、tar 大小和 SHA256。未推送 registry 的本地镜像可能没有 RepoDigests，此时使用真实 image ID 与 tar SHA256，不捏造 registry digest。保留 `build.log`、`save.log`、`base_image_inspect.json`、`image_inspect.json`、`runtime_dependencies.json`、`runtime_freeze.txt`、`image_sha256.txt`。

加载导出物并启动：

```bash
docker load -i student-x86-image.tar
docker run --rm -p 8100:8100 challenge-student-x86:20261008
# 模型选项 fp32 / full_int8 / mixed_top3
docker run --rm -p 8100:8100 challenge-student-x86:20261008 \
  --mode http --variant fp32 --host 0.0.0.0 --port 8100
```

默认 HTTP 使用 full_int8。构建校验仅检查实际版本、模块导入和模型文件存在性，不执行模型评测。nash-p 实板 SDK 工程位于 `../chip_runtime`，本 X86 镜像不会替代其板端验证。

<!-- DOCKER_RECEIPT_20261009_START -->
## 已交付的自建镜像

现有三模型 Student tar、两类日志和使用说明见 `exports/20261009_public_x86_student/README_镜像使用.md`。使用 `compose.portable.yaml` 只启动已加载镜像，默认 Full INT8；本 README 其余官方 base 构建流程保留，不能将自建 Debian11 base 写成 OE 官方环境。
<!-- DOCKER_RECEIPT_20261009_END -->
