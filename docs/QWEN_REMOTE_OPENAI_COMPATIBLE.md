# Qwen2.5-VL 远端后端接入

正式 CARLA runner 支持 OpenAI-compatible 的 Qwen2.5-VL 服务。Qwen 只输出高层动作，A/C/D 仍分别负责命令边界、纵向控制和最终安全仲裁；模型不能直接产生油门、刹车或方向盘控制量。

## 环境配置

在运行进程的同一个 shell 中设置服务信息：

```bash
export QWEN_BASE_URL='http://127.0.0.1:18000/v1'
export QWEN_MODEL='qwen2.5-vl'
export QWEN_API_KEY='your-secret-if-required'
```

`QWEN_API_KEY` 只从环境变量读取，不会作为 CLI 参数或证据配置写入日志。无需鉴权的服务可以不设置该变量。

可先独立验证接口：

```bash
conda run -n carla312 python tools/qwen_remote_smoke.py
```

服务返回纯 JSON 或完整的 ` ```json ... ``` ` 包装均可；包装外文字、未知字段和 `throttle`、`brake`、`steer` 等底层控制字段会被拒绝并触发 fail-closed。

## CARLA 闭环运行

CARLA 启动在 Town03/Town03_Opt 后，可执行：

```bash
conda run -n carla312 python -m integration.carla_runner \
  --host 127.0.0.1 \
  --port 2000 \
  --scenario-file scenarios/smoke/S01_set_speed_20.json \
  --use-current-map \
  --perception-mode sensors \
  --scenario-facts-mode perception \
  --sensor-profile default \
  --sensor-timeout-s 2.0 \
  --sensor-warmup-frames 60 \
  --qwen-remote \
  --realtime \
  --watchdog-timeout-s 3.0 \
  --log-dir artifacts/qwen_remote_live
```

若使用 ONNX RGB 检测器，再加 `--rgb-detector-model /absolute/path/to/yolo11n.onnx`。路径必须存在。

远端推理在后台线程运行，不阻塞 CARLA tick。等待、超时、陈旧或接口错误都会由 D 层强制停车。默认推理墙钟截止为 10 秒，模型结果仿真时限为 12 秒，命令执行时限为 30 秒；分别可由 `--qwen-max-inference-s`、`--qwen-decision-ttl-s` 和 `--qwen-command-ttl-s` 调整。

Low 画质机器同时运行 RGB/LiDAR 和 ONNX 检测器时，偶发帧可能略超过 1 秒。推荐把运行时心跳阈值设为 `--watchdog-timeout-s 3.0`；感知自身仍由 `--sensor-timeout-s 2.0` 独立 fail-closed，不会因此放过传感器超时。

每次运行会记录 PENDING/READY/ERROR 等 Qwen 事件、原始模型文本、验证后的高层命令和 A 层运行命令。用于回放的 RGB JPEG 保存在 gitignored 的 `artifacts/runtime/qwen_live/`。
