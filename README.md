# CARLA 多模态驾驶控制闭环

本仓库的正式车辆运行与验收入口是：

```text
python -m integration.carla_runner
```

正式控制顺序固定为：状态/感知 → A 命令与 FSM → B 横向 + C 纵向 →
D 最终安全仲裁 → 唯一 `apply_control()`。Qwen 只输出高层动作，不能输出或绕过
D 直接下发方向盘、油门和刹车。

## 当前能力

- CARLA 0.9.16 同步控制与 Actor 生命周期管理；
- RGB、LiDAR、碰撞、压线和地图状态桥接；
- YOLO11 ONNX 道路参与者检测；
- 定速、停车保持、前车跟随、TTC 与紧急制动；
- Pure Pursuit/Stanley 横向控制；
- D 对低 TTC、近距离障碍、红灯、路线偏差、异常命令和非法控制进行最终覆盖；
- JSONL 逐帧日志、场景摘要和 34 个场景契约。

## 环境

本仓库附带的 CARLA Python wheel 是 CPython 3.12 版本，请使用：

```powershell
py -3.12 -m pip install -r requirements.txt
```

YOLO11 权重默认放在 Git 忽略目录：

```text
artifacts/models/yolo11n.onnx
```

启动 CARLA：

```powershell
Start-Process `
  -FilePath ".\CARLA_0.9.16\CarlaUE4.exe" `
  -ArgumentList "-quality-level=Low" `
  -WindowStyle Hidden
```

## 正式运行

world 模式用于控制与地图真值调试：

```powershell
py -3.12 -m integration.carla_runner `
  --host 127.0.0.1 --port 2000 `
  --perception-mode world `
  --scenario cruise --frames 120
```

sensors + YOLO11 模式用于真实传感器链验收：

```powershell
py -3.12 -m integration.carla_runner `
  --host 127.0.0.1 --port 2000 `
  --perception-mode sensors `
  --scenario-facts-mode perception `
  --rgb-detector-model artifacts/models/yolo11n.onnx `
  --rgb-detector-confidence 0.25 `
  --scenario follow --frames 120 `
  --sensor-warmup-frames 30 --sensor-timeout-s 1.0
```

`world`、`sensors` 和 `virtual` 的字段来源会写入 `perception_sources`；不得把
world/virtual 真值描述为真实视觉检测。

## Qwen/Day20 边界

`integration/day20/` 保留第一组的 Qwen-VL 高层决策演示。该目录不是正式场景
验收入口；其中 Ego 控制适配器也必须经过 D 仲裁。最终演示与批量回归以
`integration.carla_runner` 生成的证据为准。

## 验证

```powershell
python -m pytest -q `
  car_control_A\tests `
  car_control_B\tests `
  car_control_C\tests `
  car_control_D\tests `
  integration\tests

python tools\validate_scenarios.py
python tools\validate_c_role.py
```

角色说明和接口边界见 `integration/HANDOFF.md`、`car_control_C/HANDOFF.md` 和
`HANDOFF_yqq_0722.md`。
