# 本次 Student 镜像使用（2026-10-09）

`student-x86-image.tar` 已生成，包含真实 Full INT8、FP32 与 Mixed Top-3 三份私有 ONNX。Linux runner 实际完成运行时阶段 Docker build、run 版本/import 检查、inspect 与 save，记录见 `runtime_stage/`；随后本机按标准 Docker archive 格式追加模型层。最终镜像 ID 是配置内容计算值，见 `assembly_manifest.json`，尚无最终 Linux Docker inspect 记录。

基础 OS 为 Debian 11（公共 Python 3.10.12 镜像），核心库版本与既有记录锁定一致；**不是官方 OE 工具链，不替代官方基准成绩**。官方 OE3.9.1 匿名拉取返回 HTTP 401，原始记录见 `official_base_attempt/`。最终 Linux `docker load`、服务启动与模型推理尚未执行。

在本目录的 Linux Docker 环境加载并启动默认 Full INT8：

```bash
docker load -i student-x86-image.tar
docker run --rm -p 8100:8100 challenge-student-x86:20261009
```

一条依赖和三份模型文件存在性校验命令：

```bash
docker run --rm --entrypoint python3 challenge-student-x86:20261009 /opt/challenge/02_源码与部署/docker/verify_runtime.py
```

切换 FP32 或 Mixed Top-3：

```bash
docker run --rm -p 8100:8100 challenge-student-x86:20261009 --mode http --variant fp32 --host 0.0.0.0 --port 8100
docker run --rm -p 8100:8100 challenge-student-x86:20261009 --mode http --variant mixed_top3 --host 0.0.0.0 --port 8100
```

需共享 RGB 与日志目录时，从完整材料根目录运行 `docker compose -f 02_源码与部署/docker/compose.portable.yaml up`，将真实输入图像放入 `runs/shared_images/`，请求的 `rgb_ref` 使用该目录内相对路径。Compose 只使用已加载镜像，无自动 build 或 pull fallback。接口为 `GET /health` 与 `POST /infer`，输入/输出契约见源码接口说明。

本次只有 Docker 镜像 tar 交付物，其他材料仍待收齐；未生成最终提交 ZIP。镜像 bytes/SHA256、私有模型身份及各项未执行标记以 `assembly_manifest.json` 为准。
