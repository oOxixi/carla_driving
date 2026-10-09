# 挑战赛道 Docker 运行时阶段构建

这个上下文只含公开源码、场景配置、启动器和依赖校验，不含本地正式 ONNX、训练权重、数据、音频或最终提交包。GitHub Ubuntu 22.04 runner 对官方 CPU 基础镜像进行实际拉取、Docker 构建、依赖版本和文件/import 检查，再流式 `docker save | gzip -1` 导出运行时阶段。该压缩文件是 Docker 镜像传输物，不能当作最终挑战赛道提交压缩包。

基础镜像为 `openexplorer/ai_toolchain_ubuntu_22_j6_cpu:v3.9.1`。先匿名读取 Docker Registry manifest，选择 Linux amd64，并按实际 digest 拉取，避免同名 tag 在预检与构建之间变化。记录公开 manifest、压缩 layers 字节数、磁盘剩余空间和 Docker inspect。token 不写入日志，不使用自定义 secrets，不推送 registry，也不删除 runner 的未知目录。

默认下载上限为压缩 layers 10 GiB，实际运行时镜像体积上限为 20 GiB。拉取前的 `3 × 压缩 layers + 6 GiB`、导出前的 gzip 空间公式是保守容量阈值，**不是实测展开体积或正式镜像体积**。容量不足、tag 不可获取、基础依赖版本不匹配、import 失败等都会停止并保留真实日志。

`verify_runtime_stage.py` 复用原校验器的版本常量，检查 Python 3.10.12、torch 2.8.0+cpu、onnxruntime 1.19.0、NumPy 1.23.0、Pillow 9.3.0、jsonschema 4.25.1、psutil 7.2.1、PyYAML >=6,<7。记录实际传递依赖 freeze。本阶段不执行模型推理。

成功产物为 `runtime-stage-image.tar.gz`、`stage_image_manifest.json`、base/image inspect、实际依赖版本/freeze、源码资产/import 检查结果、SHA256 和真实构建日志；artifact 保留 3 天。正式私有 ONNX 由本机后续处理，并需明确区分离线添加模型层与真实 Docker 加载/推理验证。**本工作流成功只代表运行时阶段成功，不代表带正式模型的最终镜像已构建或运行。**

workflow 只在 challenge 分支的本目录或该 workflow 更新时启动，也支持手工 dispatch。官方 actions 均固定 commit：checkout [v4.2.2](https://github.com/actions/checkout/commit/11bd71901bbe5b1630ceea73d27597364c9af683)、upload-artifact [v4.6.2](https://github.com/actions/upload-artifact/commit/ea165f8d65b6e75b540449e92b4886f43607fa02)。
