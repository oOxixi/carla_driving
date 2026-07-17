# CARLA 控制系统 Docker 部署与归档

本配置把运行环境拆为两个容器：

|服务|镜像|职责|
|---|---|---|
|`carla`|`carlasim/carla:0.9.16`|CARLA 0.9.16 服务端，开放 2000/2001/8000|
|`controller`|`carla-driving-controller:0.1.0`|Python 3.12、CARLA Python API、A/B/C/D 控制模块及可选语音依赖|

拆分后可以只导出算法镜像，也可以将 CARLA 与算法一并导出用于离线演示。仓库中的 `CARLA_0.9.16` 是 Windows 二进制，不能复制到 Linux 容器，已由 `.dockerignore` 排除。

## 前置条件

1. Docker Desktop 正在运行且使用 Linux containers。
2. NVIDIA GPU 透传可用：

```powershell
docker run --rm --gpus all nvidia/cuda:12.8.1-base-ubuntu24.04 nvidia-smi
```

3. 在仓库根目录创建本机配置：

```powershell
Copy-Item docker/.env.example docker/.env
```

RTX 5070 Laptop GPU 为 8GB 显存，CARLA 默认以 `Low` 与 `-RenderOffScreen` 启动。不要同时加载大型 VLM；不需要真实 ASR 时，可将 `WITH_VOICE=0` 以缩短构建并减小镜像。

## 构建和配置检查

```powershell
.\docker\scripts\verify-stack.ps1 -BuildController
```

该脚本会检查 Docker、渲染 Compose 配置并构建控制器镜像。镜像默认只验证 CARLA Python API 与 A/B/C/D 包可导入；没有统一编排入口时，不会伪装为已经完成全流程运行。

## 启动 CARLA 与控制器

```powershell
docker compose --env-file docker/.env -f docker/compose.yaml up -d carla
docker compose --env-file docker/.env -f docker/compose.yaml ps
docker compose --env-file docker/.env -f docker/compose.yaml logs -f carla
```

容器内控制程序必须连接 `CARLA_HOST=carla`、`CARLA_PORT=2000`；主机侧则用 `127.0.0.1:2000`。统一运行时入口补齐后，在 `docker/.env` 设置：

```dotenv
CONTROLLER_COMMAND=python3 -m integration.carla_runner --host carla --port 2000 --command-json /workspace/artifacts/command.json
```

再执行：

```powershell
docker compose --env-file docker/.env -f docker/compose.yaml --profile controller up --abort-on-container-exit
```

停止服务：

```powershell
docker compose --env-file docker/.env -f docker/compose.yaml down
```

## 导出、校验和离线导入

只导出算法环境：

```powershell
.\docker\scripts\export-images.ps1
```

同时导出算法和 CARLA 服务端：

```powershell
.\docker\scripts\export-images.ps1 -IncludeCarla
```

归档写入 `artifacts/carla-driving-images-*.tar` 并生成 SHA256 文件。目标机校验、导入：

```powershell
Get-FileHash .\carla-driving-images-YYYYMMDD-HHMMSS.tar -Algorithm SHA256
docker image load --input .\carla-driving-images-YYYYMMDD-HHMMSS.tar
```

离线机器仍需 Docker Desktop、Linux 容器模式和 NVIDIA 驱动。语音基础模型存在 Docker 卷 `model-cache` 中，不会自动写入镜像；若需完整离线 ASR，必须另行备份/恢复该卷。

## 常见问题

|现象|处理|
|---|---|
|`could not select device driver nvidia`|更新 NVIDIA 驱动/Docker Desktop，并先运行前置 GPU 命令。|
|CARLA 不健康|检查 `docker compose ... logs carla`；首次启动可超过 30 秒，关闭其他 GPU 程序。|
|端口 2000 无法连接|运行 `Test-NetConnection 127.0.0.1 -Port 2000`，确认本机 CARLA 没占用端口。|
|首次 ASR 下载慢|检查网络和 `model-cache` 卷；模型缓存需要随交付物单独留存。|
|要连接本机 Windows CARLA|不要把 Windows CARLA 挂载进容器。将控制器的 `CARLA_HOST` 设置为 `host.docker.internal`。|
