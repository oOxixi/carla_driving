# 7.25-next 传感器测试交接

## 版本与目的

- 分支：`7.25-next`
- 基线：远端 `7.25` 的 `65910fd`
- 目的：在不切换地图、不运行完整控制链的情况下，分别确认 RGB、LiDAR 和双传感器同步是否稳定。
- 说明：本分支只用于独立测试，不修改 `main`。

本地离线回归结果：

```text
311 passed, 1 skipped
```

该结果只证明代码和离线测试通过，不代表真实 CARLA 传感器已经通过。

## 测试前准备

1. 拉取并切换到 `7.25-next`。
2. 使用能够 `import carla` 的 Python 环境。
3. 启动与 Python API 版本一致的 CARLA。
4. 在 CARLA 中加载 `Town03`。
5. 关闭其他会控制世界同步模式或生成车辆的 Python 脚本。
6. 在仓库根目录执行以下命令。

探针不会调用 `load_world`。如果当前不是 Town03，会直接报错退出。

## 必跑顺序

先测试低资源配置：

```powershell
python tools/check_sensor_stability.py --sensor rgb --profile low --frames 100 --expected-map Town03

python tools/check_sensor_stability.py --sensor lidar --profile low --frames 100 --expected-map Town03

python tools/check_sensor_stability.py --sensor both --profile low --frames 100 --expected-map Town03
```

如果以上三项全部通过，再测试默认配置：

```powershell
python tools/check_sensor_stability.py --sensor rgb --profile default --frames 100 --expected-map Town03

python tools/check_sensor_stability.py --sensor lidar --profile default --frames 100 --expected-map Town03

python tools/check_sensor_stability.py --sensor both --profile default --frames 100 --expected-map Town03
```

不要并行运行这些命令。每条结束后确认 CARLA 仍然存活，再运行下一条。

## 判定方式

- 退出码 `0`：收到要求数量的连续对齐帧，测试通过。
- 退出码 `1`：传感器回调或双传感器对齐超时。
- 退出码 `2`：连接、地图、CARLA API 或运行环境异常。
- CARLA 窗口崩溃：记录最后一行 `probe stage=...`，该项判定失败。

成功时末尾会出现类似内容：

```text
probe result={"aligned_frames": 100, ..., "success": true}
```

## 需要回传

每个测试请回传：

1. 完整命令。
2. 终端从 `probe stage=connect` 到最终结果的完整输出。
3. 是否出现 CARLA Fatal Error 或 Shader compilation failure。
4. CARLA 版本、操作系统、显卡型号和驱动版本。
5. 若崩溃，提供 CARLA `Saved/Logs` 中对应时间的日志。

结果表：

| 配置 | RGB | LiDAR | RGB + LiDAR |
|---|---|---|---|
| low | 待测 | 待测 | 待测 |
| default | 低资源全过后再测 | 低资源全过后再测 | 低资源全过后再测 |

## 测试文件

- `tools/check_sensor_stability.py`：命令行入口。
- `integration/sensor_stability.py`：探针实现。
- `integration/tests/test_sensor_stability.py`：离线测试。
- `pytest.ini`：仓库根目录统一测试入口。
