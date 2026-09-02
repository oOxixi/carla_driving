# CARLA 多模态智能驾驶闭环

本仓库的正式车辆运行入口是：

```bash
python -m integration.carla_runner
```

正式主链为：语音/场景指令 + RGB/LiDAR/Radar/车辆状态 → Qwen3.5-2B 高层规划 →
A 状态机 → B 横向控制 + C 纵向控制 → D 安全仲裁 → 唯一 `apply_control()`。
Qwen 只能给出高层 `ManeuverPlan`，不能直接下发方向盘、油门或刹车，也不能绕过 D。

## 当前正式范围

- 模型：只使用服务器上的 Qwen 2B 生产服务；更大模型不属于当前测试主线。
- 仿真：CARLA 0.9.16，同步模式，Actor 和传感器完整生命周期管理。
- 感知：四视角 RGB、LiDAR、Radar、碰撞、压线和地图/车辆状态。
- 控制：车道保持、转向/变道、定速、跟车、TTC、紧急制动和停车保持。
- 场景：冒烟、横向、安全、回归、Qwen 路由/故障/全链以及三个正式长里程场景。
- 证据：逐帧 JSONL、场景摘要、Qwen 路由与计划、传感器来源和评分字段。

## 快速开始

```bash
python -m pip install -r requirements.txt
python tools/validate_scenarios.py
python tools/validate_official_scenes.py
python -m pytest -q
```

正式 S2 8km 全链验证：

```bash
export QWEN_SERVICE_URL=http://127.0.0.1:18000
bash scripts/run_official_s2_member3.sh --validate
bash scripts/run_official_s2_member3.sh --smoke
bash scripts/run_official_s2_member3.sh --run
```

运行输出统一写入 `artifacts/`。该目录默认不纳入 Git；需要长期保留的基准必须经过
脱敏、说明适用范围并迁入 `metrics/` 或 `submission/`。

## 文档入口

- [完整目录说明](docs/REPOSITORY_STRUCTURE.md)
- [文档索引](docs/README.md)
- [正式三场景说明](scenarios/official_competition/README.md)
- [第二组运行手册](docs/runbooks/SECOND_GROUP.md)
- [Qwen 远程服务说明](docs/runbooks/QWEN_REMOTE.md)
- [2B 独立复现说明](docs/reproduction/QWEN2B_REPRODUCTION.md)
- [接口契约](interfaces/README.md)

根目录只保留项目入口、依赖清单、Docker 启停包装器和兼容层；业务代码按职责放入对应
包，历史交接稿和按日期复制的实现不再作为源码维护。
