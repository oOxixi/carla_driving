# 挑战赛道 Docker 运行时阶段构建

这个上下文只含公开源码、场景配置、启动器和依赖校验，不含本地正式 ONNX、训练权重、数据、音频或最终提交包。GitHub Ubuntu 22.04 runner 实际构建一个自建 X86 Student 运行时，以 `python:3.10.12-slim-bullseye` 为公共基础镜像，精确安装现有核心依赖，检查版本、文件/import 后，流式 `docker save | gzip -1` 导出运行时阶段。该压缩文件是 Docker 镜像传输物，不能当作最终挑战赛道提交压缩包。

原官方 `openexplorer/ai_toolchain_ubuntu_22_j6_cpu:v3.9.1` 在[实跑 37884671386](https://github.com/oOxixi/carla_driving/actions/runs/37884671386)中获取匿名 token 后，读取 manifest 返回 HTTP 401，尚未下载 layers。此次公共 Python 容器**不是 OE 官方工具链，不替代官方基准成绩或已有官方环境实测证据**。元数据分别记录公共 base 实际拉取与此前官方引用访问失败；即使 Python 成功，也保留 `official_environment_equivalent=false`。原 `Dockerfile.student-x86` 工程不变，取得原 OE 镜像后仍可按它构建。

先匿名读取所选公共 base 的 Docker Registry manifest，选择 Linux amd64，按实际 digest 拉取，避免同名 tag 在预检与构建之间变化。记录 manifest、压缩 layers 字节数、磁盘余量、base/image inspect、基础 OS、实际 Python 和运行依赖版本。token 不写入日志，不使用自定义 secrets，不推送 registry，不删除 runner 的未知目录。`inspect_registry.py` 的默认 repository/tag 仍为原 OE 引用；本 workflow 显式传入 `library/python` 与 `3.10.12-slim-bullseye`。

默认下载上限为压缩 layers 10 GiB，实际运行时镜像体积上限为 20 GiB。拉取前的 `3 × 压缩 layers + 6 GiB`、导出前的 gzip 空间公式是保守容量阈值，**不是实测展开体积或正式镜像体积**。容量不足、tag 不可获取、基础依赖版本不匹配、import 失败等都会停止并保留真实日志。

Torch 2.8.0+cpu 从 PyTorch 官方 CPU wheel index 安装，其依赖使用官方 index／PyPI；其他依赖受原直接约束控制。`verify_runtime_stage.py` 复用原校验器的版本常量，检查 Python 3.10.12、torch 2.8.0+cpu、onnxruntime 1.19.0、NumPy 1.23.0、Pillow 9.3.0、jsonschema 4.25.1、psutil 7.2.1、PyYAML >=6,<7，版本不匹配立即停止。记录实际 pip freeze 和 OS package 版本。**这些核心版本相同不代表整个 OE 环境等同**；本阶段不执行模型推理。

成功产物为 `runtime-stage-image.tar.gz`、`stage_image_manifest.json`、base/image inspect、实际依赖版本/freeze、源码资产/import 检查结果、SHA256 和真实构建日志；artifact 保留 3 天。正式私有 ONNX 由本机后续处理，并需明确区分离线添加模型层与真实 Docker 加载/推理验证。**本工作流成功只代表运行时阶段成功，不代表带正式模型的最终镜像已构建或运行。**

workflow 只在 challenge 分支的本目录或该 workflow 更新时启动，也支持手工 dispatch。官方 actions 均固定 commit：checkout [v4.2.2](https://github.com/actions/checkout/commit/11bd71901bbe5b1630ceea73d27597364c9af683)、upload-artifact [v4.6.2](https://github.com/actions/upload-artifact/commit/ea165f8d65b6e75b540449e92b4886f43607fa02)。
