# 第二组唯一全链路运行手册

## 1. 环境

```bash
cd /home/abc/projects/carla_driving_main_20260730
conda activate carla312
python -m pip install -r requirements.txt
```

真实慢路径还需要把本地模型放入 `models/` 并设置：

```bash
export QWEN_MODEL_PATH=/absolute/path/to/Qwen2.5-VL-model
export QWEN_IMAGE_ROOT=/absolute/path/to/runtime/images
```

没有模型时服务会明确显示 `DEGRADED`。快路径仍可运行，复杂命令被拒绝，不会
回退为未经模型验证的车辆动作。`QWEN_TEST_BACKEND=1` 只能测试接口，不能作为模型
正确率或延迟证据。

## 2. 自检与服务生命周期

```bash
./run_full_pipeline.sh start
./run_full_pipeline.sh check
./run_full_pipeline.sh strict-check
./run_full_pipeline.sh status
./run_full_pipeline.sh stop
```

- `check`：接口和依赖必须通过；Qwen/CARLA 状态会记录，但可处于未启动状态；
- `strict-check`：真实 Qwen 必须 production-ready，CARLA 必须连接成功；
- PID 只会在命令行确认为 `qwen_service.server` 后用于停止，避免误杀其他进程。

## 3. 正式 CARLA 快路径闭环

```bash
./run_full_pipeline.sh run \
  --scenario-file scenarios/smoke/S01_set_speed_20.json \
  --perception-mode sensors \
  --sensor-profile low \
  --log-dir artifacts/second_group_20260731/runs/S01
```

实时语音：

```bash
./run_full_pipeline.sh run \
  --use-current-map \
  --perception-mode world \
  --default-speed-mps 0 \
  --live-mic \
  --live-mic-source alsa_input.pci-0000_00_1f.3.analog-stereo \
  --follow-spectator --realtime --frames 12000 \
  --test-command-ttl-s 30 --print-every 20 \
  --log-dir artifacts/second_group_20260731/live_voice
```

上例的 `world` 仅适合快速验证标准语音与车辆控制，不提供 Qwen 原始 RGB。正式复杂
语音验收必须改为 `--perception-mode sensors --sensor-profile low`；慢路径触发时，当前
同帧 RGB 会由 Qwen 后台线程写入共享图像目录，控制线程不做同步图像 I/O。

停止、定速、减速、保持车道走确定性快路径，不依赖 Qwen。模型服务和 CARLA 控制
循环是独立线程/进程，Qwen 超时不会降低 20 Hz 控制频率。

复杂语音（跟随、转向、变道等）会先进入确定性停车等待。只有 Qwen 在 deadline 内
返回、Schema/置信度/目标 ID/最新感知均通过，且 D 已实现对应动作时才执行；当前 D
未实现的转向、变道和靠边计划会明确拒绝并继续停车。`sensors` 模式同时挂载
RGB/LiDAR/Radar；Radar 使用 5 ms 可选同帧窗口，掉线会标记无效但不阻塞控制。

三路传感器流稳定性探针：

```bash
python tools/check_sensor_stability.py \
  --host 127.0.0.1 --port 2000 --sensor all --profile low --frames 100
```

> 2026-07-31 当前主机实测提醒：三路 100 帧同帧探针通过，但 Town03 完整感知采集
> P95 为约 40–71 ms，尚未达到 30 ms 目标；S01/D03 活跃管线也尚未达到 20 Hz。
> `sensor_to_control_ms` 只从感知就绪后开始，验收必须同时检查日志中的
> `perception_acquire_ms` 和 `pipeline_active_ms`，不得用前者替代完整链路。

## 4. 自动验证

```bash
python -m pytest -q
python -m tools.benchmark_perception_pipeline \
  --frames 1000 --output artifacts/second_group_20260731/perception_benchmark.json
python -m tools.benchmark_control_runtime \
  --frames 10000 --output car_control_D/control_benchmark.json
```

正式矩阵和 60 分钟实跑必须在真实 CARLA/Qwen 环境执行，缺少模型或服务时不得用
确定性测试后端替代：

```bash
python -m tools.run_carla_scenario_matrix \
  --scenario scenarios/smoke/S01_set_speed_20.json \
  --scenario scenarios/safety_D/D03_front_vehicle_brake.json \
  --scenario scenarios/safety_D/D08_command_conflict_red_light_continue.json \
  --seeds 0,1,2,3,4 --repeats-per-seed 4 \
  --output-dir artifacts/second_group_20260731/scenario_matrix
```

长稳脚本的正式参数为 `--duration-minutes 60`。报告必须保留资源采样、队列、传感器
对齐、Qwen 周期请求和结束后的恢复探针。
